from datetime import date

from fastapi.testclient import TestClient



def test_payment_can_close_loan_and_reverse_reopens_it(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=400)

    # Principal-only, so the collection route records it exactly as the old free-form
    # endpoint did — minus the buckets a caller used to be trusted to add up itself.
    create_payment_response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "payment_date": str(date.today()),
            "total_amount": 400,
            "payment_method": "bank-transfer",
            "allow_with_unpaid_interest": True,
        },
    )
    assert create_payment_response.status_code == 200, create_payment_response.text
    payment_id = create_payment_response.json()["payment_id"]

    loan_response = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert loan_response.status_code == 200
    assert loan_response.json()["status"] == "closed"

    reverse_response = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"})
    assert reverse_response.status_code == 200
    assert reverse_response.json()["is_reversed"] is True

    loan_after_reverse = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert loan_after_reverse.status_code == 200
    assert loan_after_reverse.json()["status"] == "active"

    second_reverse = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"})
    assert second_reverse.status_code == 400
