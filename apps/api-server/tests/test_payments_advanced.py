from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan, Payment, PaymentEvent
from src.infrastructure.utils.datetime_utils import get_local_date


def _create_interest_charge(db_session: Session, loan_id: int, amount: float = 100.0) -> InterestCharge:
    """A charge whose period the application considers ended.

    The dates come from `get_local_date`, not `date.today()`. The endpoints compare
    `period_end` against the date in `GlobalSettings.timezone` (America/Bogota by default),
    while `date.today()` is the *machine's* date — UTC on a CI runner. Between 00:00 and
    05:00 UTC those are different days, so a charge built on the machine clock landed one day
    in the future of the application clock and
    `test_principal_payment_requires_flag_when_unpaid_interest_exists` saw 200 instead of
    400. The suite passed locally and failed in CI for five hours a day.
    """
    today = get_local_date(db_session)
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=today,
        period_end=today,
        charge_date=today,
        amount=amount,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()
    db_session.refresh(charge)
    return charge


def test_interest_pending_groups_for_customer(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_interest_charge(db_session, loan["id"], amount=120)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == loan_db.customer_id
    assert payload["total_pending_interest"] > 0
    assert len(payload["groups"]) >= 1


def test_partial_interest_payment_and_traceability(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1100)
    charge = _create_interest_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 40,
            "payment_method": "cash",
            "notes": "partial interest",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_allocated_amount"] == 40
    assert payload["allocations"][0]["payment_type"] == "partial_interest_payment"

    history = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/history", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) >= 1


def test_selected_interest_with_excess_creates_advance(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=900)
    charge = _create_interest_charge(db_session, loan["id"], amount=70)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    before_payment_count = db_session.query(Payment).count()

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 100,
            "payment_method": "cash",
            "notes": "selected plus advance",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    linked_allocations = [item for item in payload["allocations"] if item["interest_charge_id"] is not None]
    advance_allocations = [item for item in payload["allocations"] if item["interest_charge_id"] is None]
    assert len(linked_allocations) == 1
    assert linked_allocations[0]["payment_id"] is not None
    assert linked_allocations[0]["allocated_total"] == 70
    assert len(advance_allocations) == 1
    assert advance_allocations[0]["payment_id"] == linked_allocations[0]["payment_id"]
    assert advance_allocations[0]["payment_type"] == "interest_advance_payment"

    after_payment_count = db_session.query(Payment).count()
    assert after_payment_count == before_payment_count + 1
    registered_payment = db_session.query(Payment).order_by(Payment.id.desc()).first()
    assert registered_payment is not None
    assert registered_payment.total_amount == 100
    assert registered_payment.allocated_to_interest == 100
    assert registered_payment.allocated_to_penalty == 0


def test_interest_advance_without_pending_charges(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1300)
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": True,
            "total_amount": 25,
            "payment_method": "cash",
            "notes": "advance only",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_allocated_amount"] == 25
    assert payload["allocations"][0]["payment_type"] == "interest_advance_payment"


def test_interest_payment_with_pending_ignores_explicit_advance_and_applies_oldest_first(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1500)
    old_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        charge_date=date(2026, 1, 31),
        amount=80,
        status="generated",
    )
    new_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        charge_date=date(2026, 2, 28),
        amount=80,
        status="generated",
    )
    db_session.add_all([old_charge, new_charge])
    db_session.commit()

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    # Previously this payload created an explicit advance. New rule enforces oldest-first allocation.
    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": False,
            "total_amount": 15,
            "payment_method": "cash",
            "notes": "explicit advance",
        },
    )
    assert payment.status_code == 200

    pending = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200
    items = [item for group in pending.json()["groups"] for item in group["items"]]
    oldest = min(items, key=lambda item: item["due_date"])
    newest = max(items, key=lambda item: item["due_date"])
    assert oldest["remaining_pending_amount"] == 65
    assert newest["remaining_pending_amount"] == 80


