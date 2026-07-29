import os
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Customer, Loan
from src.infrastructure.tasks.interest_scheduler import (
    INTEREST_CYCLE_LOCK_ID,
    interest_cycle_lock,
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


def test_the_lock_lives_on_a_connection_of_its_own(db_session: Session) -> None:
    """The lock must not sit on the connection the cycle keeps committing.

    `pg_try_advisory_lock` is session level: it lives on the connection. Taken on the
    caller's `Session`, it outlived every commit — and a Session hands its connection back
    to the pool on each one. Whenever a request checked that connection out in between, the
    release ran somewhere else, returned false (a value nobody read), and the lock stayed on
    a pooled connection for good: every later cycle reported a phantom worker and the
    portfolio stopped being billed until the process was restarted.
    """
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("advisory locks only apply to PostgreSQL")

    def holder_pid() -> int | None:
        return db_session.scalar(
            text("SELECT pid FROM pg_locks WHERE locktype = 'advisory' AND objid = :lock_id"),
            {"lock_id": INTEREST_CYCLE_LOCK_ID},
        )

    with interest_cycle_lock(db_session) as acquired:
        assert acquired is True
        before_commit = db_session.scalar(text("SELECT pg_backend_pid()"))
        db_session.commit()  # what the cycle does, up to three times, while holding it
        after_commit = db_session.scalar(text("SELECT pg_backend_pid()"))

        held_by = holder_pid()
        assert held_by is not None, "the lock was not held during the cycle"
        assert held_by not in (before_commit, after_commit), "the lock rides the session's connection"

    assert holder_pid() is None, "the lock outlived the block that took it"


def test_the_lock_is_released_even_though_the_cycle_commits(db_session: Session) -> None:
    """The lock must not survive its own cycle.

    `pg_try_advisory_lock` is session level: it lives on the connection. It used to be taken
    on the cycle's `Session`, which hands its connection back to the pool on every commit —
    and the cycle commits up to three times. A request served in between could check that
    connection out, so the release ran on a different one, returned false (nobody looked),
    and the lock stayed on a pooled connection: from then on every cycle read "another worker
    is already running it" and the portfolio stopped being billed until a restart.
    """
    test_database_url = os.getenv("TEST_DATABASE_URL")
    if not test_database_url:
        pytest.skip("advisory locks only apply to PostgreSQL")

    customer = _make_customer(db_session)
    _make_loan(db_session, customer.id)

    # Hold a connection for the whole cycle, the way a request being served would.
    busy_engine = create_engine(test_database_url, future=True)
    with busy_engine.connect() as squatter:
        squatter.execute(text("SELECT 1"))
        assert run_interest_generation_cycle(as_of_date=date.today(), db_session=db_session) >= 1

        held = squatter.execute(
            text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND objid = :lock_id"),
            {"lock_id": INTEREST_CYCLE_LOCK_ID},
        ).scalar()
        assert held == 0, "the cycle lock outlived the cycle that took it"

    busy_engine.dispose()

    # And the next cycle still runs rather than reporting a phantom worker.
    run_interest_generation_cycle(as_of_date=date.today() + timedelta(days=40), db_session=db_session)
