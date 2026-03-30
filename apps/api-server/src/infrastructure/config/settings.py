from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
