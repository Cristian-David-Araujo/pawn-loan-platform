import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

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
    return {"sub": "test-user-id", "username": "testuser"}


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    from app.api.customers import get_current_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_create_customer(client):
    response = client.post(
        "/api/v1/customers",
        json={
            "first_name": "Juan",
            "last_name": "Garcia",
            "document_type": "CC",
            "document_number": "123456789",
            "phone": "3001234567",
            "email": "juan@test.com",
            "city": "Bogota",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Juan"
    assert data["document_number"] == "123456789"
    assert data["status"] == "active"


def test_create_customer_duplicate_document(client):
    payload = {
        "first_name": "Juan",
        "last_name": "Garcia",
        "document_type": "CC",
        "document_number": "123456789",
    }
    client.post("/api/v1/customers", json=payload)
    response = client.post("/api/v1/customers", json=payload)
    assert response.status_code == 400


def test_list_customers(client):
    client.post(
        "/api/v1/customers",
        json={"first_name": "Ana", "last_name": "Lopez", "document_type": "CC", "document_number": "111"},
    )
    response = client.get("/api/v1/customers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


def test_get_customer_not_found(client):
    import uuid
    response = client.get(f"/api/v1/customers/{uuid.uuid4()}")
    assert response.status_code == 404


def test_update_customer(client):
    create_resp = client.post(
        "/api/v1/customers",
        json={"first_name": "Maria", "last_name": "Torres", "document_type": "CC", "document_number": "999"},
    )
    customer_id = create_resp.json()["id"]
    update_resp = client.put(f"/api/v1/customers/{customer_id}", json={"city": "Medellin"})
    assert update_resp.status_code == 200
    assert update_resp.json()["city"] == "Medellin"