def test_selected_partial_plus_explicit_advance(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1600)
    charge = _create_interest_charge(db_session, loan["id"], amount=100)
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    partial = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 30,
            "payment_method": "cash",
            "notes": "selected partial",
        },
    )
    assert partial.status_code == 200

    advance = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": False,
            "total_amount": 25,
            "payment_method": "cash",
            "notes": "extra advance",
        },
    )
    assert advance.status_code == 200
    assert advance.json()["allocations"][0]["payment_type"] in {
        "interest_payment",
        "partial_interest_payment",
        "interest_advance_payment",
    }


def test_interest_allocation_still_starts_from_oldest_when_only_newer_charge_is_selected(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1750)
    old_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        charge_date=date(2026, 1, 31),
        amount=100,
        status="generated",
    )
    new_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        charge_date=date(2026, 2, 28),
        amount=100,
        status="generated",
    )
    db_session.add_all([old_charge, new_charge])
    db_session.commit()

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [new_charge.id],
            "pay_all_pending": False,
            "total_amount": 30,
            "payment_method": "cash",
            "notes": "newer selected",
        },
    )
    assert payment.status_code == 200

    pending = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200
    items = [item for group in pending.json()["groups"] for item in group["items"]]
    oldest = min(items, key=lambda item: item["due_date"])
    newest = max(items, key=lambda item: item["due_date"])
    assert oldest["remaining_pending_amount"] == 70
    assert newest["remaining_pending_amount"] == 100


def test_advance_is_applied_to_oldest_pending_charge(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1700)
    old_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        charge_date=date(2026, 1, 31),
        amount=100,
        status="generated",
    )
    new_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        charge_date=date(2026, 2, 28),
        amount=80,
        status="generated",
    )
    db_session.add_all([old_charge, new_charge])
    db_session.commit()

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    advance = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": False,
            "total_amount": 30,
            "payment_method": "cash",
            "notes": "advance to oldest",
        },
    )
    assert advance.status_code == 200

    pending = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200
    items = [item for group in pending.json()["groups"] for item in group["items"]]
    oldest = min(items, key=lambda item: item["due_date"])
    assert oldest["remaining_pending_amount"] == 70


def test_advance_carries_forward_and_is_consumed_when_new_charge_appears(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1800)
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    advance = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": False,
            "total_amount": 25,
            "payment_method": "cash",
            "notes": "carry forward",
        },
    )
    assert advance.status_code == 200

    no_pending = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert no_pending.status_code == 200
    assert no_pending.json()["total_outstanding"] == 0
    assert no_pending.json()["available_advance_balance"] == 25

    new_charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        charge_date=date(2026, 3, 31),
        amount=60,
        status="generated",
    )
    db_session.add(new_charge)
    db_session.commit()

    pending_after = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert pending_after.status_code == 200
    assert pending_after.json()["total_pending_interest"] == 35


def test_principal_payment_requires_flag_when_unpaid_interest_exists(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=800)
    _create_interest_charge(db_session, loan["id"], amount=50)

    blocked = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 20,
            "payment_method": "cash",
            "allow_with_unpaid_interest": False,
            "notes": "should fail",
        },
    )
    assert blocked.status_code == 400

    allowed = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 20,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
            "notes": "allowed",
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["allocated_to_principal"] == 20


def test_principal_block_survives_a_server_timezone_behind_the_machine(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """The block must not depend on the machine and the portfolio sharing a calendar day.

    `GlobalSettings.timezone` is what the endpoints call "today", and it is routinely behind
    the host clock — America/Bogota is five hours behind UTC, which is what a CI runner uses.
    A charge built from `date.today()` therefore landed a day in the *future* of the
    application's date for five hours out of every twenty-four, `period_end <= payment_date`
    came out false, and a principal payment that should have been refused was accepted.

    This pins the skew open deliberately: the portfolio is put a full day behind the host, and
    a period that ended before that date must still block.
    """
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.timezone = "Pacific/Niue"  # UTC-11, behind every runner we use
    db_session.commit()

    loan = create_loan(principal=800)

    # Ended before the portfolio's own date, whatever the host clock says.
    charge = InterestCharge(
        loan_id=loan["id"],
        period_start=get_local_date(db_session) - timedelta(days=31),
        period_end=get_local_date(db_session) - timedelta(days=1),
        charge_date=get_local_date(db_session) - timedelta(days=1),
        amount=50,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()

    blocked = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 20,
            "payment_method": "cash",
            "allow_with_unpaid_interest": False,
        },
    )
    assert blocked.status_code == 400, blocked.text
    assert "unpaid accrued interest" in blocked.json()["detail"]


