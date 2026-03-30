from collections.abc import Generator

from src.infrastructure.persistence.database import SessionLocal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
