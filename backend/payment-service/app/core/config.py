from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/payment_db"
    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    APP_NAME: str = "Payment Service"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
