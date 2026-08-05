"""Takes one backup and records what happened.

Every attempt writes a ``BackupRun`` row, successful or not. That row is the only way an
operator can tell whether the schedule is working: a Drive authorisation revoked in June and
a scheduler thread that died both look exactly like "nothing happened" from the outside, and
the difference is in the error this records.
"""

import logging

from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import BackupRun, BackupSettings, User, now_utc
from src.modules.backup.destinations import (
    GOOGLE_DRIVE,
    LOCAL_DIRECTORY,
    BackupDestinationError,
    DriveConfiguration,
    StoredBackup,
    store_in_directory,
    store_in_google_drive,
)
from src.modules.backup.google_drive import DriveCredentials
from src.modules.backup.schedule import (
    drive_is_connected,
    ensure_backup_settings,
    resolve_local_directory,
)
from src.modules.backup.service import ExportArchive, build_export_archive
from src.shared.utils.audit import write_audit

logger = logging.getLogger(__name__)

SCHEDULED = "scheduled"
MANUAL = "manual"

# Enough to name the cause without turning the run history into a log file.
MAX_ERROR_LENGTH = 2000


def _store(settings: BackupSettings, archive: ExportArchive) -> StoredBackup:
    if settings.destination == GOOGLE_DRIVE:
        if not drive_is_connected(settings):
            raise BackupDestinationError(
                "Google Drive is not connected. Authorise a Google account before scheduling "
                "backups to Drive."
            )

        stored, folder_id = store_in_google_drive(
            archive,
            DriveConfiguration(
                credentials=DriveCredentials(
                    client_id=settings.drive_client_id or "",
                    client_secret=settings.drive_client_secret or "",
                    refresh_token=settings.drive_refresh_token or "",
                ),
                folder_name=settings.drive_folder_name,
                folder_id=settings.drive_folder_id,
            ),
            settings.retention_copies,
        )

        # Remembering the folder saves a lookup per run, and keeps the UI able to say which
        # folder the copies are in after the first one is created.
        if folder_id != settings.drive_folder_id:
            settings.drive_folder_id = folder_id

        return stored

    if settings.destination == LOCAL_DIRECTORY:
        return store_in_directory(archive, resolve_local_directory(settings), settings.retention_copies)

    raise BackupDestinationError(f"Unknown backup destination {settings.destination!r}.")


def run_backup(db: Session, trigger: str, user: User | None = None) -> BackupRun:
    """Export everything, store it at the configured destination, and record the attempt.

    Never raises for a destination failure: the failure *is* the result, and it belongs in the
    run history where the administrator reads it. A caller that needs to react checks
    ``run.status``.
    """
    settings = ensure_backup_settings(db)
    started_at = now_utc().replace(tzinfo=None)
    triggered_by = user.username if user is not None else None

    run = BackupRun(
        started_at=started_at,
        status="success",
        trigger=trigger,
        destination=settings.destination,
        triggered_by=triggered_by,
    )

    try:
        archive = build_export_archive(db, generated_by=triggered_by or "scheduled backup")
        try:
            stored = _store(settings, archive)
        finally:
            archive.stream.close()

        run.filename = archive.filename
        run.size_bytes = archive.size_bytes
        run.total_rows = archive.total_rows
        run.location = stored.location
        pruned = stored.pruned
    except Exception as exc:
        # The export reads and the destinations write outside the database, but a broken
        # session would stop the run row itself from being inserted.
        db.rollback()
        settings = ensure_backup_settings(db)

        run = BackupRun(
            started_at=started_at,
            status="failed",
            trigger=trigger,
            destination=settings.destination,
            triggered_by=triggered_by,
            error=str(exc)[:MAX_ERROR_LENGTH] or exc.__class__.__name__,
        )
        pruned = 0
        logger.warning("Backup run failed (%s to %s): %s", trigger, run.destination, exc)

    run.finished_at = now_utc().replace(tzinfo=None)
    db.add(run)
    db.flush()

    write_audit(
        db,
        action=f"backup_{run.status}",
        entity_type="BackupRun",
        entity_id=str(run.id),
        user=user,
        new_data=(
            f"trigger={run.trigger},destination={run.destination},file={run.filename or '-'},"
            f"bytes={run.size_bytes or 0},rows={run.total_rows or 0},pruned={pruned}"
            + (f",error={run.error}" if run.error else "")
        ),
        commit=False,
    )

    db.commit()
    db.refresh(run)
    return run
