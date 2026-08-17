"""A loan's status must be right the moment the money moves, not a cycle later.

`refresh_overdue_loan_statuses` used to be reachable only from
`run_interest_generation_cycle`, so a customer who cleared their arrears at the counter left
with a receipt while the loan still read `overdue` — for up to
`AUTO_INTEREST_GENERATION_INTERVAL_MINUTES`, a full day by default. These pin the three money
paths that can change the answer.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan
from src.infrastructure.utils.datetime_utils import get_local_date


def _overdue_charge(db: Session, loan_id: int, amount: float) -> InterestCharge:
    """A period whose due date has already passed, so the loan qualifies as overdue."""
    today = get_local_date(db)
    settings = db.get(GlobalSettings, 1)
    grace = settings.default_grace_days if settings else 0

    period_end = today - timedelta(days=grace + 5)
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=period_end - timedelta(days=30),
        period_end=period_end,
        charge_date=period_end,
        amount=amount,
        status="generated",
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def _mark_overdue(db: Session, loan_id: int) -> None:
    loan = db.get(Loan, loan_id)
    loan.status = LoanStatus.overdue
    db.commit()


def test_paying_the_arrears_clears_overdue_immediately(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    _overdue_charge(db_session, loan["id"], 100.0)
    _mark_overdue(db_session, loan["id"])

    customer_id = db_session.get(Loan, loan["id"]).customer_id
    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 100.0, "payment_method": "cash"},
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.active, (
        "the loan owes nothing past due, so it must not still read overdue after the receipt"
    )


def test_a_partial_payment_leaves_the_loan_overdue(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The refresh re-derives the answer; it does not just clear the flag on any payment."""
    loan = create_loan(principal=1000.0)
    _overdue_charge(db_session, loan["id"], 100.0)
    _mark_overdue(db_session, loan["id"])

    customer_id = db_session.get(Loan, loan["id"]).customer_id
    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 40.0, "payment_method": "cash"},
    )

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.overdue


def test_paying_one_loan_can_clear_another_of_the_same_customer(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """Why the sweep is scoped to the customer's book rather than to the loans that got an event.

    Interest is allocated oldest-first across every loan a customer holds, so one payment
    routinely settles a period belonging to a loan the operator did not name. Scoping to the
    loans that received a `PaymentEvent` would leave the other one reading `overdue` until the
    next cycle — the same defect, only harder to reproduce.
    """
    first = create_loan(principal=1000.0)
    customer_id = db_session.get(Loan, first["id"]).customer_id

    second = Loan(
        customer_id=customer_id,
        loan_type="pawn",
        principal_amount=500.0,
        outstanding_principal=500.0,
        monthly_interest_rate=10.0,
        late_penalty_rate=0.0,
        disbursement_date=get_local_date(db_session) - timedelta(days=60),
        due_day=5,
        status=LoanStatus.overdue,
    )
    db_session.add(second)
    db_session.commit()
    db_session.refresh(second)

    _overdue_charge(db_session, first["id"], 60.0)
    _overdue_charge(db_session, second.id, 40.0)
    _mark_overdue(db_session, first["id"])

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 100.0, "payment_method": "cash"},
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    assert db_session.get(Loan, first["id"]).status == LoanStatus.active
    assert db_session.get(Loan, second.id).status == LoanStatus.active, (
        "the second loan's period was settled by the same payment, so its status must follow"
    )


def test_reversing_the_payment_makes_the_loan_overdue_again(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The mirror: putting the debt back must put the label back with it."""
    loan = create_loan(principal=1000.0)
    _overdue_charge(db_session, loan["id"], 100.0)
    _mark_overdue(db_session, loan["id"])

    customer_id = db_session.get(Loan, loan["id"]).customer_id
    paid = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "total_amount": 100.0, "payment_method": "cash"},
    )
    assert paid.status_code == 200

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.active

    payment_id = paid.json()["payment_id"] if "payment_id" in paid.json() else None
    if payment_id is None:
        from src.infrastructure.persistence.models import Payment

        payment_id = db_session.query(Payment).order_by(Payment.id.desc()).first().id

    reversed_response = client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        headers=auth_headers,
        json={"reason": "collected in error"},
    )
    assert reversed_response.status_code == 200, reversed_response.text

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.overdue, (
        "the arrears are back, so the loan is overdue again"
    )


def test_a_closed_loan_is_never_reopened_by_the_refresh(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """`closed` and `defaulted` are not managed by this sweep.

    `pay_principal` closes a loan the instant its principal reaches zero, even with interest
    outstanding. The refresh that runs right after must not look at it and decide it is
    overdue, which would undo a close that had just been recorded.
    """
    loan = create_loan(principal=1000.0)
    _overdue_charge(db_session, loan["id"], 100.0)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 1000.0,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.closed
