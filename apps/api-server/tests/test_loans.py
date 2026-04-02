from datetime import date

from fastapi.testclient import TestClient


def test_application_approve_and_create_loan(client: TestClient, auth_headers: dict[str, str], create_customer) -> None:
    customer = create_customer(document_number="LOAN-CUST-1")

    app_payload = {
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "requested_amount": 1200,
        "monthly_interest_rate": 8.5,
        "term_months": 6,
        "notes": "Initial test app",
    }
    app_response = client.post("/api/v1/loan-applications", headers=auth_headers, json=app_payload)
    assert app_response.status_code == 201
    application_id = app_response.json()["id"]

    approve_response = client.post(f"/api/v1/loan-applications/{application_id}/approve", headers=auth_headers)
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    loan_payload = {
        "application_id": application_id,
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "principal_amount": 1000,
        "monthly_interest_rate": 8.5,
        "disbursement_date": str(date.today()),
        "due_day": 10,
    }
    loan_response = client.post("/api/v1/loans", headers=auth_headers, json=loan_payload)
    assert loan_response.status_code == 201
    assert loan_response.json()["outstanding_principal"] == 1000


def test_close_without_force_requires_zero_outstanding(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=900)

    close_response = client.post(f"/api/v1/loans/{loan['id']}/close", headers=auth_headers, json={"force": False})
    assert close_response.status_code == 400



def test_renew_closes_source_and_creates_new_loan(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    source_loan = create_loan(principal=500)

    renew_response = client.post(
        f"/api/v1/loans/{source_loan['id']}/renew",
        headers=auth_headers,
        json={"monthly_interest_rate": 7.0, "due_day": 8},
    )
    assert renew_response.status_code == 201
    renewed = renew_response.json()
    assert renewed["renewal_of"] == source_loan["id"]

    source_response = client.get(f"/api/v1/loans/{source_loan['id']}", headers=auth_headers)
    assert source_response.status_code == 200
    assert source_response.json()["status"] == "closed"


def test_update_loan_allows_rate_due_day_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=1200)

    response = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"monthly_interest_rate": 9.5, "due_day": 12, "status": "overdue"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["monthly_interest_rate"] == 9.5
    assert payload["due_day"] == 12
    assert payload["status"] == "overdue"
