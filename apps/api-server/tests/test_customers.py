from fastapi.testclient import TestClient


def test_create_customer_and_prevent_duplicate(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "first_name": "Juan",
        "last_name": "Lopez",
        "document_type": "ID",
        "document_number": "CUST-100",
        "phone": "5551000",
        "email": "juan@example.com",
        "address": "Street 123",
        "city": "Lima",
        "status": "active",
    }

    create_response = client.post("/api/v1/customers", headers=auth_headers, json=payload)
    assert create_response.status_code == 201

    duplicate_response = client.post("/api/v1/customers", headers=auth_headers, json=payload)
    assert duplicate_response.status_code == 409


def test_list_filter_get_and_update_customer(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "first_name": "Maria",
        "last_name": "Gomez",
        "document_type": "ID",
        "document_number": "CUST-200",
        "phone": "5552000",
        "email": "maria@example.com",
        "address": "Av 45",
        "city": "Bogota",
        "status": "active",
    }

    create_response = client.post("/api/v1/customers", headers=auth_headers, json=payload)
    customer_id = create_response.json()["id"]

    list_response = client.get("/api/v1/customers?q=Gomez", headers=auth_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/api/v1/customers/{customer_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["document_number"] == "CUST-200"

    update_response = client.put(
        f"/api/v1/customers/{customer_id}",
        headers=auth_headers,
        json={"city": "Medellin", "phone": "5559999"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["city"] == "Medellin"
    assert update_response.json()["phone"] == "5559999"
