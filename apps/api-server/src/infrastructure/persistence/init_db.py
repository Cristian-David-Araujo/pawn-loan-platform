from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import Base, SessionLocal, engine
from src.infrastructure.persistence.models import User
from src.infrastructure.persistence.seed import seed_database
from src.infrastructure.security.password import get_password_hash, verify_password


def init_database(seed: bool | None = None, force_seed: bool | None = None) -> None:
    settings = get_settings()
    should_seed = settings.db_seed_on_startup if seed is None else seed
    should_force_seed = settings.db_seed_force if force_seed is None else force_seed

    # In production we can run multiple workers; serialize DB bootstrap to avoid
    # races while creating PostgreSQL ENUM types and initial seed data.
    if engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": 9021001})
            try:
                _run_bootstrap(connection, settings, should_seed, should_force_seed)
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": 9021001})
        return

    _run_bootstrap(None, settings, should_seed, should_force_seed)


def _run_bootstrap(
    connection,
    settings,
    should_seed: bool,
    should_force_seed: bool,
) -> None:
    if connection is None:
        Base.metadata.create_all(bind=engine)
        db_context = SessionLocal()
    else:
        Base.metadata.create_all(bind=connection)
        db_context = Session(bind=connection)

    with db_context as db:
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
        else:
            should_update_admin = False

            if not verify_password(settings.admin_password, existing_admin.hashed_password):
                existing_admin.hashed_password = get_password_hash(settings.admin_password)
                should_update_admin = True

            if existing_admin.role != settings.admin_role:
                existing_admin.role = settings.admin_role
                should_update_admin = True

            if not existing_admin.is_active:
                existing_admin.is_active = True
                should_update_admin = True

            if should_update_admin:
                db.add(existing_admin)
                db.commit()

        if should_seed:
            seed_database(db, force=should_force_seed)
