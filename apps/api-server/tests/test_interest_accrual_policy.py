"""The three rules that decide how much a customer owes.

They are collected here rather than split across the loan, finance and payment files
because they only make sense together: interest keeps accruing while the debt is alive,
a penalty is fixed once and never recomputed, and a period that has been invoiced is
immutable. Each of them silently reported a debt other than the real one.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan


def _configure(db_session: Session, *, grace_days: int = 5, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _open_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    *,
    disbursed_days_ago: int,
    principal: float = 1000000,
    penalty_rate: float = 10,
) -> dict:
    disbursement = date.today() - timedelta(days=disbursed_days_ago)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "loan_type": "pawn",
            "principal_amount": principal,
            "outstanding_principal": principal,
            "monthly_interest_rate": 5,
            "late_penalty_rate": penalty_rate,
            "disbursement_date": disbursement.isoformat(),
            "due_day": disbursement.day,
            "description": "gold chain",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _charges(db_session: Session, loan_id: int) -> list[InterestCharge]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(InterestCharge)
            .where(InterestCharge.loan_id == loan_id)
            .order_by(InterestCharge.period_start.asc())
        ).all()
    )


def test_an_invoiced_period_survives_an_edit_of_the_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Correcting a pledge description must not rewrite what was already charged.

    The amount used to be recomputed from the *current* principal for every due period,
    so paying 400.000 of principal and then fixing a typo turned an invoice of 50.000 the
    customer had already settled into one of 30.000, with the ledger still holding 50.000.
    """
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=35, penalty_rate=0)

    interest = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 50000, "payment_method": "cash"},
    )
    assert interest.status_code == 200, interest.text

    principal = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 400000, "payment_method": "cash"},
    )
    assert principal.status_code == 200, principal.text

    billed = _charges(db_session, loan["id"])
    assert [item.amount for item in billed] == [50000]

    edit = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"description": "18k gold chain"},
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["description"] == "18k gold chain"

    after = _charges(db_session, loan["id"])
    assert [item.amount for item in after] == [50000], "an invoiced period was rewritten"


def test_an_edit_only_reaches_periods_that_have_not_ended(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Lowering the principal reprices what is still open, never what already closed."""
    # Lead days pull an unfinished period forward, which is the one an edit may reprice.
    _configure(db_session, lead_days=10)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=55, penalty_rate=0)

    before = _charges(db_session, loan["id"])
    assert len(before) == 2, "expected one closed period and one still open"
    assert [item.amount for item in before] == [50000, 50000]

    edit = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"outstanding_principal": 600000},
    )
    assert edit.status_code == 200, edit.text

    after = _charges(db_session, loan["id"])
    assert after[0].amount == 50000, "the closed period must keep the amount it was invoiced at"
    assert after[1].amount == 30000, "the open period must follow the new principal"


def test_an_overdue_loan_keeps_accruing_month_after_month(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Falling behind does not freeze the debt.

    Generation ran over `active` loans only, so the cycle that flagged a loan `overdue` was
    the last one to bill it: five months of arrears reported the two months charged before
    the transition, and the customer who came back to settle was handed the rest at once.
    """
    _configure(db_session)
    today = date.today()
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=35)

    assert len(_charges(db_session, loan["id"])) == 1

    def run_cycle(days_ahead: int) -> None:
        cycle = client.post(
            "/api/v1/interest/generate",
            headers=auth_headers,
            json={"as_of_date": (today + timedelta(days=days_ahead)).isoformat()},
        )
        assert cycle.status_code == 200, cycle.text
        db_session.expire_all()

    run_cycle(30)
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.overdue
    billed = len(_charges(db_session, loan["id"]))

    # 35 day steps: longer than the longest month, so each cycle crosses exactly one
    # anchor, and shorter than two of them. The count must go up by one every time.
    for offset in (65, 100, 135, 170):
        run_cycle(offset)
        billed += 1
        assert len(_charges(db_session, loan["id"])) == billed, "an overdue loan skipped a month"

    charges = _charges(db_session, loan["id"])
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.overdue
    assert all(item.amount == 50000 for item in charges)
    assert sum(item.amount for item in charges) == 50000 * billed


