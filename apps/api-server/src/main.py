from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1.router import api_router
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import engine
from src.infrastructure.persistence.init_db import init_database
from src.infrastructure.tasks.interest_scheduler import InterestGenerationScheduler

settings = get_settings()
interest_scheduler = InterestGenerationScheduler(interval_minutes=settings.auto_interest_generation_interval_minutes)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    if settings.db_init_on_startup:
        init_database()

    if settings.auto_interest_generation_enabled:
        interest_scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    interest_scheduler.stop()


@app.get("/health", tags=["system"])
def health() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": str(exc.__class__.__name__)},
        )

    return JSONResponse(status_code=200, content={"status": "ok"})


app.include_router(api_router, prefix="/api/v1")
