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
