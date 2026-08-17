
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import Loan


def test_reporting_endpoints(client: TestClient, auth_headers: dict[str, str], create_loan, db_session: Session) -> None:
    active_loan = create_loan(principal=750)
    overdue_loan = create_loan(principal=650)

    overdue_db_loan = db_session.get(Loan, overdue_loan["id"])
    assert overdue_db_loan is not None
    overdue_db_loan.status = LoanStatus.overdue
    db_session.commit()

    collateral_response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": active_loan["id"],
            "description": "Necklace",
            "appraised_value": 500,
            "storage_location": "Vault D",
        },
    )
    assert collateral_response.status_code == 201

    # No fees bucket: nothing but a collateral sale's surplus produces one, and the endpoint
    # that let a caller declare 10 of them out of nothing is gone. The report only needs a
    # collection to exist and to total at least 100.
    payment_response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": active_loan["id"],
            "total_amount": 100,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert payment_response.status_code == 200, payment_response.text

    active_response = client.get("/api/v1/reports/active-loans", headers=auth_headers)
    assert active_response.status_code == 200
    assert active_response.json()["count"] >= 1

    overdue_response = client.get("/api/v1/reports/overdue-loans", headers=auth_headers)
    assert overdue_response.status_code == 200
    assert overdue_response.json()["count"] >= 1

    custody_response = client.get("/api/v1/reports/collateral-custody", headers=auth_headers)
    assert custody_response.status_code == 200
    assert custody_response.json()["count"] >= 1

    cash_response = client.get("/api/v1/reports/cash-summary", headers=auth_headers)
    assert cash_response.status_code == 200
    assert cash_response.json()["payments_count"] >= 1
    assert cash_response.json()["total_collected"] >= 100
