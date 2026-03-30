from collections.abc import Callable, Generator
from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.v1.router import api_router
from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence.models import User
from src.infrastructure.security.password import get_password_hash
from src.shared.dependencies.db import get_db


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def app(db_session: Session) -> FastAPI:
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_credentials() -> dict[str, str]:
    return {"username": "admin", "password": "admin123"}


@pytest.fixture
def admin_user(db_session: Session, admin_credentials: dict[str, str]) -> User:
    user = User(
        username=admin_credentials["username"],
        hashed_password=get_password_hash(admin_credentials["password"]),
        role="administrator",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(
    client: TestClient,
    admin_user: User,
    admin_credentials: dict[str, str],
) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json=admin_credentials)
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def create_customer(client: TestClient, auth_headers: dict[str, str]) -> Callable[..., dict[str, Any]]:
    def _create_customer(document_number: str = "DOC-001") -> dict[str, Any]:
        payload = {
            "first_name": "Ana",
            "last_name": "Perez",
            "document_type": "ID",
            "document_number": document_number,
            "phone": "5550001",
            "email": "ana@example.com",
            "address": "Main St",
            "city": "Quito",
            "status": "active",
        }
        response = client.post("/api/v1/customers", headers=auth_headers, json=payload)
        assert response.status_code == 201
        return response.json()

    return _create_customer


@pytest.fixture
def create_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def _create_loan(principal: float = 1000.0) -> dict[str, Any]:
        customer = create_customer(document_number=f"DOC-{int(principal * 10)}")
        payload = {
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": principal,
            "monthly_interest_rate": 10.0,
            "disbursement_date": str(date.today()),
            "due_day": 5,
        }
        response = client.post("/api/v1/loans", headers=auth_headers, json=payload)
        assert response.status_code == 201
        return response.json()

    return _create_loan
