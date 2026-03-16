from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/customer_db"
    IDENTITY_SERVICE_URL: str = "http://identity-service:8001"
    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    APP_NAME: str = "Customer Service"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
