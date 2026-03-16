import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app


def mock_get_current_user():
    return {"sub": "test-user", "username": "testuser"}


def mock_get_token():
    return "fake-token"


@pytest.fixture
def client():
    from app.api.reports import get_current_user, get_token
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_token] = mock_get_token
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_active_loans_report_service_unavailable(client):
    with patch("app.services.reporting_service.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Connection refused")
        response = client.get("/api/v1/reports/active-loans")
        assert response.status_code == 503
