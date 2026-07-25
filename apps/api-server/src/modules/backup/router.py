from collections.abc import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import User
from src.infrastructure.tasks.interest_scheduler import (
    release_cycle_lock,
    try_acquire_cycle_lock,
)
from src.modules.backup.restore import (
    IMPORT_CONFIRMATION,
    ArchiveImportError,
    ImportAnalysis,
    analyze_archive,
    restore_archive,
)
from src.modules.backup.schemas import ImportResultRead, ImportTablePlan
from src.modules.backup.service import build_export_archive
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/backup", tags=["backup"])

CHUNK_SIZE = 64 * 1024


@router.get("/export")
def export_all_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> StreamingResponse:
    """Download every table plus the global configuration as a single ZIP archive."""
    archive = build_export_archive(db, generated_by=current_user.username)

    write_audit(
        db,
        action="export_all_data",
        entity_type="Backup",
        entity_id=archive.filename,
        user=current_user,
        new_data=(
            f"tables={len(archive.tables)},rows={archive.total_rows},"
            f"bytes={archive.size_bytes},schema_revision={archive.schema_revision}"
        ),
    )

    def iter_archive() -> Iterator[bytes]:
        try:
            while chunk := archive.stream.read(CHUNK_SIZE):
                yield chunk
        finally:
            archive.stream.close()

    return StreamingResponse(
        iter_archive(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{archive.filename}"',
            "Content-Length": str(archive.size_bytes),
            "X-Export-Rows": str(archive.total_rows),
        },
    )


def _to_result(analysis: ImportAnalysis, imported: bool) -> ImportResultRead:
    return ImportResultRead(
        imported=imported,
        can_import=analysis.can_import,
        format_version=analysis.format_version,
        archive_schema_revision=analysis.archive_schema_revision,
        database_schema_revision=analysis.database_schema_revision,
        archive_generated_at=analysis.archive_generated_at,
        total_current_rows=analysis.total_current_rows,
        total_incoming_rows=analysis.total_incoming_rows,
        tables=[
            ImportTablePlan(name=item.name, current_rows=item.current_rows, incoming_rows=item.incoming_rows)
            for item in analysis.tables
        ],
        errors=analysis.errors,
        warnings=analysis.warnings,
    )


@router.post("/import", response_model=ImportResultRead)
async def import_all_data(
    file: UploadFile = File(...),
    confirmation: str = Form(""),
    validate_only: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> ImportResultRead:
    """Analyse an export archive and, once confirmed, replace all data with it.

    With ``validate_only`` the archive is only inspected. Applying it wipes every table
    and reloads it from the archive in a single transaction.
    """
    content = await file.read()

    if validate_only:
        try:
            return _to_result(analyze_archive(db, content), imported=False)
        except ArchiveImportError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if confirmation != IMPORT_CONFIRMATION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Type "{IMPORT_CONFIRMATION}" to confirm replacing all data.',
        )

    # The interest scheduler must not write while the tables are being replaced.
    if not try_acquire_cycle_lock(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A background interest job is running. Try again in a moment.",
        )

    try:
        analysis = restore_archive(db, content)
    except ArchiveImportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        release_cycle_lock(db)

    write_audit(
        db,
        action="import_all_data",
        entity_type="Backup",
        entity_id=file.filename or "upload.zip",
        user=current_user,
        old_data=f"rows_before={analysis.total_current_rows}",
        new_data=(
            f"rows_after={analysis.total_incoming_rows},"
            f"tables={len(analysis.tables)},schema_revision={analysis.archive_schema_revision}"
        ),
    )

    return _to_result(analysis, imported=True)