def test_a_defaulted_loan_stops_accruing(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Foreclosing is a decision to collect through the pledge, not through more interest."""
    _configure(db_session)
    today = date.today()
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=35)

    foreclose = client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers)
    assert foreclose.status_code == 200, foreclose.text

    before = len(_charges(db_session, loan["id"]))
    cycle = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": (today + timedelta(days=90)).isoformat()},
    )
    assert cycle.status_code == 200, cycle.text
    assert len(_charges(db_session, loan["id"])) == before


def test_a_period_marked_as_not_billed_is_never_generated_again(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The months the old defect skipped are closed, and a *new* gap still self-heals.

    Deploying the accrual fix on a portfolio full of holes would have billed every skipped
    month at once. They are marked instead — and because the marker is an ordinary charge,
    the generator's "skip what exists" rule is what keeps them closed, so nothing else had
    to give up filling a gap that appears from here on.
    """
    _configure(db_session)
    today = date.today()
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=95)

    charges = _charges(db_session, loan["id"])
    assert len(charges) == 3

    # Stand in for the migration: the middle period was never billed.
    skipped = charges[1]
    skipped.amount = 0
    skipped.status = "not_billed"
    skipped.penalty_amount = 0
    db_session.commit()

    # And a payment on the loan must not quietly relabel it.
    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 10000, "payment_method": "cash"},
    )

    cycle = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": (today + timedelta(days=1)).isoformat()},
    )
    assert cycle.status_code == 200, cycle.text

    after = _charges(db_session, loan["id"])
    assert len(after) == 3, "the skipped period was billed again"
    marked = [item for item in after if item.period_start == skipped.period_start][0]
    assert marked.amount == 0
    assert marked.status == "not_billed", "the record of why the month is missing was erased"

    pending = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    listed = [item for group in pending["groups"] for item in group["items"]]
    assert all(item["interest_charge_id"] != marked.id for item in listed), "a zero charge was billed"


def test_a_penalty_does_not_shrink_when_the_customer_pays_part_of_the_interest(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The penalty is fixed against what the period owed at its due date, and stays there.

    It used to be `pending interest x rate` evaluated on every read, so a partial payment
    lowered the very base it was computed from and the figure moved under the operator.
    """
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=40)

    charges = _charges(db_session, loan["id"])
    assert len(charges) == 1
    assert charges[0].penalty_amount == 5000, "10% of the 50.000 the period owed when it fell due"
    assert charges[0].penalty_rate_applied == 10

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 30000, "payment_method": "cash"},
    )
    assert payment.status_code == 200, payment.text

    assert _charges(db_session, loan["id"])[0].penalty_amount == 5000, "the recorded penalty moved"


def test_changing_grace_days_or_the_rate_leaves_recorded_penalties_alone(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Policy reaches the periods that fall due after it, never the ones already settled.

    Raising `default_grace_days` used to push every past due date forward and wipe the
    penalty off the whole portfolio backwards, with no record that anything had changed.
    """
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=40)

    def recorded_penalty() -> float:
        return _charges(db_session, loan["id"])[0].penalty_amount

    def reported_penalty() -> float:
        response = client.get(
            f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
        )
        assert response.status_code == 200, response.text
        return response.json()["total_pending_penalty"]

    assert recorded_penalty() == 5000
    assert reported_penalty() == 5000

    _configure(db_session, grace_days=45)
    assert recorded_penalty() == 5000
    assert reported_penalty() == 5000

    _configure(db_session, grace_days=5)
    edit = client.put(
        f"/api/v1/loans/{loan['id']}", headers=auth_headers, json={"late_penalty_rate": 2}
    )
    assert edit.status_code == 200, edit.text
    assert recorded_penalty() == 5000
    assert reported_penalty() == 5000


def test_a_loan_with_no_penalty_rate_records_a_zero_instead_of_nothing(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """A settled question, not an open one: the cycle must not revisit it every night."""
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=40, penalty_rate=0)

    charge = _charges(db_session, loan["id"])[0]
    assert charge.penalty_amount == 0
    assert charge.penalty_rate_applied == 0
    assert charge.penalty_applied_at is not None


def test_editing_a_loan_no_longer_requires_resending_rate_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=0)

    response = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"description": "only this changed"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["monthly_interest_rate"] == loan["monthly_interest_rate"]
    assert body["status"] == loan["status"]
