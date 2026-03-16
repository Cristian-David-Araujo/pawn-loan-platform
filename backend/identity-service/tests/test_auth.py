import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.repositories.user_repository import UserRepository

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


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user(setup_db):
    db = TestingSessionLocal()
    repo = UserRepository(db)
    role = repo.create_role("administrator", "Admin role")
    user = repo.create("admin", "admin@test.com", "secret123", "Admin User")
    repo.assign_role(user, role)
    db.close()
    return {"username": "admin", "password": "secret123"}


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secret123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 401


def test_create_user(client):
    response = client.post(
        "/api/v1/users",
        json={"username": "newuser", "email": "new@test.com", "password": "pass123"},
    )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"


def test_get_me(client, admin_user):
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secret123"},
    )
    token = login_resp.json()["access_token"]
    me_resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"
