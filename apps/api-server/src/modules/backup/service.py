"""Full data export.

Produces a single ZIP archive holding every row of every table, so the client owns a
complete copy of their data. Tables and columns are discovered from the SQLAlchemy
metadata instead of being listed by hand: a new model column is exported automatically
and can never be silently dropped from the backup.
"""

import base64
import csv
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO

from sqlalchemy import Table, select, text
from sqlalchemy.orm import Session

from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence.models import GlobalSettings
from src.infrastructure.utils.datetime_utils import get_local_datetime

EXPORT_FORMAT_VERSION = "1.0"

# Rows are streamed in batches so a large audit_logs table never lands in memory at once.
ROW_BATCH_SIZE = 1000

# Keeps small exports in memory and spills bigger ones to a temporary file.
SPOOL_MAX_BYTES = 32 * 1024 * 1024

# Credentials, not client data. Exporting them puts a live secret inside a file that is
# copied off the server by design — and, once recurring backups are on, into the very Google
# Drive folder those credentials unlock.
#
# `users.reset_token` would let anyone holding the archive take over an account.
# `backup_settings.drive_*` is the OAuth client and refresh token of the Google account the
# archives land in: an archive carrying them hands over the whole backup destination. The
# cost is that a restore leaves Google Drive disconnected and the administrator reconnects
# it, which the schedule screen states plainly.
REDACTED_COLUMNS: set[tuple[str, str]] = {
    ("users", "reset_token"),
    ("users", "reset_token_expires_at"),
    ("backup_settings", "drive_client_secret"),
    ("backup_settings", "drive_refresh_token"),
}

README = """Pawn & Personal Loan Platform - data export

manifest.json   Export metadata: generation date, database schema revision,
                table list with row counts, and the columns of each table.
data/           One JSON file per table with every row and every column.
                This is the complete, machine readable copy of your data.
csv/            The same data as spreadsheet files (UTF-8 with BOM), ready to
                open in Excel or Google Sheets.

Files under data/ are the authoritative copy: they preserve exact values and
types. The CSV files are a convenience view of the same rows.

Keep this archive in a safe place. It contains all your business information,
including user password hashes.
"""


@dataclass
class TableExport:
    name: str
    rows: int
    columns: list[str]


@dataclass
class ExportArchive:
    stream: BinaryIO
    filename: str
    size_bytes: int
    tables: list[TableExport]
    total_rows: int
    schema_revision: str | None


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    return value


def _is_redacted(table_name: str, column_name: str) -> bool:
    return (table_name, column_name) in REDACTED_COLUMNS


def _serialize_row(table: Table, row: Any) -> dict[str, Any]:
    return {
        column.name: None if _is_redacted(table.name, column.name) else _serialize_value(row[column.name])
        for column in table.columns
    }


def _stream_rows(db: Session, table: Table):
    result = db.execute(select(table).execution_options(stream_results=True, yield_per=ROW_BATCH_SIZE))
    for partition in result.mappings().partitions(ROW_BATCH_SIZE):
        yield from partition


def _write_table_json(archive: zipfile.ZipFile, db: Session, table: Table) -> int:
    written = 0
    with archive.open(f"data/{table.name}.json", "w") as handle:
        handle.write(b"[\n")
        for row in _stream_rows(db, table):
            prefix = b",\n" if written else b""
            payload = json.dumps(_serialize_row(table, row), ensure_ascii=False)
            handle.write(prefix + payload.encode("utf-8"))
            written += 1
        handle.write(b"\n]\n")
    return written


def _write_table_csv(archive: zipfile.ZipFile, db: Session, table: Table) -> None:
    column_names = [column.name for column in table.columns]
    with archive.open(f"csv/{table.name}.csv", "w") as handle:
        # BOM so accented characters open correctly in Excel.
        with io.TextIOWrapper(handle, encoding="utf-8-sig", newline="") as text_handle:
            writer = csv.writer(text_handle)
            writer.writerow(column_names)
            for row in _stream_rows(db, table):
                serialized = _serialize_row(table, row)
                writer.writerow(["" if serialized[name] is None else serialized[name] for name in column_names])


def read_schema_revision(db: Session) -> str | None:
    """Alembic revision the database is on, so a restore knows the target schema."""
    try:
        return db.scalar(text("SELECT version_num FROM alembic_version"))
    except Exception:
        # Missing table (for example on a metadata created database) aborts the
        # transaction on PostgreSQL, so it has to be rolled back before reusing it.
        db.rollback()
        return None


def build_export_archive(db: Session, generated_by: str | None) -> ExportArchive:
    # Read first: a failure here rolls the transaction back before any data is queried.
    schema_revision = read_schema_revision(db)

    settings = db.get(GlobalSettings, 1)
    generated_at = get_local_datetime(db)

    buffer = SpooledTemporaryFile(max_size=SPOOL_MAX_BYTES)
    tables: list[TableExport] = []

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for table in Base.metadata.sorted_tables:
            rows = _write_table_json(archive, db, table)
            _write_table_csv(archive, db, table)
            tables.append(
                TableExport(
                    name=table.name,
                    rows=rows,
                    columns=[column.name for column in table.columns],
                )
            )

        manifest = {
            "format_version": EXPORT_FORMAT_VERSION,
            "app_name": settings.app_name if settings is not None else None,
            "company_name": settings.company_name if settings is not None else None,
            "generated_at": generated_at.isoformat(),
            "generated_by": generated_by,
            "database_dialect": db.get_bind().dialect.name,
            "schema_revision": schema_revision,
            "total_rows": sum(item.rows for item in tables),
            "redacted_fields": sorted(f"{table}.{column}" for table, column in REDACTED_COLUMNS),
            "tables": [
                {"name": item.name, "rows": item.rows, "columns": item.columns} for item in tables
            ],
        }
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", README)

    size_bytes = buffer.tell()
    buffer.seek(0)

    return ExportArchive(
        stream=buffer,
        filename=f"{_filename_slug(settings)}-export-{generated_at.strftime('%Y%m%d-%H%M%S')}.zip",
        size_bytes=size_bytes,
        tables=tables,
        total_rows=sum(item.rows for item in tables),
        schema_revision=schema_revision,
    )


def _filename_slug(settings: GlobalSettings | None) -> str:
    # Only reached before any settings row exists, or when both names are blank. Retention
    # orders copies by the timestamp in the filename rather than by this prefix, so changing
    # it does not disturb archives already written under the old one.
    raw = (settings.company_name or settings.app_name) if settings is not None else "mutuum"
    slug = "".join(character if character.isalnum() else "-" for character in (raw or "").lower())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "mutuum"
