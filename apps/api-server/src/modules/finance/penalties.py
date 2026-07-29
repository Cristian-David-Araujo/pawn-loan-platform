"""Fixing the late penalty of a billing period, once and for good.

The penalty used to be a formula evaluated on every read — `pending interest x rate` — so
the same debt reported a different figure depending on when you looked at it. Paying part
of the interest shrank it, raising `GlobalSettings.default_grace_days` erased it from the
entire portfolio backwards, and lowering a loan's `late_penalty_rate` rewrote penalties on
periods that had fallen due months earlier. None of it left a trace, and a statement
printed yesterday did not match the one printed today.

Here it becomes a stored fact: when a period passes its due date the penalty is computed
once, against the interest that period still owed and the rate the loan carried at that
moment, and written to the charge together with both. From then on it is history. Policy
changes reach the periods that fall due after them, never the ones already settled.
"""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan
from src.modules.finance.interest_balance import (
    charge_due_date,
    default_grace_days,
    grace_days_for_loan,
    pending_interest_by_charge_for_loans,
)

logger = logging.getLogger(__name__)


def freeze_due_penalties(db: Session, as_of_date: date) -> list[InterestCharge]:
    """Fix the penalty of every period that has fallen due without one recorded yet.

    The base is the interest the period still owes *now*, which is what the collection
    screens show. Running daily that is the balance it owed at its due date; if the cycle
    has been stopped for a while, payments made in between lower it — an error that can
    only favour the customer, and one that a stopped scheduler already implies.

    Returns the charges it stamped, so the caller can record how many in the audit trail.
    """
    # Sessions run with autoflush off, so charges the caller just generated would be
    # invisible to the query below and would go a whole cycle without their penalty.
    db.flush()

    unfrozen = list(
        db.scalars(
            select(InterestCharge)
            .where(InterestCharge.penalty_applied_at.is_(None))
            .order_by(InterestCharge.period_end.asc(), InterestCharge.id.asc())
        ).all()
    )
    if not unfrozen:
        return []

    loans = list(db.scalars(select(Loan).where(Loan.id.in_({charge.loan_id for charge in unfrozen}))).all())
    loans_by_id = {loan.id: loan for loan in loans}
    configured_grace_days = default_grace_days(db)
    pending_by_charge = pending_interest_by_charge_for_loans(db, loans)

    frozen: list[InterestCharge] = []
    for charge in unfrozen:
        loan = loans_by_id.get(charge.loan_id)
        if loan is None:
            continue

        # Foreclosing is the decision to collect through the pledge instead of through more
        # interest — which is why `ACCRUING_STATUSES` leaves `defaulted` out. A late penalty
        # is more interest by another name, so it stops at the same line. A `closed` loan
        # does keep accruing penalties: it can still owe (see `allow_with_unpaid_interest`),
        # and that debt is collected at the counter like any other.
        if loan.status == LoanStatus.defaulted:
            continue

        due_date = charge_due_date(charge.period_end, grace_days_for_loan(loan, configured_grace_days))
        if due_date >= as_of_date:
            continue

        rate = max(0.0, loan.late_penalty_rate)
        base = pending_by_charge.get(charge.id, 0.0)
        charge.penalty_amount = round(base * (rate / 100), 2)
        charge.penalty_rate_applied = rate
        # The day the period fell due, not the day the cycle got around to it: a scheduler
        # that runs late must not make the penalty look like it was applied late.
        charge.penalty_applied_at = due_date
        frozen.append(charge)

    return frozen


def describe_frozen_penalties(frozen: list[InterestCharge]) -> str:
    """Compact audit representation of a batch of penalty freezes."""
    total = round(sum(charge.penalty_amount or 0.0 for charge in frozen), 2)
    return f"charges={len(frozen)},total_penalty={total}"
