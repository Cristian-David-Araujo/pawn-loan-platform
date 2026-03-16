from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import customers
from app.core.config import settings
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
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

app.include_router(customers.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.APP_NAME}
