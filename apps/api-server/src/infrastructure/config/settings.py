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

    db_init_on_startup: bool = True
    db_seed_on_startup: bool = True
    db_seed_force: bool = False

    model_config = SettingsConfigDict(env_file=str(ROOT_ENV_FILE), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
