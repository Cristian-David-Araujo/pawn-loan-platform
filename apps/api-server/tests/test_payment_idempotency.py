"""A double-clicked submit must not be two payments.

The row lock added earlier stops two cashiers racing on the same balance. It does nothing
about the same cashier sending the same collection twice because the connection was slow and
the button still looked live — which is the likelier failure at a counter.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import InterestCharge, Loan, Payment
from src.infrastructure.utils.datetime_utils import get_local_date


def _charge(db: Session, loan_id: int, amount: float) -> None:
    today = get_local_date(db)
    db.add(
        InterestCharge(
            loan_id=loan_id,
            period_start=today - timedelta(days=60),
            period_end=today - timedelta(days=30),
            charge_date=today - timedelta(days=30),
            amount=amount,
            status="generated",
        )
    )
    db.commit()


def _count(db: Session) -> int:
    return db.query(Payment).count()


def test_the_same_key_records_one_interest_payment(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 100.0)

    body = {
        "customer_id": customer_id,
        "total_amount": 50.0,
        "payment_method": "cash",
        "idempotency_key": "attempt-1",
    }

    first = client.post("/api/v1/payments/interest", headers=auth_headers, json=body)
    assert first.status_code == 200, first.text
    after_first = _count(db_session)

    second = client.post("/api/v1/payments/interest", headers=auth_headers, json=body)
    assert second.status_code == 409
    assert "already recorded" in second.json()["detail"]
    assert _count(db_session) == after_first, "the retry must not have taken the money again"


def test_a_rejected_retry_writes_nothing(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The guard runs before anything is touched, so a refusal leaves no half-written trace."""
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 100.0)

    body = {
        "customer_id": customer_id,
        "total_amount": 40.0,
        "payment_method": "cash",
        "idempotency_key": "attempt-2",
    }
    client.post("/api/v1/payments/interest", headers=auth_headers, json=body)

    db_session.expire_all()
    before = db_session.get(Loan, loan["id"]).status
    events_before = db_session.query(Payment).count()

    client.post("/api/v1/payments/interest", headers=auth_headers, json=body)

    db_session.expire_all()
    assert db_session.query(Payment).count() == events_before
    assert db_session.get(Loan, loan["id"]).status == before


def test_principal_payments_are_guarded_too(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    body = {
        "loan_id": loan["id"],
        "total_amount": 200.0,
        "payment_method": "cash",
        "allow_with_unpaid_interest": True,
        "idempotency_key": "attempt-3",
    }

    first = client.post("/api/v1/payments/principal", headers=auth_headers, json=body)
    assert first.status_code == 200, first.text
    after_first = _count(db_session)

    second = client.post("/api/v1/payments/principal", headers=auth_headers, json=body)
    assert second.status_code == 409
    assert _count(db_session) == after_first

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).outstanding_principal == 800.0, (
        "the second request must not have reduced the principal again"
    )


def test_without_a_key_nothing_changes(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The field is optional, and two genuinely separate collections of the same amount are a
    normal thing at a counter. Only a repeated *key* is a repeat."""
    loan = create_loan(principal=1000.0)
    body = {"loan_id": loan["id"], "total_amount": 100.0, "payment_method": "cash",
            "allow_with_unpaid_interest": True}

    assert client.post("/api/v1/payments/principal", headers=auth_headers, json=body).status_code == 200
    assert client.post("/api/v1/payments/principal", headers=auth_headers, json=body).status_code == 200
    assert _count(db_session) == 2
