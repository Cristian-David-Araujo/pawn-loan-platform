from fastapi import FastAPI

from src.api.v1.router import api_router
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.init_db import init_database

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
def startup_event() -> None:
    init_database()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
