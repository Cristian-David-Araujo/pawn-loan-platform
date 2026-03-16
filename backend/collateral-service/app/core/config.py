from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/collateral_db"
    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    APP_NAME: str = "Collateral Service"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
