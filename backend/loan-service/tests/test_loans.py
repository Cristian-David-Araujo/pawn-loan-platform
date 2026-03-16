import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def mock_get_current_user():
    return {"sub": str(uuid.uuid4()), "username": "testuser"}


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from app.api.loan_applications import get_current_user as app_get_current_user
    from app.api.loans import get_current_user as loans_get_current_user
    app.dependency_overrides[app_get_current_user] = mock_get_current_user
    app.dependency_overrides[loans_get_current_user] = mock_get_current_user
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_application(client):
    customer_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/loan-applications",
        json={
            "customer_id": customer_id,
            "loan_type": "personal",
            "requested_amount": "5000.00",
            "monthly_interest_rate": "0.05",
            "term_months": 12,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "submitted"
    assert data["customer_id"] == customer_id


def test_approve_application(client):
    customer_id = str(uuid.uuid4())
    app_resp = client.post(
        "/api/v1/loan-applications",
        json={
            "customer_id": customer_id,
            "loan_type": "personal",
            "requested_amount": "3000.00",
            "monthly_interest_rate": "0.03",
            "term_months": 6,
        },
    )
    app_id = app_resp.json()["id"]
    approve_resp = client.post(f"/api/v1/loan-applications/{app_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"


def test_create_loan_from_approved_application(client):
    customer_id = str(uuid.uuid4())
    app_resp = client.post(
        "/api/v1/loan-applications",
        json={
            "customer_id": customer_id,
            "loan_type": "personal",
            "requested_amount": "2000.00",
            "monthly_interest_rate": "0.04",
            "term_months": 3,
        },
    )
    app_id = app_resp.json()["id"]
    client.post(f"/api/v1/loan-applications/{app_id}/approve")
    loan_resp = client.post(
        "/api/v1/loans",
        json={
            "application_id": app_id,
            "principal_amount": "2000.00",
            "monthly_interest_rate": "0.04",
            "disbursement_date": datetime.now(timezone.utc).isoformat(),
            "due_day": 15,
            "term_months": 3,
            "disbursement_method": "cash",
        },
    )
    assert loan_resp.status_code == 201
    loan_data = loan_resp.json()
    assert loan_data["status"] == "active"
    assert loan_data["outstanding_principal"] == "2000.00"


def test_list_loans(client):
    response = client.get("/api/v1/loans")
    assert response.status_code == 200
    assert "items" in response.json()
