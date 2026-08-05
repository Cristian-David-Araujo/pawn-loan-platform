from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import GlobalSettings, InterestCharge
from src.infrastructure.tasks.interest_scheduler import run_interest_generation_cycle


def test_generate_interest_for_active_loans(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    create_loan(principal=1200)
    create_loan(principal=800)

    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(date.today() + timedelta(days=40))},
    )
    assert response.status_code == 200
    charges = response.json()
    assert len(charges) == 2
    assert all(item["status"] == "generated" for item in charges)



def test_loan_balance_and_ledger(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    loan = create_loan(principal=1000)

    interest_response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(date.today() + timedelta(days=40))},
    )
    assert interest_response.status_code == 200

    payment_response = client.post(
        "/api/v1/payments",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "payment_date": str(date.today()),
            "total_amount": 150,
            "allocated_to_penalty": 0,
            "allocated_to_interest": 100,
            "allocated_to_fees": 0,
            "allocated_to_principal": 50,
            "payment_method": "cash",
        },
    )
    assert payment_response.status_code == 201

    balance_response = client.get(f"/api/v1/loans/{loan['id']}/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    balance = balance_response.json()
    assert balance["loan_id"] == loan["id"]
    assert balance["total_interest_generated"] > 0
    assert balance["total_payments"] == 150

    ledger_response = client.get(f"/api/v1/loans/{loan['id']}/ledger", headers=auth_headers)
    assert ledger_response.status_code == 200
    ledger = ledger_response.json()
    assert ledger["loan_id"] == loan["id"]
    assert len(ledger["interest_charges"]) >= 1
    assert len(ledger["payments"]) == 1


def _unbilled_cycle() -> tuple[date, date]:
    """A billing period that creating the loan cannot have billed yet.

    Loan creation generates charges up to `today + interest_generation_lead_days`, so a period
    that has already ended by the time the suite runs is billed on create and
    `POST /interest/generate` then correctly returns nothing new for it. These two tests used a
    fixed 2026-07-05 disbursement and 2026-08-05 cycle, which meant they only tested the
    endpoint while the real calendar was still short of that date: from ten days before it they
    failed on behaviour that was right. Anchoring two months ahead keeps the period out of
    reach of the lead window, and anchoring on the 1st makes "one month later" the same
    arithmetic in every month, including February.
    """
    today = date.today()
    start_index = today.month - 1 + 2
    period_start = date(today.year + start_index // 12, start_index % 12 + 1, 1)
    end_index = start_index + 1
    period_end = date(today.year + end_index // 12, end_index % 12 + 1, 1)
    return period_start, period_end


def test_generate_interest_uses_due_day_calendar_cycle(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CYCLE-1")
    period_start, period_end = _unbilled_cycle()
    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 8,
            "disbursement_date": str(period_start),
            "due_day": period_start.day,
        },
    )
    assert loan_response.status_code == 201

    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(period_end)},
    )
    assert response.status_code == 200
    charges = response.json()
    assert len(charges) == 1
    assert charges[0]["period_start"] == str(period_start)
    assert charges[0]["period_end"] == str(period_end)


def test_generate_interest_skips_duplicate_period(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CYCLE-2")
    period_start, period_end = _unbilled_cycle()
    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 8,
            "disbursement_date": str(period_start),
            "due_day": period_start.day,
        },
    )
    assert loan_response.status_code == 201

    first = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(period_end)},
    )
    assert first.status_code == 200
    assert len(first.json()) == 1

    second = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(period_end + timedelta(days=1))},
    )
    assert second.status_code == 200
    assert len(second.json()) == 0


def test_generate_interest_backfills_missing_periods(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CYCLE-3")
    disbursement_date = date.today()
    next_month = (disbursement_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    as_of_date = next_month + timedelta(days=70)

    loan_response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 8,
            "disbursement_date": str(disbursement_date),
            "due_day": disbursement_date.day,
        },
    )
    assert loan_response.status_code == 201

    response = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": str(as_of_date)},
    )
    assert response.status_code == 200

    charges = response.json()
    assert len(charges) >= 2


