import uuid
from datetime import date
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
    from app.api.payments import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_payment(client):
    loan_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/payments",
        json={
            "loan_id": loan_id,
            "payment_date": str(date.today()),
            "total_amount": "500.00",
            "allocated_to_interest": "300.00",
            "allocated_to_principal": "200.00",
            "payment_method": "cash",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total_amount"] == "500.00"
    assert data["status"] == "completed"


def test_reverse_payment(client):
    loan_id = str(uuid.uuid4())
    create_resp = client.post(
        "/api/v1/payments",
        json={
            "loan_id": loan_id,
            "payment_date": str(date.today()),
            "total_amount": "200.00",
            "payment_method": "bank_transfer",
        },
    )
    payment_id = create_resp.json()["id"]
    reverse_resp = client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        json={"reason": "Data entry error"},
    )
    assert reverse_resp.status_code == 200
    assert reverse_resp.json()["status"] == "reversed"


def test_list_payments(client):
    response = client.get("/api/v1/payments")
    assert response.status_code == 200
    assert "items" in response.json()
