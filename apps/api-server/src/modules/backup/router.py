import secrets
from collections.abc import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import BackupRun, BackupSettings, User
from src.infrastructure.tasks.interest_scheduler import interest_cycle_lock
from src.modules.backup.destinations import (
    GOOGLE_DRIVE,
    LOCAL_DIRECTORY,
    BackupDestinationError,
    describe_directory_writability,
)
from src.modules.backup.google_drive import (
    DriveCredentials,
    GoogleDriveError,
    build_authorization_url,
    ensure_folder,
    exchange_authorization_code,
    fetch_access_token,
)
from src.modules.backup.restore import (
    IMPORT_CONFIRMATION,
    ArchiveImportError,
    ImportAnalysis,
    analyze_archive,
    restore_archive,
)
from src.modules.backup.runner import MANUAL, run_backup
from src.modules.backup.schedule import (
    drive_is_connected,
    ensure_backup_settings,
    local_now,
    next_run_at,
    resolve_local_directory,
)
from src.modules.backup.schemas import (
    BackupRunRead,
    BackupScheduleRead,
    BackupScheduleUpdate,
    DestinationTestRead,
    DriveAuthorizationRead,
    DriveAuthorizationStart,
    DriveConnectRequest,
    ImportResultRead,
    ImportTablePlan,
)
from src.modules.backup.service import build_export_archive
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/backup", tags=["backup"])

CHUNK_SIZE = 64 * 1024

# How many attempts the history screen shows. Long enough to see a schedule that has been
# failing for weeks, short enough to stay one small response.
RUN_HISTORY_LIMIT = 50


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
    with interest_cycle_lock(db) as acquired:
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A background interest job is running. Try again in a moment.",
            )

        try:
            analysis = restore_archive(db, content)
        except ArchiveImportError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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


def _recent_runs(db: Session, limit: int = RUN_HISTORY_LIMIT) -> list[BackupRun]:
    return list(db.scalars(select(BackupRun).order_by(BackupRun.started_at.desc(), BackupRun.id.desc()).limit(limit)))


def _last_run(db: Session, only_successful: bool = False) -> BackupRun | None:
    statement = select(BackupRun).order_by(BackupRun.started_at.desc(), BackupRun.id.desc()).limit(1)
    if only_successful:
        statement = statement.where(BackupRun.status == "success")
    return db.scalars(statement).first()


def _to_schedule(db: Session, settings: BackupSettings) -> BackupScheduleRead:
    return BackupScheduleRead(
        enabled=settings.enabled,
        frequency=settings.frequency,
        hour=settings.hour,
        day_of_week=settings.day_of_week,
        day_of_month=settings.day_of_month,
        destination=settings.destination,
        local_directory=settings.local_directory or "",
        local_directory_effective=resolve_local_directory(settings),
        retention_copies=settings.retention_copies,
        drive_connected=drive_is_connected(settings),
        drive_account_email=settings.drive_account_email,
        drive_folder_name=settings.drive_folder_name,
        drive_folder_id=settings.drive_folder_id,
        # Only meaningful while the schedule is on; reporting a next run for a disabled
        # schedule would say a copy is coming when none is.
        next_run_at=next_run_at(settings, local_now(db)) if settings.enabled else None,
        last_run=_read_run(_last_run(db)),
        last_successful_run=_read_run(_last_run(db, only_successful=True)),
    )


def _read_run(run: BackupRun | None) -> BackupRunRead | None:
    return BackupRunRead.model_validate(run) if run is not None else None


@router.get("/schedule", response_model=BackupScheduleRead)
def get_backup_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> BackupScheduleRead:
    """The recurring backup schedule and how the last attempts went."""
    return _to_schedule(db, ensure_backup_settings(db))


@router.put("/schedule", response_model=BackupScheduleRead)
def update_backup_schedule(
    payload: BackupScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> BackupScheduleRead:
    settings = ensure_backup_settings(db)

    # Turning the schedule on with a destination that cannot receive a copy would report a
    # protected installation and produce nothing until someone read the run history.
    if payload.enabled and payload.destination == GOOGLE_DRIVE and not drive_is_connected(settings):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Connect a Google account before scheduling backups to Google Drive.",
        )

    settings.enabled = payload.enabled
    settings.frequency = payload.frequency
    settings.hour = payload.hour
    settings.day_of_week = payload.day_of_week
    settings.day_of_month = payload.day_of_month
    settings.destination = payload.destination
    settings.local_directory = (payload.local_directory or "").strip() or None
    settings.retention_copies = payload.retention_copies

    folder_name = (payload.drive_folder_name or "").strip()
    if folder_name and folder_name != settings.drive_folder_name:
        settings.drive_folder_name = folder_name
        # The stored id belongs to the previous name; keeping it would upload into a folder
        # the operator no longer believes is the destination.
        settings.drive_folder_id = None

    db.commit()
    db.refresh(settings)

    write_audit(
        db,
        action="update_backup_schedule",
        entity_type="BackupSettings",
        entity_id=str(settings.id),
        user=current_user,
        new_data=(
            f"enabled={settings.enabled},frequency={settings.frequency},hour={settings.hour},"
            f"day_of_week={settings.day_of_week},day_of_month={settings.day_of_month},"
            f"destination={settings.destination},retention_copies={settings.retention_copies}"
        ),
    )

    return _to_schedule(db, settings)