def _create_loan_for(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    principal: float,
    days_ago: int,
) -> dict:
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "loan_type": "pawn",
            "principal_amount": principal,
            "monthly_interest_rate": 10.0,
            "disbursement_date": str(date.today() - timedelta(days=days_ago)),
            "due_day": 5,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_principal_payment_spreads_over_several_loans_oldest_first(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """One payment can settle a whole loan and part of the next, oldest disbursement first."""
    customer = create_customer(document_number="DOC-MULTI-PRINCIPAL")
    older = _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)
    newer = _create_loan_for(client, auth_headers, customer["id"], principal=500, days_ago=10)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "pay_all_outstanding": True,
            "total_amount": 400,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert [item["loan_id"] for item in body["allocations"]] == [older["id"], newer["id"]]
    assert body["total_allocated_amount"] == 400
    assert body["allocations"][0]["allocated_to_principal"] == 300
    assert body["allocations"][0]["new_outstanding_principal"] == 0
    assert body["allocations"][0]["loan_status"] == LoanStatus.closed.value
    assert body["allocations"][1]["allocated_to_principal"] == 100
    assert body["allocations"][1]["new_outstanding_principal"] == 400

    # Both ledger rows hang off one payment, so the receipt can show the split.
    assert len({item["payment_event_id"] for item in body["allocations"]}) == 2
    events = db_session.scalars(
        select(PaymentEvent).where(PaymentEvent.payment_id == body["payment_id"])
    ).all()
    assert len(list(events)) == 2


def test_principal_payment_honours_the_selected_loans(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Unlike interest, a principal selection is obeyed: money must not drift elsewhere."""
    customer = create_customer(document_number="DOC-SELECT-PRINCIPAL")
    older = _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)
    newer = _create_loan_for(client, auth_headers, customer["id"], principal=500, days_ago=10)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "selected_loan_ids": [newer["id"]],
            "total_amount": 200,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert [item["loan_id"] for item in body["allocations"]] == [newer["id"]]
    assert db_session.get(Loan, older["id"]).outstanding_principal == 300
    assert db_session.get(Loan, newer["id"]).outstanding_principal == 300


def test_principal_payment_over_the_selected_capacity_changes_nothing(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """A payment that cannot be fully applied is refused, not applied halfway."""
    customer = create_customer(document_number="DOC-OVER-PRINCIPAL")
    older = _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)
    newer = _create_loan_for(client, auth_headers, customer["id"], principal=500, days_ago=10)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "selected_loan_ids": [older["id"]],
            "total_amount": 400,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert response.status_code == 400

    db_session.expire_all()
    assert db_session.get(Loan, older["id"]).outstanding_principal == 300
    assert db_session.get(Loan, newer["id"]).outstanding_principal == 500
    assert db_session.scalars(select(Payment).where(Payment.loan_id == older["id"])).first() is None


def test_principal_payment_blocked_by_unpaid_interest_names_the_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The per-loan interest rule still applies when the payment covers several loans."""
    customer = create_customer(document_number="DOC-BLOCKED-PRINCIPAL")
    older = _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)
    _create_loan_for(client, auth_headers, customer["id"], principal=500, days_ago=10)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "pay_all_outstanding": True,
            "total_amount": 100,
            "payment_method": "cash",
            "allow_with_unpaid_interest": False,
        },
    )
    assert response.status_code == 400
    assert str(older["id"]) in response.json()["detail"]

    db_session.expire_all()
    assert db_session.get(Loan, older["id"]).outstanding_principal == 300


def test_principal_payment_needs_a_target(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="DOC-NOTARGET-PRINCIPAL")
    _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)

    response = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 100, "allow_with_unpaid_interest": True},
    )
    assert response.status_code == 400


