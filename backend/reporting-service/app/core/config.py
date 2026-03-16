from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service URLs for cross-service queries
    LOAN_SERVICE_URL: str = "http://loan-service:8003"
    CUSTOMER_SERVICE_URL: str = "http://customer-service:8002"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8006"
    COLLATERAL_SERVICE_URL: str = "http://collateral-service:8004"
    FINANCE_SERVICE_URL: str = "http://finance-service:8005"
    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    APP_NAME: str = "Reporting Service"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
