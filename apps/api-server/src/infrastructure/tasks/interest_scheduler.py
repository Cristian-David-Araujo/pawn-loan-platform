import logging
from datetime import date, timedelta
from threading import Event, Thread

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from src.infrastructure.persistence.database import SessionLocal
from src.infrastructure.persistence.models import GlobalSettings, Loan
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_generation import (
    ACCRUING_STATUSES,
    generate_missing_interest_charges_for_loan,
)
from src.modules.finance.loan_status import describe_transitions, refresh_overdue_loan_statuses
from src.modules.finance.penalties import describe_frozen_penalties, freeze_due_penalties
from src.shared.utils.audit import write_audit

logger = logging.getLogger(__name__)

# The API runs with several uvicorn workers and each one starts its own scheduler.
# Without this lock two workers can generate the same billing period concurrently and
# charge the customer twice, since nothing at the database level rejects duplicates.
INTEREST_CYCLE_LOCK_ID = 9021002


def try_acquire_cycle_lock(db: Session) -> bool:
    if db.get_bind().dialect.name != "postgresql":
        return True

    return bool(db.scalar(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": INTEREST_CYCLE_LOCK_ID}))


def release_cycle_lock(db: Session) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return

    try:
        db.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": INTEREST_CYCLE_LOCK_ID})
    except Exception:
        logger.exception("Could not release the interest generation lock")


def run_interest_generation_cycle(
    as_of_date: date | None = None,
    db_session: Session | None = None,
) -> int:
    db = db_session or SessionLocal()
    should_close_session = db_session is None

    if not try_acquire_cycle_lock(db):
        logger.info("Interest generation cycle skipped: another worker is already running it")
        if should_close_session:
            db.close()
        return 0

    try:
        settings = db.get(GlobalSettings, 1)
        lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
        reference_date = as_of_date or get_local_date(db)
        effective_as_of_date = reference_date + timedelta(days=lead_days)

        loans = list(db.scalars(select(Loan).where(Loan.status.in_(ACCRUING_STATUSES))).all())
        generated = []
        for loan in loans:
            generated.extend(
                generate_missing_interest_charges_for_loan(
                    db=db,
                    loan=loan,
                    as_of_date=effective_as_of_date,
                    charge_date=reference_date,
                )
            )

        if generated:
            db.commit()

        write_audit(
            db,
            action="auto_generate_interest",
            entity_type="InterestCharge",
            entity_id=f"count={len(generated)}",
            new_data=f"as_of_date={reference_date}",
        )

        # Periods that crossed their due date get their penalty fixed before anything reads
        # a balance, so the figure the collection screens show is the one that was recorded.
        frozen = freeze_due_penalties(db, reference_date)
        if frozen:
            db.commit()
            write_audit(
                db,
                action="auto_freeze_late_penalties",
                entity_type="InterestCharge",
                entity_id=f"count={len(frozen)}",
                new_data=f"as_of_date={reference_date},{describe_frozen_penalties(frozen)}",
            )

        # Newly generated charges can push loans past their grace period, so statuses
        # are refreshed in the same cycle.
        transitions = refresh_overdue_loan_statuses(db, reference_date)
        if transitions:
            db.commit()
            write_audit(
                db,
                action="auto_refresh_loan_statuses",
                entity_type="Loan",
                entity_id=f"count={len(transitions)}",
                new_data=f"as_of_date={reference_date},{describe_transitions(transitions)}",
            )

        return len(generated)
    except Exception:
        db.rollback()
        logger.exception("Automatic interest generation cycle failed")
        return 0
    finally:
        release_cycle_lock(db)
        if should_close_session:
            db.close()


class InterestGenerationScheduler:
    def __init__(self, interval_minutes: int) -> None:
        self.interval_seconds = max(60, interval_minutes * 60)
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="interest-generation-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        generated = run_interest_generation_cycle()
        logger.info("Automatic interest generation cycle completed with %s charges", generated)

        while not self._stop_event.wait(timeout=self.interval_seconds):
            generated = run_interest_generation_cycle()
            logger.info("Automatic interest generation cycle completed with %s charges", generated)