def test_interest_survives_a_loan_closed_with_unpaid_interest(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """Paying off principal with `allow_with_unpaid_interest` must not erase the interest.

    `pay_principal` closes the loan the moment principal hits zero. When the interest reads
    dropped every closed loan, the leftover charges disappeared from the collection screens
    and from the printed balances: the receipt said "settled in full, nothing pending" on a
    loan that still owed, and no screen could ever collect it.
    """
    loan = create_loan(principal=500)
    _create_interest_charge(db_session, loan["id"], amount=120)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None
    customer_id = loan_db.customer_id

    settled = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 500,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert settled.status_code == 200
    assert settled.json()["loan_status"] == LoanStatus.closed.value

    # Still collectable: the periods remain on the interest screen.
    pending = client.get(f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200
    assert pending.json()["total_pending_interest"] == 120

    # Still printable: the receipt reads these figures, and zero principal must not imply
    # zero debt.
    context = client.get(f"/api/v1/payments/customers/{customer_id}/principal-context", headers=auth_headers)
    assert context.status_code == 200
    entry = next(item for item in context.json()["items"] if item["loan_id"] == loan["id"])
    assert entry["outstanding_principal"] == 0
    assert entry["accrued_unpaid_interest"] == 120
    assert entry["total_payoff_amount"] == 120

    # And payable: the money can actually be taken afterwards.
    paid = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer_id, "pay_all_pending": True, "total_amount": 120},
    )
    assert paid.status_code == 200

    after = client.get(f"/api/v1/payments/customers/{customer_id}/interest-pending", headers=auth_headers)
    assert after.json()["total_pending_interest"] == 0

    # Once it owes nothing the closed loan drops out again, so history stays out of the way.
    settled_context = client.get(
        f"/api/v1/payments/customers/{customer_id}/principal-context", headers=auth_headers
    )
    assert all(item["loan_id"] != loan["id"] for item in settled_context.json()["items"])


def test_reversal_records_who_when_and_why(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    """Reversal is how a payment is deleted, so it has to be answerable."""
    loan = create_loan(principal=600)

    payment = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 200,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["payment_id"]

    # A blank reason is refused: an unexplained deletion is not traceable.
    assert (
        client.post(
            f"/api/v1/payments/{payment_id}/reverse",
            headers=auth_headers,
            json={"reason": "  "},
        ).status_code
        == 422
    )

    reversal = client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        headers=auth_headers,
        json={"reason": "Cobrado dos veces por error de caja"},
    )
    assert reversal.status_code == 200
    body = reversal.json()

    assert body["is_reversed"] is True
    assert body["reversal_reason"] == "Cobrado dos veces por error de caja"
    assert body["reversed_at"] is not None
    assert body["reverser"]["username"] == "admin"

    # The listing carries it too, so the UI can explain a struck-through row.
    listed = next(
        item for item in client.get("/api/v1/payments", headers=auth_headers).json()
        if item["id"] == payment_id
    )
    assert listed["reversal_reason"] == "Cobrado dos veces por error de caja"


def test_reversing_a_multi_loan_principal_payment_restores_each_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Principal goes back to the loan that received it, not all to the first one.

    `Payment.loan_id` only points at the first target, so crediting the whole
    `allocated_to_principal` there over-restored that loan and left the others short.
    """
    customer = create_customer(document_number="DOC-REVERSE-MULTI")
    older = _create_loan_for(client, auth_headers, customer["id"], principal=300, days_ago=90)
    newer = _create_loan_for(client, auth_headers, customer["id"], principal=500, days_ago=10)

    payment = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "pay_all_outstanding": True,
            "total_amount": 400,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["payment_id"]

    db_session.expire_all()
    assert db_session.get(Loan, older["id"]).outstanding_principal == 0
    assert db_session.get(Loan, older["id"]).status == LoanStatus.closed
    assert db_session.get(Loan, newer["id"]).outstanding_principal == 400

    reversal = client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        headers=auth_headers,
        json={"reason": "Pago anulado por el cliente"},
    )
    assert reversal.status_code == 200

    db_session.expire_all()
    # Each loan gets back exactly what it received, and the one this payment closed reopens.
    assert db_session.get(Loan, older["id"]).outstanding_principal == 300
    assert db_session.get(Loan, older["id"]).status != LoanStatus.closed
    assert db_session.get(Loan, newer["id"]).outstanding_principal == 500
