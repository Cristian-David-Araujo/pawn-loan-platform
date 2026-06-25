from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import User
from src.infrastructure.security.password import get_password_hash


def test_login_success(client: TestClient, admin_user: User) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_failure_invalid_password(client: TestClient, admin_user: User) -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_create_and_list_users_as_administrator(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    create_response = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={"username": "officer", "password": "officer123", "role": "loan_officer"},
    )
    assert create_response.status_code == 201

    list_response = client.get("/api/v1/users", headers=auth_headers)
    assert list_response.status_code == 200
    usernames = [item["username"] for item in list_response.json()]
    assert "officer" in usernames


def test_non_admin_cannot_list_users(client: TestClient, db_session: Session) -> None:
    user = User(
        username="regular",
        hashed_password=get_password_hash("regular123"),
        role="loan_officer",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post("/api/v1/auth/login", json={"username": "regular", "password": "regular123"})
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403


def test_forgot_password_and_reset_flow(client: TestClient, admin_user: User) -> None:
    # 1. Request password recovery for existing user
    forgot_res = client.post("/api/v1/auth/forgot-password", json={"username_or_email": "admin"})
    assert forgot_res.status_code == 200
    data = forgot_res.json()
    assert "reset_token" in data
    token = data["reset_token"]
    assert token is not None

    # 2. Reset password using the generated token
    reset_res = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "supersecurenewpassword123"})
    assert reset_res.status_code == 200
    assert reset_res.json()["message"] == "Contraseña actualizada exitosamente"

    # 3. Verify login works with new password
    login_res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "supersecurenewpassword123"})
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


def test_forgot_password_anti_enumeration(client: TestClient) -> None:
    # Request recovery for non-existent user should return exact same 200 OK status and message
    res = client.post("/api/v1/auth/forgot-password", json={"username_or_email": "fakeuser_never_exists"})
    assert res.status_code == 200
    assert res.json()["message"] == "Si la cuenta existe y está activa, recibirás instrucciones para restablecer tu contraseña."
    assert res.json()["reset_token"] is None


def test_reset_password_invalid_token(client: TestClient) -> None:
    res = client.post("/api/v1/auth/reset-password", json={"token": "invalid_or_expired_token", "new_password": "newpassword123"})
    assert res.status_code == 400
    assert "inválido o expirado" in res.json()["detail"]

