from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, InterestCharge, Loan


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



def test_foreclose_and_sell_collateral_flow(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=500)

    create_item_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "description": "Necklace",
            "appraised_value": 900,
            "storage_location": "Vault F",
        },
    )
    assert create_item_response.status_code == 201
    item = create_item_response.json()
    assert item["status"] == "in_custody"

    # Selling before foreclosure must be rejected
    early_sell = client.post(
        f"/api/v1/collateral-items/{item['id']}/sell",
        headers=auth_headers,
        json={"sale_price": 600},
    )
    assert early_sell.status_code == 400

    foreclose_response = client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers)
    assert foreclose_response.status_code == 200
    assert foreclose_response.json()["status"] == "defaulted"

    # Foreclosing twice must be rejected
    second_foreclose = client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers)
    assert second_foreclose.status_code == 400

    item_after = client.get(f"/api/v1/collateral-items/{item['id']}", headers=auth_headers).json()
    assert item_after["status"] == "for_sale"

    sell_response = client.post(
        f"/api/v1/collateral-items/{item['id']}/sell",
        headers=auth_headers,
        json={"sale_price": 600, "notes": "Auction"},
    )
    assert sell_response.status_code == 200
    sold = sell_response.json()
    assert sold["status"] == "sold"
    assert sold["sale_price"] == 600
    assert sold["sold_at"] is not None

    loan_after = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers).json()
    assert loan_after["outstanding_principal"] == 0
    assert loan_after["status"] == "closed"


def test_foreclose_rejects_personal_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="FORECLOSE-PERSONAL")

    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "personal",
            "principal_amount": 400,
            "monthly_interest_rate": 5,
            "disbursement_date": str(date.today()),
            "due_day": 15,
        },
    )
    assert loan_response.status_code == 201

    foreclose_response = client.post(
        f"/api/v1/loans/{loan_response.json()['id']}/foreclose",
        headers=auth_headers,
    )
    assert foreclose_response.status_code == 400



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

    # An item in custody belongs to the customer: writing it off takes a foreclosure first.
    too_early = client.post(f"/api/v1/collateral-items/{item_id}/liquidate", headers=auth_headers)
    assert too_early.status_code == 400
    assert "foreclosed" in too_early.json()["detail"].lower()

    foreclose_response = client.post(f"/api/v1/loans/{loan_id}/foreclose", headers=auth_headers)
    assert foreclose_response.status_code == 200

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


def _create_pawn_loan_with_item(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    principal: float,
    items: int = 1,
) -> tuple[dict, list[int]]:
    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "loan_type": "pawn",
            "principal_amount": principal,
            "monthly_interest_rate": 10.0,
            "disbursement_date": str(date.today()),
            "due_day": 5,
        },
    )
    assert loan_response.status_code == 201
    loan = loan_response.json()

    item_ids = []
    for index in range(items):
        created = client.post(
            "/api/v1/collateral-items",
            headers=auth_headers,
            json={
                "loan_id": loan["id"],
                "description": f"Pledge {index}",
                "appraised_value": principal,
                "storage_location": "Vault C",
            },
        )
        assert created.status_code == 201
        item_ids.append(created.json()["id"])

    return loan, item_ids


def test_release_collateral_rejected_while_interest_is_pending(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Zero principal is not enough: the pledge is the leverage to collect the interest."""
    customer = create_customer(document_number="COLL-RELEASE-INTEREST")
    loan, item_ids = _create_pawn_loan_with_item(client, auth_headers, customer["id"], principal=500)

    charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date.today() - timedelta(days=60),
        period_end=date.today() - timedelta(days=30),
        charge_date=date.today() - timedelta(days=30),
        amount=50,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()

    # Close the loan the only way that leaves interest behind.
    closed = client.post(
        f"/api/v1/loans/{loan['id']}/close",
        headers=auth_headers,
        json={"force": True},
    )
    assert closed.status_code == 200
    db_session.expire_all()
    db_session.get(Loan, loan["id"]).outstanding_principal = 0
    db_session.commit()

    blocked = client.post(f"/api/v1/collateral-items/{item_ids[0]}/release", headers=auth_headers)
    assert blocked.status_code == 400
    assert "interest" in blocked.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.get(CollateralItem, item_ids[0]).status == "in_custody"


def test_release_collateral_for_loan_releases_every_item(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    customer = create_customer(document_number="COLL-RELEASE-BULK")
    loan, item_ids = _create_pawn_loan_with_item(
        client, auth_headers, customer["id"], principal=400, items=3
    )

    settled = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 400,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert settled.status_code == 200
    assert settled.json()["loan_status"] == LoanStatus.closed.value

    response = client.post(f"/api/v1/collateral-items/loans/{loan['id']}/release", headers=auth_headers)
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == set(item_ids)
    assert all(item["status"] == "released" for item in response.json())

    # Safe to retry: nothing is left in custody, so the second call is simply empty.
    again = client.post(f"/api/v1/collateral-items/loans/{loan['id']}/release", headers=auth_headers)
    assert again.status_code == 200
    assert again.json() == []


def test_release_collateral_for_loan_rejected_with_outstanding_principal(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    customer = create_customer(document_number="COLL-RELEASE-OPEN")
    loan, item_ids = _create_pawn_loan_with_item(client, auth_headers, customer["id"], principal=600)

    response = client.post(f"/api/v1/collateral-items/loans/{loan['id']}/release", headers=auth_headers)
    assert response.status_code == 400

    db_session.expire_all()
    assert db_session.get(CollateralItem, item_ids[0]).status == "in_custody"
