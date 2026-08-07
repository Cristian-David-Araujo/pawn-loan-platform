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

    # The recurring backup itself is configured from the admin screen and stored in the
    # database — what belongs in the environment is only whether this deployment runs the
    # scheduler thread at all, how often it looks, and where a local copy lands. The
    # directory is a deployment fact (which volume is mounted), not portfolio policy.
    backup_scheduler_enabled: bool = True
    backup_scheduler_interval_minutes: int = 15
    backup_local_directory: str = "/var/backups/pawn-platform"

    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_FILE), extra="ignore")


# Settings whose value the running application *uses*, shipped with a published default.
#
# `ADMIN_PASSWORD` is deliberately **not** here. It only seeds the admin user the first time
# an installation boots; from then on the password lives in the database and the operator
# changes it from the users screen, so the variable goes stale by design. Refusing to start
# over a stale value took production down for no security gain — and it would have missed the
# case that actually matters, a strong variable over a weak stored password.
DEVELOPMENT_DEFAULTS = {
    "jwt_secret_key": "change_this_in_production",
}


def assert_production_secrets(settings: Settings) -> None:
    """Refuse to serve production with a published signing key.

    Only the literal default is rejected, so an installation that set its own value is never
    affected. It fails at startup rather than warning because there is no safe way to serve
    with this one: `change_this_in_production` is in the README and in `.env.example`, so
    anyone can mint a token for any user, administrator included. The fix is a config change
    the operator already controls, and no data is at stake either way.

    Nothing else belongs in this check. A guard that can stop a deployment has to be limited
    to values that are both genuinely unsafe and fixable from the environment alone.
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
