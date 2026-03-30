from datetime import date

from fastapi.testclient import TestClient


def test_payment_allocation_must_match_total(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    loan = create_loan(principal=1000)

    response = client.post(
        "/api/v1/payments",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "payment_date": str(date.today()),
            "total_amount": 100,
            "allocated_to_penalty": 0,
            "allocated_to_interest": 20,
            "allocated_to_fees": 10,
            "allocated_to_principal": 60,
            "payment_method": "cash",
        },
    )
    assert response.status_code == 400



def test_payment_can_close_loan_and_reverse_reopens_it(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=400)

    create_payment_response = client.post(
        "/api/v1/payments",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "payment_date": str(date.today()),
            "total_amount": 400,
            "allocated_to_penalty": 0,
            "allocated_to_interest": 0,
            "allocated_to_fees": 0,
            "allocated_to_principal": 400,
            "payment_method": "bank-transfer",
        },
    )
    assert create_payment_response.status_code == 201
    payment_id = create_payment_response.json()["id"]

    loan_response = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert loan_response.status_code == 200
    assert loan_response.json()["status"] == "closed"

    reverse_response = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers)
    assert reverse_response.status_code == 200
    assert reverse_response.json()["is_reversed"] is True

    loan_after_reverse = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert loan_after_reverse.status_code == 200
    assert loan_after_reverse.json()["status"] == "active"

    second_reverse = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers)
    assert second_reverse.status_code == 400
