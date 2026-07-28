"""An advance belongs to the customer, not to the loan it happened to be filed against.

A `PaymentEvent` needs a loan, so money paid ahead is recorded against one of them — but the
netting has to span the customer's whole book. It used to be consumed inside the single loan
that held the row, so a customer could be shown "200.000 in credit" and "50.000 overdue" on
the same statement, with a penalty accruing against money they had already handed over.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan
from src.infrastructure.tasks.interest_scheduler import run_interest_generation_cycle
from src.modules.finance.interest_balance import sync_interest_charge_statuses


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _loan(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    *,
    principal: float,
    days_ago: int = 0,
    penalty: float = 10,
) -> dict:
    disbursement = date.today() - timedelta(days=days_ago)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id, "loan_type": "personal", "principal_amount": principal,
            "outstanding_principal": principal, "monthly_interest_rate": 5,
            "late_penalty_rate": penalty, "disbursement_date": disbursement.isoformat(),
            "due_day": disbursement.day,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _pending(client: TestClient, auth_headers: dict[str, str], customer_id: int) -> dict:
    response = client.get(
        f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_an_advance_covers_the_other_loans_of_the_same_customer(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """200.000 paid ahead with two loans open must cover both of next month's charges."""
    _configure(db_session)
    customer = create_customer()
    today = date.today()
    small = _loan(client, auth_headers, customer["id"], principal=1000000)
    large = _loan(client, auth_headers, customer["id"], principal=2000000)

    paid = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 200000, "payment_method": "cash"},
    )
    assert paid.status_code == 200, paid.text
    assert _pending(client, auth_headers, customer["id"])["available_advance_balance"] == 200000

    run_interest_generation_cycle(as_of_date=today + timedelta(days=35), db_session=db_session)
    db_session.expire_all()

    # 50.000 on the small loan and 100.000 on the large one, all of it inside the 200.000.
    balance = _pending(client, auth_headers, customer["id"])
    assert balance["total_pending_interest"] == 0, "the advance stayed trapped in one loan"
    assert balance["total_pending_penalty"] == 0
    assert balance["available_advance_balance"] == 50000, "the unused remainder is wrong"

    db_session.expire_all()
    for loan_id in (small["id"], large["id"]):
        assert db_session.get(Loan, loan_id).status == LoanStatus.active


def test_a_loan_covered_by_an_advance_does_not_fall_overdue(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The loan the advance was not filed against used to go overdue and accrue a penalty."""
    _configure(db_session)
    customer = create_customer()
    today = date.today()
    _loan(client, auth_headers, customer["id"], principal=1000000)
    other = _loan(client, auth_headers, customer["id"], principal=1000000)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 200000, "payment_method": "cash"},
    )

    # Two cycles: the periods fall due and the status job runs over the result.
    run_interest_generation_cycle(as_of_date=today + timedelta(days=35), db_session=db_session)
    run_interest_generation_cycle(as_of_date=today + timedelta(days=40), db_session=db_session)
    db_session.expire_all()

    assert db_session.get(Loan, other["id"]).status == LoanStatus.active
    assert _pending(client, auth_headers, customer["id"])["total_pending_penalty"] == 0


def test_a_charge_covered_by_an_advance_is_cached_as_paid(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """`InterestCharge.status` is a cache of the netted balance, advances included.

    It was derived from the charge's own ledger rows alone, so a period fully covered by an
    advance was cached as `generated` while every balance in the system agreed it owed
    nothing. Called directly here because the cache is only refreshed on the paths that move
    interest — a payment, a reversal, a foreclosure sale — and the generation cycle is not one
    of them, so a charge born already covered keeps a stale status until the next collection.
    That is tolerable precisely because the status is never the source of truth.
    """
    _configure(db_session)
    customer = create_customer()
    today = date.today()
    loan = _loan(client, auth_headers, customer["id"], principal=1000000)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 200000, "payment_method": "cash"},
    )
    run_interest_generation_cycle(as_of_date=today + timedelta(days=35), db_session=db_session)
    db_session.expire_all()

    charge = db_session.scalar(select(InterestCharge).where(InterestCharge.loan_id == loan["id"]))
    assert charge.amount == 50000

    sync_interest_charge_statuses(db_session, loan["id"])
    db_session.commit()
    db_session.expire_all()

    charge = db_session.scalar(select(InterestCharge).where(InterestCharge.loan_id == loan["id"]))
    assert charge.status == "paid", "a charge covered by the advance still read as unbilled"


def test_the_advance_is_consumed_oldest_period_first_across_loans(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Same order money is applied at the counter, which is what makes the two agree."""
    _configure(db_session)
    customer = create_customer()
    today = date.today()
    # The older loan bills first, so its period is the one the advance has to reach first.
    older = _loan(client, auth_headers, customer["id"], principal=1000000, days_ago=20)
    newer = _loan(client, auth_headers, customer["id"], principal=1000000, days_ago=5)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 60000, "payment_method": "cash"},
    )
    run_interest_generation_cycle(as_of_date=today + timedelta(days=40), db_session=db_session)
    db_session.expire_all()

    items = {
        item["loan_id"]: item
        for group in _pending(client, auth_headers, customer["id"])["groups"]
        for item in group["items"]
    }
    # 60.000 covers the older period in full (50.000) and 10.000 of the newer one.
    assert older["id"] not in items, "the oldest period was not covered first"
    assert items[newer["id"]]["remaining_pending_amount"] == 40000


def test_reversing_the_advance_puts_the_debt_back(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The pool is derived from live ledger rows, so undoing the payment undoes the cover."""
    _configure(db_session)
    customer = create_customer()
    today = date.today()
    _loan(client, auth_headers, customer["id"], principal=1000000)
    _loan(client, auth_headers, customer["id"], principal=2000000)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 200000, "payment_method": "cash"},
    )
    run_interest_generation_cycle(as_of_date=today + timedelta(days=35), db_session=db_session)
    db_session.expire_all()
    assert _pending(client, auth_headers, customer["id"])["total_pending_interest"] == 0

    payment_id = client.get("/api/v1/payments", headers=auth_headers).json()[0]["id"]
    reversed_response = client.post(
        f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "till error"}
    )
    assert reversed_response.status_code == 200, reversed_response.text

    db_session.expire_all()
    after = _pending(client, auth_headers, customer["id"])
    assert after["total_pending_interest"] == 150000
    assert after["available_advance_balance"] == 0
