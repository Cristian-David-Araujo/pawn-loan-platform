"""In-process scheduler for the recurring backup.

Same shape as the interest generation scheduler: a daemon thread per uvicorn worker, guarded
by an advisory lock so only one worker actually takes the copy. Its own lock id, not the
interest one — a backup is a read and has no reason to be held up by a billing cycle, and
sharing an id would make each job able to postpone the other.

The thread wakes far more often than the schedule fires and asks the database whether the
current slot still needs a copy. That is deliberate: the answer lives in ``backup_runs``, so
a restart, a redeploy or three days of downtime cannot skip a slot, and no worker needs to
remember anything between wake-ups.
"""

import logging
from threading import Event, Thread

from sqlalchemy.orm import Session

from src.infrastructure.persistence.database import SessionLocal
from src.infrastructure.persistence.models import BackupRun
from src.infrastructure.tasks.locks import advisory_lock
from src.modules.backup.runner import SCHEDULED, run_backup
from src.modules.backup.schedule import ensure_backup_settings, is_backup_due, local_now

logger = logging.getLogger(__name__)

# Distinct from INTEREST_CYCLE_LOCK_ID on purpose; see the module docstring.
BACKUP_CYCLE_LOCK_ID = 9021003


def run_due_backup(db_session: Session | None = None) -> BackupRun | None:
    """Take the scheduled copy if the current slot still needs one.

    Returns the run, or ``None`` when nothing was due or another worker is doing it.
    """
    db = db_session or SessionLocal()
    should_close_session = db_session is None

    try:
        settings = ensure_backup_settings(db)
        if not settings.enabled:
            return None

        # Checked before the lock as well as after: the common case is "nothing due", and it
        # should not cost a connection and a lock round trip every fifteen minutes.
        if not is_backup_due(db, settings, local_now(db)):
            return None

        with advisory_lock(db, BACKUP_CYCLE_LOCK_ID, "scheduled backup") as acquired:
            if not acquired:
                logger.info("Scheduled backup skipped: another worker is already running it")
                return None

            # Re-read inside the lock: the worker that held it may have just finished this
            # very slot, and running again would upload a duplicate copy.
            db.expire_all()
            settings = ensure_backup_settings(db)
            if not is_backup_due(db, settings, local_now(db)):
                return None

            run = run_backup(db, trigger=SCHEDULED)
            logger.info(
                "Scheduled backup finished with status %s (%s)", run.status, run.location or run.error
            )
            return run
    except Exception:
        # A scheduler thread that dies takes every future backup with it, and nothing would
        # say so — `run_backup` already records destination failures as runs, so reaching
        # here means something unexpected.
        db.rollback()
        logger.exception("The scheduled backup check failed")
        return None
    finally:
        if should_close_session:
            db.close()


class BackupScheduler:
    def __init__(self, interval_minutes: int) -> None:
        # A slot is only ever late by at most one interval, so this is the schedule's
        # precision. Fifteen minutes keeps "2am" honest without polling constantly.
        self.interval_seconds = max(60, interval_minutes * 60)
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="backup-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        # Checked once at startup too, so a server that was off through its slot takes the
        # missed copy as soon as it is back rather than waiting for the next interval.
        run_due_backup()

        while not self._stop_event.wait(timeout=self.interval_seconds):
            run_due_backup()