def test_pending_interest_penalty_uses_configured_loan_rate(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="PENALTY-RATE-LOAN")

    zero_penalty_loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 10,
            "late_penalty_rate": 0,
            "disbursement_date": "2026-01-05",
            "due_day": 5,
        },
    )
    assert zero_penalty_loan.status_code == 201

    configured_penalty_loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 1000,
            "monthly_interest_rate": 10,
            "late_penalty_rate": 3,
            "disbursement_date": "2026-01-05",
            "due_day": 5,
        },
    )
    assert configured_penalty_loan.status_code == 201

    generated = client.post(
        "/api/v1/interest/generate",
        headers=auth_headers,
        json={"as_of_date": "2026-02-05"},
    )
    assert generated.status_code == 200

    pending = client.get(f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers)
    assert pending.status_code == 200

    groups = pending.json()["groups"]
    items = [item for group in groups for item in group["items"]]

    zero_penalty_id = zero_penalty_loan.json()["id"]
    configured_penalty_id = configured_penalty_loan.json()["id"]

    zero_penalty_items = [item for item in items if item["loan_id"] == zero_penalty_id]
    configured_penalty_items = [item for item in items if item["loan_id"] == configured_penalty_id]

    assert all(item["penalty_amount"] == 0 for item in zero_penalty_items)
    assert any(item["penalty_amount"] > 0 for item in configured_penalty_items)


def test_auto_interest_generation_cycle_creates_due_charges(
    db_session,
    create_loan,
) -> None:
    create_loan(principal=1000)

    generated = run_interest_generation_cycle(
        as_of_date=date.today() + timedelta(days=40),
        db_session=db_session,
    )
    assert generated == 1

    charges = list(db_session.scalars(select(InterestCharge)).all())
    assert len(charges) == 1


def _set_grace_days(db_session: Session, days: int) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = days
    db_session.commit()


def test_grace_days_come_from_the_setting_not_the_disbursement_day(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """A loan signed on the 25th used to get 25 days of grace, one signed on the 3rd got 3."""
    _set_grace_days(db_session, 5)
    customer = create_customer(document_number="GRACE-POLICY")

    created = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "personal",
            "principal_amount": 500,
            "monthly_interest_rate": 5,
            "late_penalty_rate": 2,
            "disbursement_date": str(date.today().replace(day=25) - timedelta(days=31)),
            "due_day": 25,
        },
    )
    assert created.status_code == 201
    assert created.json()["due_day"] == 5

    charges = client.get(f"/api/v1/loans/{created.json()['id']}/ledger", headers=auth_headers)
    assert charges.status_code == 200


def test_a_loan_without_penalty_gets_no_grace(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Grace only postpones the penalty, so a penalty-free loan is due when the period ends.

    Otherwise the debt sits as "upcoming" for the whole grace window and stays out of the
    collection screens even though nothing can ever be charged for paying late.
    """
    _set_grace_days(db_session, 30)
    customer = create_customer(document_number="GRACE-NO-PENALTY")

    disbursed = date.today() - timedelta(days=40)
    created = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "personal",
            "principal_amount": 1000,
            "monthly_interest_rate": 10,
            "late_penalty_rate": 0,
            "disbursement_date": str(disbursed),
        },
    )
    assert created.status_code == 201
    loan_id = created.json()["id"]

    pending = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    )
    assert pending.status_code == 200
    items = [item for group in pending.json()["groups"] for item in group["items"]]
    assert items, "the loan accrued interest and should be collectable"

    item = items[0]
    charge = db_session.scalars(
        select(InterestCharge).where(InterestCharge.id == item["interest_charge_id"])
    ).one()
    # No grace: the period is due the day it ends, despite the 30 day global setting.
    assert item["due_date"] == str(charge.period_end)
    assert item["overdue"] is True
    assert loan_id == item["loan_id"]


def test_the_same_billing_period_cannot_be_charged_twice(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """The database is what guarantees it; the advisory lock only makes the race rare.

    A scheduler cycle overlapping the manual endpoint produced duplicate charges that
    customers were then billed — and in some cases paid — twice.
    """
    loan = create_loan(principal=1000)
    charge = InterestCharge(
        loan_id=loan["id"],
        period_start=date.today() - timedelta(days=60),
        period_end=date.today() - timedelta(days=30),
        charge_date=date.today() - timedelta(days=30),
        amount=100,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()

    duplicate = InterestCharge(
        loan_id=loan["id"],
        period_start=charge.period_start,
        period_end=charge.period_end,
        charge_date=charge.charge_date,
        amount=100,
        status="generated",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
