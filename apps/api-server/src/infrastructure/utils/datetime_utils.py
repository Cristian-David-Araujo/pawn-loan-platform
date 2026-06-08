from datetime import date, datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import GlobalSettings


def get_local_date(db: Session) -> date:
    """Returns the current date using the configured timezone from GlobalSettings."""
    settings = db.get(GlobalSettings, 1)
    tz_name = settings.timezone if settings else "America/Bogota"
    return datetime.now(ZoneInfo(tz_name)).date()


def get_local_datetime(db: Session) -> datetime:
    """Returns the current datetime using the configured timezone from GlobalSettings."""
    settings = db.get(GlobalSettings, 1)
    tz_name = settings.timezone if settings else "America/Bogota"
    return datetime.now(ZoneInfo(tz_name))
