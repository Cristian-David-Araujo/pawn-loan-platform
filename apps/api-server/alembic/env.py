from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence import models as _models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    # `disable_existing_loggers=False` is load-bearing, not tidiness. `fileConfig` defaults to
    # True, which switches off every logger configured before it runs — and this file is not
    # only executed by the `alembic` CLI: `run_database_migrations()` calls it **in-process** on
    # API startup, after uvicorn has set up its own. Production served with `uvicorn.access`
    # silenced from the first boot, so there was no request log at all: a login that never
    # reached the server and one rejected by it looked exactly the same from the outside.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
