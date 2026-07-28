from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_root_env_file() -> str:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / ".env"
        if candidate.exists():
            return str(candidate)

    # Fallback for environments where .env is not present yet
    return str(current.parents[3] / ".env")


ROOT_ENV_FILE = _resolve_root_env_file()


class Settings(BaseSettings):
    app_name: str = "Pawn Loan API"
    app_env: str = "development"

    database_url: str = "postgresql+psycopg://pawn_user:pawn_password@localhost:5432/pawn_loan_db"

    jwt_secret_key: str = "change_this_in_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_role: str = "administrator"
    admin_password_reset_on_startup: bool = False

    db_init_on_startup: bool = True
    db_seed_on_startup: bool = True
    db_seed_force: bool = False

    auto_interest_generation_enabled: bool = True
    auto_interest_generation_interval_minutes: int = 1440

    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_FILE), extra="ignore")


# The values shipped in `.env.example` and printed in the README. Convenient in development,
# and an unlocked front door in production.
DEVELOPMENT_DEFAULTS = {
    "admin_password": "admin123",
    "jwt_secret_key": "change_this_in_production",
}


def assert_production_secrets(settings: Settings) -> None:
    """Refuse to serve production with the documented development credentials.

    Only the literal defaults are rejected, so an installation that already set its own
    values is never affected. It fails at startup rather than warning, because a warning in a
    container log is a warning nobody reads: `admin` / `admin123` appears in the README, in
    `.env.example` and in the seed, and a public deployment keeping it is an open door — and
    the JWT signing key being the published string means anyone can mint their own token.
    """
    if settings.app_env.strip().lower() != "production":
        return

    unchanged = [name for name, default in DEVELOPMENT_DEFAULTS.items() if getattr(settings, name) == default]
    if unchanged:
        raise RuntimeError(
            "Refusing to start with development credentials in production. "
            f"Set these in the environment: {', '.join(sorted(name.upper() for name in unchanged))}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
