"""What a customer's invoice history has to say.

`interest-pending` answers "what is owed"; it is what the collection screen and the allocation
preview are built on. Nothing answered "which invoices exist and which are paid" — a settled
period simply disappeared from the application once it was covered.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import InterestCharge, Loan
from src.infrastructure.utils.datetime_utils import get_local_date


def _charge(db: Session, loan_id: int, amount: float, *, months_ago: int = 1, marker: bool = False) -> InterestCharge:
    today = get_local_date(db)
    period_end = today - timedelta(days=30 * months_ago)
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=period_end - timedelta(days=30),
        period_end=period_end,
        charge_date=period_end,
        amount=0.0 if marker else amount,
        status="not_billed" if marker else "generated",
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def _history(client: TestClient, headers: dict[str, str], customer_id: int) -> dict:
    response = client.get(f"/api/v1/payments/customers/{customer_id}/interest-history", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_a_settled_period_stays_in_the_history(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 100.0)

    paid = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 100.0, "payment_method": "cash"},
    )
    assert paid.status_code == 200

    # Gone from the collection view, which is correct.
    pending = client.get(f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers).json()
    assert pending["total_outstanding"] == 0

    body = _history(client, auth_headers, customer_id)
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["settled"] is True
    assert item["paid_amount"] == 100.0
    assert item["outstanding"] == 0.0
    assert body["total_paid"] == 100.0


def test_a_partly_paid_period_reports_both_halves(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 100.0)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 40.0, "payment_method": "cash"},
    )

    item = _history(client, auth_headers, customer_id)["items"][0]
    assert item["paid_amount"] == 40.0
    assert item["outstanding"] == 60.0
    assert item["settled"] is False


def test_a_voided_charge_is_shown_as_voided_not_hidden(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """It owes nothing, but it is part of the history. Hiding it would make a period vanish
    between two statements with nothing saying why."""
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    charge = _charge(db_session, loan["id"], 100.0)

    client.post(
        f"/api/v1/interest/charges/{charge.id}/void",
        headers=auth_headers,
        json={"reason": "billed by mistake"},
    )

    body = _history(client, auth_headers, customer_id)
    item = body["items"][0]
    assert item["voided"] is True
    assert item["void_reason"] == "billed by mistake"
    assert item["outstanding"] == 0.0
    assert item["settled"] is False, "a cancelled invoice was not settled by anyone"
    assert body["total_charged"] == 0.0, "a voided charge is not part of what was billed"


def test_a_not_billed_marker_never_appears(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """A zero-amount marker is a month deliberately never charged. It exists so the generator
    does not fill the gap later; it is not an invoice and must reach no statement."""
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 0.0, marker=True)

    assert _history(client, auth_headers, customer_id)["items"] == []


def test_the_history_agrees_with_the_collection_screen(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """Two endpoints, one balance. They derive it from the same canonical calculation, and a
    customer reading a statement must not be told a different figure from the one the counter
    is about to collect."""
    loan = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, loan["id"]).customer_id
    _charge(db_session, loan["id"], 100.0)
    _charge(db_session, loan["id"], 50.0, months_ago=2)

    pending = client.get(f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers).json()
    history = _history(client, auth_headers, customer_id)

    assert history["total_outstanding"] == pending["total_outstanding"]
