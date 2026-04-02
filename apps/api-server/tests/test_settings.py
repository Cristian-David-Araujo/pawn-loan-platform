from fastapi.testclient import TestClient


def test_settings_default_currency_is_cop(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["currency_code"] == "COP"


def test_settings_can_be_updated(client: TestClient, auth_headers: dict[str, str]) -> None:
    update_response = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={
            "currency_code": "USD",
            "timezone": "America/Bogota",
            "date_format": "DD/MM/YYYY",
            "default_late_penalty_rate": 1.5,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["currency_code"] == "USD"
    assert payload["default_late_penalty_rate"] == 1.5
