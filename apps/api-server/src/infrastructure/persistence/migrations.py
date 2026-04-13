from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from src.infrastructure.config.settings import get_settings


def run_database_migrations(target_revision: str = "head") -> None:
    settings = get_settings()
    base_dir = Path(__file__).resolve().parents[3]
    alembic_ini = base_dir / "alembic.ini"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(base_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)

    command.upgrade(config, target_revision)
