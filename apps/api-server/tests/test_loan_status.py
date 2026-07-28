from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan


def _create_past_due_charge(db_session: Session, loan_id: int, amount: float = 100.0) -> InterestCharge:
    # Period ended two months ago, so it is past due even with the grace period.
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=date.today() - timedelta(days=90),
        period_end=date.today() - timedelta(days=60),
        charge_date=date.today() - timedelta(days=60),
        amount=amount,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()
    db_session.refresh(charge)
    return charge


def _run_generation(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(date.today())},
    )
    assert response.status_code == 200


def test_loan_becomes_overdue_when_interest_is_past_due(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_past_due_charge(db_session, loan["id"], amount=100)

    _run_generation(client, auth_headers)

    db_session.expire_all()
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    assert loan_db.status == LoanStatus.overdue


def test_overdue_loan_returns_to_active_when_past_due_interest_is_paid(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    charge = _create_past_due_charge(db_session, loan["id"], amount=100)

    _run_generation(client, auth_headers)
    db_session.expire_all()
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    assert loan_db.status == LoanStatus.overdue

    pending = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending",
        headers=auth_headers,
    )
    assert pending.status_code == 200
    outstanding = pending.json()["total_outstanding"]
    assert outstanding >= 100

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": True,
            "total_amount": outstanding,
            "payment_method": "cash",
            "notes": "settle past due interest",
        },
    )
    assert payment.status_code == 200

    _run_generation(client, auth_headers)
    db_session.expire_all()
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    assert loan_db.status == LoanStatus.active


def test_terminal_loan_statuses_are_not_touched(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_past_due_charge(db_session, loan["id"], amount=100)

    closed = client.post(
        f"/api/v1/loans/{loan['id']}/close",
        headers=auth_headers,
        json={"force": True, "reason": "settled by agreement with the customer"},
    )
    assert closed.status_code == 200

    _run_generation(client, auth_headers)

    db_session.expire_all()
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    assert loan_db.status == LoanStatus.closed
