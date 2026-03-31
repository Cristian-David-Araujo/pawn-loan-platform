from sqlalchemy import select

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import Base, SessionLocal, engine
from src.infrastructure.persistence.models import User
from src.infrastructure.persistence.seed import seed_database
from src.infrastructure.security.password import get_password_hash


def init_database(seed: bool | None = None, force_seed: bool | None = None) -> None:
    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    should_seed = settings.db_seed_on_startup if seed is None else seed
    should_force_seed = settings.db_seed_force if force_seed is None else force_seed

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

        if should_seed:
            seed_database(db, force=should_force_seed)
