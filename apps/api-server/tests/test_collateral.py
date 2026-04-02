from datetime import date

from fastapi.testclient import TestClient


def test_create_collateral_requires_existing_loan(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "loan_id": 999,
        "description": "Gold chain",
        "appraised_value": 600,
        "storage_location": "Vault A",
    }
    response = client.post("/api/v1/collateral-items", headers=auth_headers, json=payload)
    assert response.status_code == 404


def test_create_collateral_rejects_personal_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="COLL-CUST-PERSONAL")

    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "personal",
            "principal_amount": 500,
            "monthly_interest_rate": 6,
            "disbursement_date": str(date.today()),
            "due_day": 10,
        },
    )
    assert loan_response.status_code == 201
    personal_loan_id = loan_response.json()["id"]

    collateral_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": personal_loan_id,
            "description": "Laptop",
            "appraised_value": 450,
            "storage_location": "Vault D",
        },
    )
    assert collateral_response.status_code == 400


def test_create_collateral_rejects_closed_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="COLL-CUST-CLOSED")

    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 0,
            "monthly_interest_rate": 8,
            "disbursement_date": str(date.today()),
            "due_day": 12,
        },
    )
    assert loan_response.status_code == 201
    loan_id = loan_response.json()["id"]

    close_response = client.post(
        f"/api/v1/loans/{loan_id}/close",
        headers=auth_headers,
        json={"force": False},
    )
    assert close_response.status_code == 200

    collateral_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan_id,
            "description": "Gold ring",
            "appraised_value": 300,
            "storage_location": "Vault E",
        },
    )
    assert collateral_response.status_code == 400



def test_release_collateral_requires_zero_balance(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=700)

    create_item_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "description": "Watch",
            "appraised_value": 800,
            "storage_location": "Vault B",
        },
    )
    assert create_item_response.status_code == 201
    item_id = create_item_response.json()["id"]

    release_response = client.post(f"/api/v1/collateral-items/{item_id}/release", headers=auth_headers)
    assert release_response.status_code == 400



def test_liquidate_collateral_updates_status(client: TestClient, auth_headers: dict[str, str], create_customer) -> None:
    customer = create_customer(document_number="COLL-CUST-1")

    loan_payload = {
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "principal_amount": 0,
        "monthly_interest_rate": 7,
        "disbursement_date": str(date.today()),
        "due_day": 9,
    }
    loan_response = client.post("/api/v1/loans", headers=auth_headers, json=loan_payload)
    assert loan_response.status_code == 201
    loan_id = loan_response.json()["id"]

    item_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan_id,
            "description": "Ring",
            "appraised_value": 300,
            "storage_location": "Vault C",
        },
    )
    assert item_response.status_code == 201
    item_id = item_response.json()["id"]

    liquidate_response = client.post(f"/api/v1/collateral-items/{item_id}/liquidate", headers=auth_headers)
    assert liquidate_response.status_code == 200
    assert liquidate_response.json()["status"] == "liquidated"


def test_update_collateral_item(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    loan = create_loan(principal=700)

    create_item_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "description": "Initial watch",
            "appraised_value": 800,
            "storage_location": "Vault B",
        },
    )
    assert create_item_response.status_code == 201
    item_id = create_item_response.json()["id"]

    update_response = client.put(
        f"/api/v1/collateral-items/{item_id}",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "description": "Updated watch",
            "appraised_value": 900,
            "storage_location": "Vault C",
            "status": "in_custody",
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["description"] == "Updated watch"
    assert payload["appraised_value"] == 900
    assert payload["storage_location"] == "Vault C"


def test_update_collateral_rejects_personal_loan_reassociation(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    create_loan,
) -> None:
    pawn_loan = create_loan(principal=700)

    personal_customer = create_customer(document_number="COLL-UPD-PERS")
    personal_loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": personal_customer["id"],
            "loan_type": "personal",
            "principal_amount": 500,
            "monthly_interest_rate": 6,
            "disbursement_date": str(date.today()),
            "due_day": 10,
        },
    )
    assert personal_loan_response.status_code == 201
    personal_loan_id = personal_loan_response.json()["id"]

    create_item_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": pawn_loan["id"],
            "description": "Ring",
            "appraised_value": 350,
            "storage_location": "Vault D",
        },
    )
    assert create_item_response.status_code == 201
    item_id = create_item_response.json()["id"]

    update_response = client.put(
        f"/api/v1/collateral-items/{item_id}",
        headers=auth_headers,
        json={
            "loan_id": personal_loan_id,
            "description": "Ring",
            "appraised_value": 350,
            "storage_location": "Vault D",
            "status": "in_custody",
        },
    )
    assert update_response.status_code == 400
