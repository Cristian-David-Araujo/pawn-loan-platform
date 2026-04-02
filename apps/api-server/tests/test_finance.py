from datetime import date

from fastapi.testclient import TestClient


def test_generate_interest_for_active_loans(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    create_loan(principal=1200)
    create_loan(principal=800)

    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(date.today())},
    )
    assert response.status_code == 200
    charges = response.json()
    assert len(charges) == 2
    assert all(item["status"] == "generated" for item in charges)



def test_loan_balance_and_ledger(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    loan = create_loan(principal=1000)

    interest_response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(date.today())},
    )
    assert interest_response.status_code == 200

    payment_response = client.post(
        "/api/v1/payments",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "payment_date": str(date.today()),
            "total_amount": 150,
            "allocated_to_penalty": 0,
            "allocated_to_interest": 100,
            "allocated_to_fees": 0,
            "allocated_to_principal": 50,
            "payment_method": "cash",
        },
    )
    assert payment_response.status_code == 201

    balance_response = client.get(f"/api/v1/loans/{loan['id']}/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    balance = balance_response.json()
    assert balance["loan_id"] == loan["id"]
    assert balance["total_interest_generated"] > 0
    assert balance["total_payments"] == 150

    ledger_response = client.get(f"/api/v1/loans/{loan['id']}/ledger", headers=auth_headers)
    assert ledger_response.status_code == 200
    ledger = ledger_response.json()
    assert ledger["loan_id"] == loan["id"]
    assert len(ledger["interest_charges"]) >= 1
    assert len(ledger["payments"]) == 1


def test_generate_interest_uses_due_day_calendar_cycle(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CYCLE-1")
    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 8,
            "disbursement_date": "2026-07-05",
            "due_day": 5,
        },
    )
    assert loan_response.status_code == 201

    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": "2026-08-05"},
    )
    assert response.status_code == 200
    charges = response.json()
    assert len(charges) == 1
    assert charges[0]["period_start"] == "2026-07-05"
    assert charges[0]["period_end"] == "2026-08-05"


def test_generate_interest_skips_duplicate_period(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CYCLE-2")
    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 8,
            "disbursement_date": "2026-07-05",
            "due_day": 5,
        },
    )
    assert loan_response.status_code == 201

    first = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": "2026-08-05"},
    )
    assert first.status_code == 200
    assert len(first.json()) == 1

    second = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": "2026-08-06"},
    )
    assert second.status_code == 200
    assert len(second.json()) == 0


def test_pending_interest_penalty_uses_configured_loan_rate(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="PENALTY-RATE-LOAN")

    zero_penalty_loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 10,
            "late_penalty_rate": 0,
            "disbursement_date": "2026-01-05",
            "due_day": 5,
        },
    )
    assert zero_penalty_loan.status_code == 201

    configured_penalty_loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 10,
            "late_penalty_rate": 3,
            "disbursement_date": "2026-01-05",
            "due_day": 5,
        },
    )
    assert configured_penalty_loan.status_code == 201

    generated = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": "2026-02-05"},
    )
    assert generated.status_code == 200

    pending = client.get(f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200

    groups = pending.json()["groups"]
    items = [item for group in groups for item in group["items"]]
    by_loan_id = {item["loan_id"]: item for item in items}

    zero_penalty_id = zero_penalty_loan.json()["id"]
    configured_penalty_id = configured_penalty_loan.json()["id"]

    assert by_loan_id[zero_penalty_id]["penalty_amount"] == 0
    assert by_loan_id[configured_penalty_id]["penalty_amount"] > 0
