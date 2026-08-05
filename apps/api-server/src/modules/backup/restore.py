"""Full data import (restore).

Replaces the entire database with the contents of an export archive. This is
destructive by definition, so the flow is: analyse first, refuse on any doubt, and
apply everything inside a single transaction so a failure leaves the data untouched.
"""

import base64
import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Integer, LargeBinary, Table, func, insert, select, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Session

from src.infrastructure.persistence.database import Base
from src.modules.backup.service import EXPORT_FORMAT_VERSION, read_schema_revision

# The administrator must type this exactly to authorise the replacement.
IMPORT_CONFIRMATION = "REPLACE ALL DATA"

SUPPORTED_FORMAT_VERSIONS = {EXPORT_FORMAT_VERSION}

MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024


class ArchiveImportError(Exception):
    """Raised when an archive cannot be read or cannot be applied."""


@dataclass
class TablePlan:
    name: str
    current_rows: int
    incoming_rows: int


@dataclass
class ImportAnalysis:
    format_version: str | None = None
    archive_schema_revision: str | None = None
    database_schema_revision: str | None = None
    archive_generated_at: str | None = None
    tables: list[TablePlan] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def can_import(self) -> bool:
        return not self.errors

    @property
    def total_current_rows(self) -> int:
        return sum(item.current_rows for item in self.tables)

    @property
    def total_incoming_rows(self) -> int:
        return sum(item.incoming_rows for item in self.tables)


