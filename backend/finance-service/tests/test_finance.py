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
    from app.api.finance import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_generate_interest(client):
    loan_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/interest/generate",
        json={
            "loan_id": loan_id,
            "principal_base": "10000.00",
            "interest_rate": "0.05",
            "period_start": "2025-01-01",
            "period_end": "2025-01-31",
            "charge_date": "2025-02-01",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "500.00"
    assert data["status"] == "pending"


def test_duplicate_interest_rejected(client):
    loan_id = str(uuid.uuid4())
    payload = {
        "loan_id": loan_id,
        "principal_base": "5000.00",
        "interest_rate": "0.03",
        "period_start": "2025-02-01",
        "period_end": "2025-02-28",
        "charge_date": "2025-03-01",
    }
    client.post("/api/v1/interest/generate", json=payload)
    response = client.post("/api/v1/interest/generate", json=payload)
    assert response.status_code == 400


def test_get_balance(client):
    loan_id = str(uuid.uuid4())
    client.post(
        "/api/v1/interest/generate",
        json={
            "loan_id": loan_id,
            "principal_base": "1000.00",
            "interest_rate": "0.05",
            "period_start": "2025-03-01",
            "period_end": "2025-03-31",
            "charge_date": "2025-04-01",
        },
    )
    response = client.get(f"/api/v1/loans/{loan_id}/balance?outstanding_principal=1000.00")
    assert response.status_code == 200
    data = response.json()
    assert data["total_pending_interest"] == "50.00"
    assert data["total_outstanding"] == "1050.00"
