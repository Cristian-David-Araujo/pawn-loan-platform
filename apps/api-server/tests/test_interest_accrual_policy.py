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
from src.infrastructure.persistence.models import (
    Customer,
    GlobalSettings,
    InterestCharge,
    Loan,
    PaymentEvent,
)
from src.infrastructure.tasks.interest_scheduler import run_interest_generation_cycle


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


def test_a_period_still_running_does_not_block_a_principal_payment(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """`interest_generation_lead_days` bills the month in progress on purpose.

    Showing it as pending is the point of the setting — it lets the upcoming period appear on
    the collection screen early. Blocking on it was not: a customer was refused their own
    principal payment over interest for days that had not happened yet.
    """
    _configure(db_session, lead_days=10)
    customer = create_customer()
    # Disbursed 25 days ago: the period ends in 5 days, so lead days have already billed it.
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=25, penalty_rate=0)

    charges = _charges(db_session, loan["id"])
    assert len(charges) == 1, "expected the period in progress to be billed early"
    assert charges[0].period_end > date.today()

    pending = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert pending["total_pending_interest"] == 50000, "the upcoming period should still be visible"

    paid = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 400000, "payment_method": "cash"},
    )
    assert paid.status_code == 200, paid.text

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).outstanding_principal == 600000


def test_a_period_that_has_ended_still_blocks_a_principal_payment(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The rule itself stands: interest that has accrued comes before principal."""
    _configure(db_session, lead_days=10)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=40, penalty_rate=0)

    refused = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 400000, "payment_method": "cash"},
    )
    assert refused.status_code == 400
    assert "unpaid accrued interest" in refused.json()["detail"].lower()


def test_editing_a_payment_corrects_how_it_was_recorded_not_how_much_it_moved(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Amounts sent to the edit endpoint are ignored, and every ledger row follows the rest.

    A collection of 100.000 covering two periods, edited down to 50.000, used to leave the
    `Payment` row saying 50.000 while the ledger kept 100.000 and the customer's debt stayed
    reduced by the larger figure — the receipt and the balance describing different money.
    The ledger rows were found by matching six fields on their exact old values, so a
    payment split across periods matched more than one and none of them was updated.
    """
    _configure(db_session)
    customer = create_customer()
    _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=65, penalty_rate=0)

    collected = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 100000, "payment_method": "cash"},
    )
    assert collected.status_code == 200, collected.text
    payment_id = collected.json()["allocations"][0]["payment_id"]
    assert len({item["payment_event_id"] for item in collected.json()["allocations"]}) == 2

    def pending() -> float:
        response = client.get(
            f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
        )
        return response.json()["total_pending_interest"]

    assert pending() == 0

    edited = client.put(
        f"/api/v1/payments/{payment_id}",
        headers=auth_headers,
        json={
            "payment_date": date.today().isoformat(),
            "payment_method": "transfer",
            "notes": "was a transfer, not cash",
            # Sent by an old client; must not move a peso.
            "total_amount": 50000,
            "allocated_to_interest": 50000,
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["total_amount"] == 100000, "an edit changed the amount collected"
    assert edited.json()["payment_method"] == "transfer"
    assert pending() == 0, "an edit moved the customer's debt"

    db_session.expire_all()
    events = list(db_session.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == payment_id)).all())
    assert len(events) == 2
    assert all(item.payment_method == "transfer" for item in events), "a ledger row kept the old method"
    assert sum(item.allocated_to_interest for item in events) == 100000


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