def _open_archive(content: bytes) -> zipfile.ZipFile:
    if len(content) > MAX_ARCHIVE_BYTES:
        raise ArchiveImportError("The archive is too large to import.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ArchiveImportError("The file is not a valid ZIP archive.") from exc

    if sum(item.file_size for item in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
        raise ArchiveImportError("The archive expands to an unreasonable size.")

    return archive


def _read_json_entry(archive: zipfile.ZipFile, name: str) -> Any:
    try:
        raw = archive.read(name)
    except KeyError as exc:
        raise ArchiveImportError(f"The archive is missing {name}.") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArchiveImportError(f"{name} is not valid JSON.") from exc


def _read_table_rows(archive: zipfile.ZipFile, table: Table) -> list[dict[str, Any]]:
    entry = f"data/{table.name}.json"
    rows = _read_json_entry(archive, entry)

    if not isinstance(rows, list):
        raise ArchiveImportError(f"{entry} must contain a list of rows.")
    if any(not isinstance(row, dict) for row in rows):
        raise ArchiveImportError(f"{entry} contains a row that is not an object.")

    return rows


def _deserialize_value(column: Any, value: Any) -> Any:
    if value is None:
        return None

    column_type = column.type

    if isinstance(column_type, SAEnum) and column_type.enum_class is not None:
        try:
            return column_type.enum_class(value)
        except ValueError:
            try:
                return column_type.enum_class[value]
            except KeyError as exc:
                raise ArchiveImportError(
                    f"Invalid value {value!r} for {column.table.name}.{column.name}."
                ) from exc

    if isinstance(column_type, DateTime):
        return datetime.fromisoformat(value) if isinstance(value, str) else value

    if isinstance(column_type, Date):
        return date.fromisoformat(value) if isinstance(value, str) else value

    if isinstance(column_type, Boolean):
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return bool(value)

    if isinstance(column_type, LargeBinary):
        return base64.b64decode(value) if isinstance(value, str) else value

    return value


def _row_sort_key(table: Table, row: dict[str, Any]) -> tuple:
    # Ascending primary key: self referencing rows (a renewed loan pointing at its
    # source loan) then always land after the row they reference.
    return tuple(
        (row.get(column.name) is None, row.get(column.name)) for column in table.primary_key.columns
    )


def _check_columns(table: Table, rows: list[dict[str, Any]], analysis: ImportAnalysis) -> None:
    """The export writes uniform rows, so the first one describes the whole table."""
    if not rows:
        return

    expected = {column.name for column in table.columns}
    present = set(rows[0])

    unknown = present - expected
    missing = expected - present

    if unknown:
        analysis.errors.append(
            f"{table.name} has columns that do not exist in this schema: {', '.join(sorted(unknown))}."
        )
    if missing:
        analysis.errors.append(f"{table.name} is missing columns: {', '.join(sorted(missing))}.")


def _check_administrator_access(users: list[dict[str, Any]], analysis: ImportAnalysis) -> None:
    """A restore that leaves nobody able to sign in would lock the client out for good."""
    active_admins = [
        user for user in users if str(user.get("role")) == "administrator" and bool(user.get("is_active"))
    ]

    if not active_admins:
        analysis.errors.append(
            "The archive has no active administrator, so nobody could sign in after the restore."
        )
    elif not any(user.get("hashed_password") for user in active_admins):
        analysis.warnings.append(
            "Administrator passwords are missing from the archive; a password reset would be needed."
        )


def _check_backup_destination(rows: list[dict[str, Any]], analysis: ImportAnalysis) -> None:
    """Say out loud that a restore leaves Google Drive disconnected.

    The export redacts the OAuth secret and refresh token on purpose — an archive carrying them
    hands over the destination the archives are kept in — so a restore reloads a schedule that
    is switched on and points at a Drive it can no longer reach. Left unsaid, the recurring
    backup stops working at the exact moment the installation has just proved it needs one.
    """
    reconnect_needed = any(
        row.get("destination") == "google_drive" or row.get("drive_client_id") for row in rows
    )

    if reconnect_needed:
        analysis.warnings.append(
            "The Google Drive credentials are not included in an export. Reconnect the Google "
            "account from the settings screen after restoring, or the recurring backup will fail."
        )


def analyze_archive(db: Session, content: bytes) -> ImportAnalysis:
    """Inspect an archive against the live schema without writing anything."""
    analysis = ImportAnalysis()
    archive = _open_archive(content)

    manifest = _read_json_entry(archive, "manifest.json")
    if not isinstance(manifest, dict):
        raise ArchiveImportError("manifest.json has an unexpected structure.")

    analysis.format_version = manifest.get("format_version")
    analysis.archive_schema_revision = manifest.get("schema_revision")
    analysis.archive_generated_at = manifest.get("generated_at")
    analysis.database_schema_revision = read_schema_revision(db)

    if analysis.format_version not in SUPPORTED_FORMAT_VERSIONS:
        analysis.errors.append(
            f"Unsupported export format {analysis.format_version!r}. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMAT_VERSIONS))}."
        )

    if analysis.database_schema_revision is None:
        analysis.warnings.append(
            "This database has no Alembic revision recorded, so the schema could not be matched."
        )
    elif analysis.archive_schema_revision != analysis.database_schema_revision:
        analysis.errors.append(
            f"Schema mismatch: the archive was created on revision "
            f"{analysis.archive_schema_revision!r} and this database is on "
            f"{analysis.database_schema_revision!r}. Restore it on a matching version."
        )

    entries = set(archive.namelist())
    users_rows: list[dict[str, Any]] = []
    backup_settings_rows: list[dict[str, Any]] = []

    for table in Base.metadata.sorted_tables:
        current_rows = db.scalar(select(func.count()).select_from(table)) or 0

        if f"data/{table.name}.json" not in entries:
            analysis.errors.append(f"The archive has no data for table {table.name}.")
            analysis.tables.append(TablePlan(table.name, current_rows, 0))
            continue

        rows = _read_table_rows(archive, table)
        _check_columns(table, rows, analysis)

        if table.name == "users":
            users_rows = rows
        elif table.name == "backup_settings":
            backup_settings_rows = rows

        analysis.tables.append(TablePlan(table.name, current_rows, len(rows)))

    _check_administrator_access(users_rows, analysis)
    _check_backup_destination(backup_settings_rows, analysis)

    analysis.warnings.append(
        "Every table will be replaced. Export the current data first if you need a way back."
    )

    return analysis


def restore_archive(db: Session, content: bytes) -> ImportAnalysis:
    """Replace every table with the archive contents inside a single transaction."""
    analysis = analyze_archive(db, content)
    if not analysis.can_import:
        raise ArchiveImportError(" ".join(analysis.errors))

    archive = _open_archive(content)
    tables = list(Base.metadata.sorted_tables)

    try:
        # Children first so foreign keys never block the wipe.
        for table in reversed(tables):
            db.execute(table.delete())

        for table in tables:
            rows = _read_table_rows(archive, table)
            if not rows:
                continue

            columns = {column.name: column for column in table.columns}
            payload = [
                {name: _deserialize_value(columns[name], value) for name, value in row.items()}
                for row in sorted(rows, key=lambda row: _row_sort_key(table, row))
            ]
            db.execute(insert(table), payload)

        for table in tables:
            _reset_identity_sequences(db, table)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return analysis


def _reset_identity_sequences(db: Session, table: Table) -> None:
    """Realign PostgreSQL sequences with the imported ids.

    Without this the next insert reuses an id the archive already occupies.
    """
    if db.get_bind().dialect.name != "postgresql":
        return

    for column in table.primary_key.columns:
        if not isinstance(column.type, Integer):
            continue

        sequence = db.scalar(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {"table_name": table.name, "column_name": column.name},
        )
        if not sequence:
            continue

        highest = db.scalar(select(func.max(column)))
        if highest is None:
            db.execute(text("SELECT setval(:sequence, 1, false)"), {"sequence": sequence})
        else:
            db.execute(
                text("SELECT setval(:sequence, :highest, true)"),
                {"sequence": sequence, "highest": int(highest)},
            )
