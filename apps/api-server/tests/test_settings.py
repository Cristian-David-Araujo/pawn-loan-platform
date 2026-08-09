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
            "company_name": "Nelsy Araujo",
            "currency_code": "USD",
            "timezone": "America/Bogota",
            "date_format": "DD/MM/YYYY",
            "default_late_penalty_rate": 1.5,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["company_name"] == "Nelsy Araujo"
    assert payload["currency_code"] == "USD"
    assert payload["default_late_penalty_rate"] == 1.5


def test_the_product_name_cannot_be_changed(client: TestClient, auth_headers: dict[str, str]) -> None:
    """`app_name` is the product's name, not an installation's choice.

    It is still *read* — the sidebar and the login card show it — so removing it from the
    response would break both. What it must not be is writable: it used to sit in the same
    form as `company_name`, one field away from the name the installation genuinely does
    choose, and that is how a deployment ended up able to rename the product from a text box.

    An older client that still sends the field is ignored rather than rejected, so a browser
    tab left open across the deploy still saves the rest of the form.
    """
    before = client.get("/api/v1/settings", headers=auth_headers).json()["app_name"]

    response = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={
            "app_name": "My Pawn Shop",
            "company_name": "Nelsy Araujo",
            "currency_code": "COP",
            "timezone": "America/Bogota",
            "date_format": "DD/MM/YYYY",
            "default_late_penalty_rate": 1.5,
        },
    )

    assert response.status_code == 200, "a stale client sending the field must not fail the save"
    assert response.json()["app_name"] == before
    assert response.json()["company_name"] == "Nelsy Araujo", "the rest of the form still saved"
