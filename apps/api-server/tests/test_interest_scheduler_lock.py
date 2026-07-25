import os
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Customer, Loan
from src.infrastructure.tasks.interest_scheduler import (
    INTEREST_CYCLE_LOCK_ID,
    run_interest_generation_cycle,
)


def _make_customer(db_session: Session) -> Customer:
    customer = Customer(
        first_name="Ana",
        last_name="Perez",
        document_type="ID",
        document_number="DOC-LOCK",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def _make_loan(db_session: Session, customer_id: int) -> Loan:
    loan = Loan(
        customer_id=customer_id,
        loan_type="pawn",
        principal_amount=1000,
        outstanding_principal=1000,
        monthly_interest_rate=10,
        late_penalty_rate=0,
        disbursement_date=date.today() - timedelta(days=60),
        due_day=5,
    )
    db_session.add(loan)
    db_session.commit()
    db_session.refresh(loan)
    return loan


def test_cycle_generates_charges_when_lock_is_free(db_session: Session) -> None:
    customer = _make_customer(db_session)
    loan = _make_loan(db_session, customer.id)

    generated = run_interest_generation_cycle(as_of_date=date.today(), db_session=db_session)

    assert generated >= 1
    assert loan.id is not None


def test_cycle_is_skipped_while_another_worker_holds_the_lock(db_session: Session) -> None:
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("advisory locks only apply to PostgreSQL")

    customer = _make_customer(db_session)
    _make_loan(db_session, customer.id)

    # Simulate a second uvicorn worker already running the cycle.
    other_engine = create_engine(test_database_url, future=True)
    with other_engine.connect() as connection:
        acquired = connection.scalar(
            text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": INTEREST_CYCLE_LOCK_ID}
        )
        assert acquired is True

        try:
            generated = run_interest_generation_cycle(as_of_date=date.today(), db_session=db_session)
            assert generated == 0
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": INTEREST_CYCLE_LOCK_ID}
            )

    other_engine.dispose()

    # With the lock released the cycle runs normally again.
    assert run_interest_generation_cycle(as_of_date=date.today(), db_session=db_session) >= 1
