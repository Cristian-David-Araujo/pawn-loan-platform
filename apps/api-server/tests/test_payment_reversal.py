from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, PaymentEvent
from src.infrastructure.utils.datetime_utils import get_local_date


def _create_interest_charge(db_session: Session, loan_id: int, amount: float = 100.0) -> InterestCharge:
    # Same clock as the endpoints compare against — see the note in test_payments_advanced.
    today = get_local_date(db_session)
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=today - timedelta(days=30),
        period_end=today,
        charge_date=today,
        amount=amount,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()
    db_session.refresh(charge)
    return charge


def _pending_total(client: TestClient, auth_headers: dict[str, str], customer_id: int) -> float:
    response = client.get(f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers)
    assert response.status_code == 200
    return response.json()["total_pending_interest"]


def test_reversing_interest_payment_restores_pending_interest(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    charge = _create_interest_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 100,
            "payment_method": "cash",
            "notes": "full interest",
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]
    assert _pending_total(client, auth_headers, loan_db.customer_id) == 0

    db_session.refresh(charge)
    assert charge.status == "paid"

    reversal = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"})
    assert reversal.status_code == 200
    assert reversal.json()["is_reversed"] is True

    # The interest is owed again, and the cached charge status follows the ledger.
    assert _pending_total(client, auth_headers, loan_db.customer_id) == 100
    db_session.expire_all()
    db_session.refresh(charge)
    assert charge.status == "generated"

    events = db_session.query(PaymentEvent).filter(PaymentEvent.payment_id == payment_id).all()
    assert events
    assert all(event.is_reversed for event in events)


def test_loan_interest_due_matches_pending_interest_after_reversal(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1200)
    charge = _create_interest_charge(db_session, loan["id"], amount=80)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 50,
            "payment_method": "cash",
            "notes": "partial interest",
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]

    reversal = client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"})
    assert reversal.status_code == 200

    loan_read = client.get(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert loan_read.status_code == 200
    assert loan_read.json()["interest_due"] == _pending_total(client, auth_headers, loan_db.customer_id) == 80


def test_reversing_principal_payment_restores_outstanding_and_reopens_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=500)

    settlement = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 500,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
            "notes": "full settlement",
        },
    )
    assert settlement.status_code == 200
    assert settlement.json()["loan_status"] == LoanStatus.closed.value

    event_id = settlement.json()["payment_event_id"]
    event = db_session.get(PaymentEvent, event_id)
    assert event is not None
    assert event.payment_id is not None

    reversal = client.post(f"/api/v1/payments/{event.payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"})
    assert reversal.status_code == 200

    db_session.expire_all()
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    assert loan_db.outstanding_principal == 500
    assert loan_db.status == LoanStatus.active


def test_payment_cannot_be_reversed_twice(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=700)
    charge = _create_interest_charge(db_session, loan["id"], amount=60)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 60,
            "payment_method": "cash",
            "notes": "interest",
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]

    assert client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"}).status_code == 200
    assert client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"}).status_code == 400
