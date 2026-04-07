import logging
from datetime import date, timedelta
from threading import Event, Thread

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.database import SessionLocal
from src.infrastructure.persistence.models import GlobalSettings, Loan
from src.modules.finance.interest_generation import generate_missing_interest_charges_for_loan
from src.shared.utils.audit import write_audit

logger = logging.getLogger(__name__)


def run_interest_generation_cycle(
    as_of_date: date | None = None,
    db_session: Session | None = None,
) -> int:
    db = db_session or SessionLocal()
    should_close_session = db_session is None
    try:
        settings = db.get(GlobalSettings, 1)
        lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
        reference_date = as_of_date or date.today()
        effective_as_of_date = reference_date + timedelta(days=lead_days)

        loans = list(db.scalars(select(Loan).where(Loan.status == LoanStatus.active)).all())
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

        return len(generated)
    except Exception:
        db.rollback()
        logger.exception("Automatic interest generation cycle failed")
        return 0
    finally:
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