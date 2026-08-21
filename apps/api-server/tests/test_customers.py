from fastapi.testclient import TestClient


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"


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
        json={
            "first_name": "Maria Elena",
            "last_name": "Garcia",
            "document_type": "PASSPORT",
            "document_number": "CUST-201",
            "city": "Medellin",
            "phone": "5559999",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["first_name"] == "Maria Elena"
    assert update_response.json()["last_name"] == "Garcia"
    assert update_response.json()["document_type"] == "PASSPORT"
    assert update_response.json()["document_number"] == "CUST-201"
    assert update_response.json()["city"] == "Medellin"
    assert update_response.json()["phone"] == "5559999"


def test_update_customer_rejects_duplicate_document(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = {
        "first_name": "Ana",
        "last_name": "Lopez",
        "document_type": "ID",
        "document_number": "CUST-300",
        "phone": "5553000",
        "city": "Quito",
    }
    second = {
        "first_name": "Pedro",
        "last_name": "Rios",
        "document_type": "ID",
        "document_number": "CUST-301",
        "phone": "5553001",
        "city": "Quito",
    }

    first_response = client.post("/api/v1/customers", headers=auth_headers, json=first)
    second_response = client.post("/api/v1/customers", headers=auth_headers, json=second)
    assert first_response.status_code == 201
    assert second_response.status_code == 201

    second_id = second_response.json()["id"]
    update_response = client.put(
        f"/api/v1/customers/{second_id}",
        headers=auth_headers,
        json={"document_number": "CUST-300"},
    )

    assert update_response.status_code == 409


def test_customer_identity_document_sides_can_be_uploaded_replaced_downloaded_and_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    customer = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={
            "first_name": "Identity",
            "last_name": "Customer",
            "document_type": "CC",
            "document_number": "IDENTITY-MEDIA-1",
            "phone": "5550000",
            "city": "Bogota",
        },
    ).json()
    customer_id = customer["id"]

    uploaded = client.post(
        f"/api/v1/customers/{customer_id}/identity-document",
        headers=auth_headers,
        files={"file": ("identity.pdf", PDF_BYTES, "application/pdf")},
        data={"side": "front"},
    )
    assert uploaded.status_code == 201, uploaded.text
    first_document = uploaded.json()
    assert first_document["filename"] == "identity.pdf"
    assert first_document["content_type"] == "application/pdf"
    assert first_document["side"] == "front"

    back = client.post(
        f"/api/v1/customers/{customer_id}/identity-document",
        headers=auth_headers,
        files={"file": ("identity-back.pdf", PDF_BYTES, "application/pdf")},
        data={"side": "back"},
    )
    assert back.status_code == 201, back.text
    assert back.json()["side"] == "back"
    assert back.json()["id"] != first_document["id"]

    # A rescan replaces the prior document instead of creating ambiguous versions.
    replacement = client.post(
        f"/api/v1/customers/{customer_id}/identity-document",
        headers=auth_headers,
        files={"file": ("identity-rescan.pdf", PDF_BYTES + b"\n", "application/pdf")},
        data={"side": "front"},
    )
    assert replacement.status_code == 201
    assert replacement.json()["id"] == first_document["id"]
    assert replacement.json()["filename"] == "identity-rescan.pdf"

    metadata = client.get(
        f"/api/v1/customers/{customer_id}/identity-document", headers=auth_headers
    )
    assert metadata.status_code == 200
    assert {document["side"] for document in metadata.json()} == {"front", "back"}
    assert next(document for document in metadata.json() if document["side"] == "front")["filename"] == "identity-rescan.pdf"

    download = client.get(
        f"/api/v1/customers/{customer_id}/identity-document/front/file", headers=auth_headers
    )
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert download.content == PDF_BYTES + b"\n"

    deleted = client.delete(
        f"/api/v1/customers/{customer_id}/identity-document/back", headers=auth_headers
    )
    assert deleted.status_code == 204
    remaining = client.get(
        f"/api/v1/customers/{customer_id}/identity-document", headers=auth_headers
    ).json()
    assert [document["side"] for document in remaining] == ["front"]

    invalid_side = client.post(
        f"/api/v1/customers/{customer_id}/identity-document",
        headers=auth_headers,
        files={"file": ("identity.pdf", PDF_BYTES, "application/pdf")},
        data={"side": "middle"},
    )
    assert invalid_side.status_code == 400
