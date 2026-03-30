from sqlalchemy import select

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import Base, SessionLocal, engine
from src.infrastructure.persistence.models import User
from src.infrastructure.security.password import get_password_hash


def init_database() -> None:
    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    with SessionLocal() as db:
        existing_admin = db.scalar(select(User).where(User.username == settings.admin_username))
        if existing_admin is None:
            db.add(
                User(
                    username=settings.admin_username,
                    hashed_password=get_password_hash(settings.admin_password),
                    role=settings.admin_role,
                    is_active=True,
                )
            )
            db.commit()
