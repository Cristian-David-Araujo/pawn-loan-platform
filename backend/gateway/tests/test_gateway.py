import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_resource_returns_404(client):
    with patch("app.api.proxy.proxy_request") as mock_proxy:
        response = client.get("/api/v1/unknown-resource/123")
        assert response.status_code == 404