@router.post("/schedule/run-now", response_model=BackupRunRead)
def run_backup_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> BackupRunRead:
    """Take a copy immediately, to the configured destination.

    A failure comes back as a run with ``status='failed'`` and its error rather than as an
    HTTP error: the attempt is recorded either way, and the screen shows both the same way.
    """
    run = run_backup(db, trigger=MANUAL, user=current_user)
    return BackupRunRead.model_validate(run)


@router.get("/runs", response_model=list[BackupRunRead])
def list_backup_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> list[BackupRunRead]:
    return [BackupRunRead.model_validate(run) for run in _recent_runs(db)]


@router.post("/destination/test", response_model=DestinationTestRead)
def test_backup_destination(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> DestinationTestRead:
    """Prove the destination can receive a copy, without producing one.

    Worth its own endpoint because the alternative is finding out at 2am: a read-only volume
    and a revoked Drive authorisation both look like a working configuration until the first
    scheduled copy is attempted.
    """
    settings = ensure_backup_settings(db)

    if settings.destination == GOOGLE_DRIVE:
        if not drive_is_connected(settings):
            return DestinationTestRead(
                ok=False, destination=settings.destination, detail="No Google account is connected."
            )

        try:
            access_token = fetch_access_token(
                DriveCredentials(
                    client_id=settings.drive_client_id or "",
                    client_secret=settings.drive_client_secret or "",
                    refresh_token=settings.drive_refresh_token or "",
                )
            )
            folder_id = ensure_folder(access_token, settings.drive_folder_name, settings.drive_folder_id)
        except GoogleDriveError as exc:
            return DestinationTestRead(ok=False, destination=settings.destination, detail=str(exc))

        if folder_id != settings.drive_folder_id:
            settings.drive_folder_id = folder_id
            db.commit()

        return DestinationTestRead(
            ok=True,
            destination=settings.destination,
            detail=f"{settings.drive_folder_name} ({folder_id})",
        )

    try:
        directory = describe_directory_writability(resolve_local_directory(settings))
    except BackupDestinationError as exc:
        return DestinationTestRead(ok=False, destination=settings.destination, detail=str(exc))

    return DestinationTestRead(ok=True, destination=settings.destination, detail=directory)


@router.post("/drive/authorize", response_model=DriveAuthorizationRead)
def start_drive_authorization(
    payload: DriveAuthorizationStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> DriveAuthorizationRead:
    """Store the OAuth client and hand back the Google consent URL to open.

    The ``state`` is generated here and checked by the client against what it stored before
    opening the URL. That check is what stops a crafted ``?code=`` link from connecting the
    installation to somebody else's Drive.
    """
    settings = ensure_backup_settings(db)

    settings.drive_client_id = payload.client_id.strip()
    settings.drive_client_secret = payload.client_secret.strip()
    db.commit()

    state = secrets.token_urlsafe(24)
    return DriveAuthorizationRead(
        authorization_url=build_authorization_url(
            client_id=settings.drive_client_id,
            redirect_uri=payload.redirect_uri,
            state=state,
        ),
        redirect_uri=payload.redirect_uri,
        state=state,
    )


@router.post("/drive/connect", response_model=BackupScheduleRead)
def connect_drive_account(
    payload: DriveConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> BackupScheduleRead:
    """Exchange the consent code for a refresh token and create the destination folder."""
    settings = ensure_backup_settings(db)

    if not settings.drive_client_id or not settings.drive_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start the Google authorisation before sending the code.",
        )

    try:
        account = exchange_authorization_code(
            client_id=settings.drive_client_id,
            client_secret=settings.drive_client_secret,
            code=payload.code.strip(),
            redirect_uri=payload.redirect_uri,
        )
        access_token = fetch_access_token(
            DriveCredentials(
                client_id=settings.drive_client_id,
                client_secret=settings.drive_client_secret,
                refresh_token=account.refresh_token,
            )
        )
        folder_id = ensure_folder(access_token, settings.drive_folder_name, None)
    except GoogleDriveError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    settings.drive_refresh_token = account.refresh_token
    settings.drive_account_email = account.email
    settings.drive_folder_id = folder_id
    db.commit()
    db.refresh(settings)

    write_audit(
        db,
        action="connect_backup_drive",
        entity_type="BackupSettings",
        entity_id=str(settings.id),
        user=current_user,
        new_data=f"account={settings.drive_account_email or 'unknown'},folder={folder_id}",
    )

    return _to_schedule(db, settings)


@router.post("/drive/disconnect", response_model=BackupScheduleRead)
def disconnect_drive_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> BackupScheduleRead:
    """Forget the Google credentials, and stop a schedule that now has nowhere to write.

    Leaving the schedule enabled and pointed at Drive would keep failing every slot; the
    honest outcome of removing the destination is that the schedule is off.
    """
    settings = ensure_backup_settings(db)
    previous_account = settings.drive_account_email

    settings.drive_client_id = None
    settings.drive_client_secret = None
    settings.drive_refresh_token = None
    settings.drive_account_email = None
    settings.drive_folder_id = None

    if settings.destination == GOOGLE_DRIVE:
        settings.enabled = False
        settings.destination = LOCAL_DIRECTORY

    db.commit()
    db.refresh(settings)

    write_audit(
        db,
        action="disconnect_backup_drive",
        entity_type="BackupSettings",
        entity_id=str(settings.id),
        user=current_user,
        old_data=f"account={previous_account or 'unknown'}",
    )

    return _to_schedule(db, settings)
