"""The recurring backup schedule: reading it, and deciding when it is due.

Slots are computed in the portfolio's own timezone (``GlobalSettings.timezone``), because
"every day at 2am" is a statement about the business's clock, not the server's. Everything
persisted stays UTC-naive like the rest of the models.
"""

import calendar
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.models import BackupRun, BackupSettings, GlobalSettings

DAILY = "daily"
WEEKLY = "weekly"
MONTHLY = "monthly"
FREQUENCIES = (DAILY, WEEKLY, MONTHLY)

# The day of the month is capped so a schedule can never point at a day some months lack:
# "the 31st" would silently skip February.
MAX_DAY_OF_MONTH = 28

# A slot that keeps failing is retried a few times and then left alone until the next one.
# Without a cap the scheduler retries every wake-up, and a revoked Drive token fills the run
# history with hundreds of identical rows — burying the first failure, which is the one that
# says what broke.
MAX_ATTEMPTS_PER_SLOT = 3


def ensure_backup_settings(db: Session) -> BackupSettings:
    """The single ``id=1`` row, created on demand — same shape as ``GlobalSettings``."""
    settings = db.get(BackupSettings, 1)
    if settings is None:
        settings = BackupSettings(id=1, local_directory=get_settings().backup_local_directory)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def resolve_local_directory(settings: BackupSettings) -> str:
    """Configured directory, falling back to the deployment default from the environment."""
    configured = (settings.local_directory or "").strip()
    return configured or get_settings().backup_local_directory


def portfolio_timezone(db: Session) -> ZoneInfo:
    global_settings = db.get(GlobalSettings, 1)
    name = global_settings.timezone if global_settings is not None else "America/Bogota"
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("America/Bogota")


def local_now(db: Session) -> datetime:
    return datetime.now(portfolio_timezone(db))


def to_naive_utc(moment: datetime) -> datetime:
    """Match how the models store time: UTC with the offset dropped."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


def _at_hour(moment: datetime, hour: int) -> datetime:
    return moment.replace(hour=max(0, min(23, hour)), minute=0, second=0, microsecond=0)


def _shift_month(moment: datetime, months: int) -> datetime:
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def last_due_slot(settings: BackupSettings, now_local: datetime) -> datetime:
    """The most recent moment the schedule called for, at or before ``now_local``.

    Comparing against this — rather than against "did we run in the last 24 hours" — is what
    makes a missed slot get picked up. A server that was off at 2am takes the copy as soon as
    it comes back, and takes exactly one.
    """
    hour = max(0, min(23, settings.hour))

    if settings.frequency == WEEKLY:
        target = max(1, min(7, settings.day_of_week))
        candidate = _at_hour(now_local, hour)
        days_back = (now_local.isoweekday() - target) % 7
        candidate -= timedelta(days=days_back)
        if candidate > now_local:
            candidate -= timedelta(days=7)
        return candidate

    if settings.frequency == MONTHLY:
        day = max(1, min(MAX_DAY_OF_MONTH, settings.day_of_month))
        candidate = _at_hour(now_local.replace(day=day), hour)
        if candidate > now_local:
            candidate = _shift_month(candidate, -1)
        return candidate

    candidate = _at_hour(now_local, hour)
    if candidate > now_local:
        candidate -= timedelta(days=1)
    return candidate


def next_run_at(settings: BackupSettings, now_local: datetime) -> datetime:
    """The next moment the schedule calls for, strictly after ``now_local``."""
    hour = max(0, min(23, settings.hour))

    if settings.frequency == WEEKLY:
        target = max(1, min(7, settings.day_of_week))
        candidate = _at_hour(now_local, hour)
        days_ahead = (target - now_local.isoweekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now_local:
            candidate += timedelta(days=7)
        return candidate

    if settings.frequency == MONTHLY:
        day = max(1, min(MAX_DAY_OF_MONTH, settings.day_of_month))
        candidate = _at_hour(now_local.replace(day=day), hour)
        if candidate <= now_local:
            candidate = _shift_month(candidate, 1)
        return candidate

    candidate = _at_hour(now_local, hour)
    if candidate <= now_local:
        candidate += timedelta(days=1)
    return candidate


def is_backup_due(db: Session, settings: BackupSettings, now_local: datetime) -> bool:
    """Whether the current slot still needs a copy.

    Only *scheduled* runs count. A manual "back up now" is the operator taking an extra copy;
    letting it satisfy the schedule would mean a manual run at 1am silently cancels the 2am
    one, and the operator would have no way to tell.
    """
    if not settings.enabled:
        return False

    slot_started_after = to_naive_utc(last_due_slot(settings, now_local))

    attempts = db.execute(
        select(BackupRun.status, func.count())
        .where(BackupRun.trigger == "scheduled", BackupRun.started_at >= slot_started_after)
        .group_by(BackupRun.status)
    ).all()

    counts = {status: count for status, count in attempts}
    if counts.get("success"):
        return False

    return counts.get("failed", 0) < MAX_ATTEMPTS_PER_SLOT


def drive_is_connected(settings: BackupSettings) -> bool:
    return bool(settings.drive_client_id and settings.drive_client_secret and settings.drive_refresh_token)
