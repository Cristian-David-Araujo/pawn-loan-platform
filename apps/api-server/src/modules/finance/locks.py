"""Holding a loan still while money is being applied to it.

Every write path that reads a balance, decides an amount from it and then writes has a
window between the read and the write. Two cashiers taking 100.000 each against a 100.000
principal both read the same figure, both passed the capacity check, and ``max(0, ...)``
quietly absorbed the negative: two payments recorded, the loan closed, and 100.000 of
overpayment accounted for nowhere. Taking the row lock first makes the second request wait
and then fail its own check against the refreshed figure.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Loan


def lock_loans(db: Session, loans: list[Loan]) -> None:
    """Lock these loans for the rest of the transaction and refresh them.

    Rows are locked in id order so two requests touching the same pair of loans queue up
    instead of deadlocking on each other. SQLite has no row locking and serialises writes
    anyway, so it short-circuits — the same thing the interest cycle's advisory lock does.
    """
    if not loans or db.get_bind().dialect.name != "postgresql":
        return

    loan_ids = sorted({loan.id for loan in loans})
    db.execute(select(Loan.id).where(Loan.id.in_(loan_ids)).order_by(Loan.id).with_for_update())
    for loan in loans:
        db.refresh(loan)


def lock_customer_loans(db: Session, customer_id: int) -> None:
    """Lock a customer's whole book, for the paths that decide amounts across all of it.

    Interest allocation and the advance pool both span every loan a customer holds, so the
    set that has to hold still is the book, not one row of it.
    """
    loans = list(db.scalars(select(Loan).where(Loan.customer_id == customer_id)).all())
    lock_loans(db, loans)