def test_a_backlogged_period_is_billed_on_the_principal_it_carried(db_session: Session) -> None:
    """A cycle catching up must not bill old periods on today's balance.

    The amount used to be `outstanding_principal * rate` against the balance at the moment
    the cycle ran, which is the balance the period carried only while the cycle is on time.
    Stopped for three months over a 700.000 principal payment, it billed all three backlogged
    periods on the remaining 300.000 — two of them at a third of what was owed, silently.
    """
    db_session.add(GlobalSettings(id=1, default_grace_days=0, interest_generation_lead_days=0))
    customer = Customer(first_name="Ana", last_name="Perez", document_type="ID", document_number="DOC-BASE")
    db_session.add(customer)
    db_session.commit()

    disbursed = date.today() - timedelta(days=95)
    loan = Loan(
        customer_id=customer.id, loan_type="personal", principal_amount=1000000,
        outstanding_principal=300000, monthly_interest_rate=3, late_penalty_rate=0,
        disbursement_date=disbursed, due_day=0,
    )
    db_session.add(loan)
    db_session.commit()

    # Paid on day 40: after the first period ended, before the other two.
    db_session.add(
        PaymentEvent(
            payment_type="principal_payment", loan_id=loan.id, total_entered_amount=700000,
            allocated_to_principal=700000, payment_date=disbursed + timedelta(days=40),
        )
    )
    db_session.commit()

    run_interest_generation_cycle(as_of_date=date.today(), db_session=db_session)

    charges = _charges(db_session, loan.id)
    assert [charge.amount for charge in charges] == [30000.0, 9000.0, 9000.0]
    assert [charge.principal_base for charge in charges] == [1000000.0, 300000.0, 300000.0]


def test_moving_the_disbursement_date_keeps_every_invoiced_period(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Re-anchoring a loan may not delete what has already been invoiced.

    `PUT /loans/{id}` re-derives every period from the disbursement date, and used to delete
    each charge that no longer matched and carried no payment — taking with it the late
    penalties frozen on those periods and the zero-amount markers that record a month which
    was deliberately never billed. A two-day correction rewrote months of history.
    """
    _configure(db_session, grace_days=0)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=95)

    before = _charges(db_session, loan["id"])
    assert len(before) == 3
    assert all(charge.penalty_applied_at is not None for charge in before)
    frozen_penalty = round(sum(charge.penalty_amount for charge in before), 2)
    assert frozen_penalty > 0

    marker = InterestCharge(
        loan_id=loan["id"],
        period_start=date.today() - timedelta(days=400),
        period_end=date.today() - timedelta(days=370),
        charge_date=date.today() - timedelta(days=370),
        amount=0.0,
        status="not_billed",
    )
    db_session.add(marker)
    db_session.commit()
    marker_id = marker.id

    shifted = (date.today() - timedelta(days=93)).isoformat()
    response = client.put(f"/api/v1/loans/{loan['id']}", headers=auth_headers, json={"disbursement_date": shifted})
    assert response.status_code == 200, response.text

    after = _charges(db_session, loan["id"])
    assert {charge.id for charge in before} <= {charge.id for charge in after}, "an invoiced period was deleted"
    assert round(sum(charge.penalty_amount or 0 for charge in after), 2) == frozen_penalty
    assert db_session.get(InterestCharge, marker_id) is not None, "the not_billed marker was deleted"
    # The new anchor may not bill a stretch of time an existing invoice already covers.
    spans = sorted((charge.period_start, charge.period_end) for charge in after if charge.amount > 0)
    assert all(spans[index][1] <= spans[index + 1][0] for index in range(len(spans) - 1)), "periods overlap"


def test_a_defaulted_loan_stops_accruing_late_penalties(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Foreclosing stops interest; the late penalty is interest by another name.

    Accrual already excluded `defaulted` — collecting through the pledge is the decision not
    to keep charging — but the freeze ran off `penalty_applied_at IS NULL` alone, so a period
    billed before the foreclosure still grew a penalty afterwards.
    """
    _configure(db_session, grace_days=0, lead_days=15)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=0)

    # Billed early thanks to the lead days, but not due yet, so no penalty is frozen.
    run_interest_generation_cycle(as_of_date=date.today() + timedelta(days=20), db_session=db_session)
    charges = _charges(db_session, loan["id"])
    assert len(charges) == 1
    assert charges[0].penalty_applied_at is None

    assert client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers, json={}).status_code == 200

    run_interest_generation_cycle(as_of_date=date.today() + timedelta(days=40), db_session=db_session)

    charges = _charges(db_session, loan["id"])
    assert len(charges) == 1, "a defaulted loan kept accruing interest"
    assert charges[0].penalty_amount is None, "a defaulted loan was charged a late penalty"
