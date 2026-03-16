from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    IDENTITY_SERVICE_URL: str = "http://identity-service:8001"
    CUSTOMER_SERVICE_URL: str = "http://customer-service:8002"
    LOAN_SERVICE_URL: str = "http://loan-service:8003"
    COLLATERAL_SERVICE_URL: str = "http://collateral-service:8004"
    FINANCE_SERVICE_URL: str = "http://finance-service:8005"
    PAYMENT_SERVICE_URL: str = "http://payment-service:8006"
    REPORTING_SERVICE_URL: str = "http://reporting-service:8007"
    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    APP_NAME: str = "API Gateway"
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
