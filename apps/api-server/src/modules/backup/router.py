from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import User
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
