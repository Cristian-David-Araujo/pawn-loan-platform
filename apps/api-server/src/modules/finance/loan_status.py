"""Automatic loan status transitions driven by the interest ledger."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import Loan
from src.modules.finance.interest_balance import pending_interest_for_loans

# Only these statuses are managed automatically; closed and defaulted loans are
# terminal states owned by explicit operator actions.
MANAGED_STATUSES = (LoanStatus.active, LoanStatus.overdue)


@dataclass(frozen=True)
class LoanStatusTransition:
    loan_id: int
    previous_status: LoanStatus
    new_status: LoanStatus


def refresh_overdue_loan_statuses(db: Session, as_of_date: date) -> list[LoanStatusTransition]:
    """Move loans between ``active`` and ``overdue`` based on past due interest.

    A loan is overdue when at least one billing period is past its due date (period
    end plus the configured grace days) and still has an outstanding balance. When
    the past due balance is settled the loan returns to ``active``.
    """
    loans = list(db.scalars(select(Loan).where(Loan.status.in_(MANAGED_STATUSES))).all())
    if not loans:
        return []

    balances = pending_interest_for_loans(db, loans, as_of_date)
    transitions: list[LoanStatusTransition] = []

    for loan in loans:
        balance = balances[loan.id]
        should_be_overdue = balance.has_overdue_interest

        if should_be_overdue and loan.status == LoanStatus.active:
            new_status = LoanStatus.overdue
        elif not should_be_overdue and loan.status == LoanStatus.overdue:
            new_status = LoanStatus.active
        else:
            continue

        transitions.append(
            LoanStatusTransition(
                loan_id=loan.id,
                previous_status=loan.status,
                new_status=new_status,
            )
        )
        loan.status = new_status

    return transitions


def describe_transitions(transitions: list[LoanStatusTransition]) -> str:
    """Compact audit representation of a batch of transitions."""
    to_overdue = [item.loan_id for item in transitions if item.new_status == LoanStatus.overdue]
    to_active = [item.loan_id for item in transitions if item.new_status == LoanStatus.active]
    return f"to_overdue={to_overdue},to_active={to_active}"
