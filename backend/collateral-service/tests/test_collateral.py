import uuid
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
    from app.api.collateral import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_collateral_item(client):
    loan_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/collateral-items",
        json={
            "loan_id": loan_id,
            "item_type": "Jewelry",
            "description": "Gold necklace 18k",
            "appraised_value": "500.00",
            "physical_condition": "good",
            "custody_code": "COD-001",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "received"
    assert data["item_type"] == "Jewelry"


def test_release_collateral(client):
    loan_id = str(uuid.uuid4())
    create_resp = client.post(
        "/api/v1/collateral-items",
        json={
            "loan_id": loan_id,
            "item_type": "Electronics",
            "description": "Laptop",
            "appraised_value": "800.00",
        },
    )
    item_id = create_resp.json()["id"]
    release_resp = client.post(f"/api/v1/collateral-items/{item_id}/release", json={})
    assert release_resp.status_code == 200
    assert release_resp.json()["status"] == "released"


def test_liquidate_collateral(client):
    loan_id = str(uuid.uuid4())
    create_resp = client.post(
        "/api/v1/collateral-items",
        json={
            "loan_id": loan_id,
            "item_type": "Watch",
            "description": "Rolex",
            "appraised_value": "2000.00",
        },
    )
    item_id = create_resp.json()["id"]
    liquidate_resp = client.post(
        f"/api/v1/collateral-items/{item_id}/liquidate",
        json={"sale_amount": "1800.00", "notes": "Sold at auction"},
    )
    assert liquidate_resp.status_code == 200
    assert liquidate_resp.json()["status"] == "sold"
