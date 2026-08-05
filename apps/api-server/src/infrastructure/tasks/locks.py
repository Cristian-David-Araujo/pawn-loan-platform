"""Cross-worker advisory locks for the background jobs.

Every uvicorn worker starts its own scheduler threads, so a job that must not run twice at
once needs a lock the whole process group can see. This is the one implementation; jobs
declare a lock id and wrap their body in it.
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@contextmanager
def advisory_lock(db: Session, lock_id: int, job_name: str) -> Iterator[bool]:
    """Hold a PostgreSQL advisory lock on a connection of its own, for the whole block.

    ``pg_try_advisory_lock`` is session level: it lives on the *connection*, not on the
    transaction. Taken on the caller's ``Session`` it does not survive the job correctly,
    because a Session hands its connection back to the pool on every commit — and these jobs
    commit while holding the lock. Any request served in between could check that connection
    out, leaving the job on a different one: ``pg_advisory_unlock`` then ran where the lock
    had never been taken, returned ``false`` (a value nobody looked at), and the lock stayed
    on a pooled connection forever. From the next cycle on, every worker read "another worker
    is already running it" and the job silently stopped until a restart.

    Taking a dedicated connection makes the unlock run where the lock is, by construction.
    Yields whether the lock was acquired; the caller decides what to do when it was not.
    """
    if db.get_bind().dialect.name != "postgresql":
        # SQLite has no advisory locks and serialises writes anyway — the same
        # short-circuit the money-path row locks take.
        yield True
        return

    connection = db.get_bind().connect()
    acquired = False
    try:
        acquired = bool(connection.scalar(text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}))
        yield acquired
    finally:
        try:
            if acquired:
                released = connection.scalar(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id}
                )
                if not released:
                    # Cannot happen while the lock is held on this very connection, but a
                    # lock that leaks stops the job from ever running again, so it must
                    # never fail silently.
                    logger.error("The %s lock was not held by its own connection", job_name)
        except Exception:
            logger.exception("Could not release the %s lock", job_name)
        finally:
            connection.close()
