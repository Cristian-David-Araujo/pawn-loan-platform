"""Canonical interest balance calculation.

Every read of "how much interest is still owed" must go through this module so the
loan listings, the collection screens and the overdue transition job cannot drift
apart. Balances are derived exclusively from non reversed ``PaymentEvent`` rows;
``InterestCharge.status`` is a denormalized cache, never the source of truth.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, PaymentEvent

ADVANCE_PAYMENT_TYPE = "interest_advance_payment"


@dataclass(frozen=True)
class PendingInterestItem:
    """Outstanding interest for a single billing period of a loan."""

    interest_charge_id: int
    loan_id: int
    loan_type: str
    disbursement_date: date
    billing_period: str
    period_start: date
    period_end: date
    due_date: date
    original_interest_amount: float
    pending_interest: float
    penalty_amount: float
    pending_penalty: float
    overdue: bool
    outstanding: float


@dataclass(frozen=True)
class LoanInterestBalance:
    """Aggregated pending interest for a loan, plus its unapplied advance balance."""

    loan: Loan
    items: list[PendingInterestItem]
    available_advance_balance: float

    @property
    def pending_interest(self) -> float:
        return round(sum(item.pending_interest for item in self.items), 2)

    @property
    def pending_penalty(self) -> float:
        return round(sum(item.pending_penalty for item in self.items), 2)

    @property
    def outstanding(self) -> float:
        return round(sum(item.outstanding for item in self.items), 2)

    @property
    def has_overdue_interest(self) -> bool:
        return any(item.overdue and item.outstanding > 0 for item in self.items)


def charge_due_date(period_end: date, grace_days: int) -> date:
    """Due date of a billing period.

    ``Loan.due_day`` is used as the grace period in days after ``period_end``.
    """
    return period_end + timedelta(days=max(0, grace_days))


def _sum_interest(events: list[PaymentEvent]) -> float:
    return round(sum(event.allocated_to_interest for event in events), 2)


def _sum_penalty(events: list[PaymentEvent]) -> float:
    return round(sum(event.allocated_to_penalty for event in events), 2)


def _active_events_for_loans(db: Session, loan_ids: list[int]) -> list[PaymentEvent]:
    if not loan_ids:
        return []

    return list(
        db.scalars(
            select(PaymentEvent).where(
                PaymentEvent.loan_id.in_(loan_ids),
                PaymentEvent.is_reversed.is_(False),
            )
        ).all()
    )


def _charges_for_loans(db: Session, loan_ids: list[int]) -> list[InterestCharge]:
    if not loan_ids:
        return []

    return list(
        db.scalars(
            select(InterestCharge)
            .where(InterestCharge.loan_id.in_(loan_ids))
            .order_by(InterestCharge.period_end.asc(), InterestCharge.id.asc())
        ).all()
    )


def _build_loan_balance(
    loan: Loan,
    charges: list[InterestCharge],
    events_by_charge: dict[int, list[PaymentEvent]],
    advance_events: list[PaymentEvent],
    as_of_date: date,
) -> LoanInterestBalance:
    advance_pool = _sum_interest(advance_events)
    items: list[PendingInterestItem] = []

    for charge in charges:
        charge_events = events_by_charge.get(charge.id, [])
        pending_interest = round(max(0.0, charge.amount - _sum_interest(charge_events)), 2)

        # Advances are consumed oldest period first, mirroring the allocation order.
        if advance_pool > 0 and pending_interest > 0:
            applied = round(min(advance_pool, pending_interest), 2)
            pending_interest = round(pending_interest - applied, 2)
            advance_pool = round(advance_pool - applied, 2)

        due_date = charge_due_date(charge.period_end, loan.due_day)
        overdue = due_date < as_of_date
        penalty_amount = (
            round(pending_interest * (loan.late_penalty_rate / 100), 2)
            if overdue and pending_interest > 0
            else 0.0
        )
        pending_penalty = round(max(0.0, penalty_amount - _sum_penalty(charge_events)), 2)
        outstanding = round(pending_interest + pending_penalty, 2)
        if outstanding <= 0:
            continue

        items.append(
            PendingInterestItem(
                interest_charge_id=charge.id,
                loan_id=charge.loan_id,
                loan_type=loan.loan_type.value,
                disbursement_date=loan.disbursement_date,
                billing_period=charge.period_start.strftime("%Y-%m"),
                period_start=charge.period_start,
                period_end=charge.period_end,
                due_date=due_date,
                original_interest_amount=round(charge.amount, 2),
                pending_interest=pending_interest,
                penalty_amount=penalty_amount,
                pending_penalty=pending_penalty,
                overdue=overdue,
                outstanding=outstanding,
            )
        )

    return LoanInterestBalance(loan=loan, items=items, available_advance_balance=advance_pool)


def pending_interest_for_loans(
    db: Session,
    loans: list[Loan],
    as_of_date: date,
) -> dict[int, LoanInterestBalance]:
    """Pending interest for several loans using a fixed number of queries."""
    loan_ids = [loan.id for loan in loans]
    charges = _charges_for_loans(db, loan_ids)
    events = _active_events_for_loans(db, loan_ids)

    charges_by_loan: dict[int, list[InterestCharge]] = {}
    for charge in charges:
        charges_by_loan.setdefault(charge.loan_id, []).append(charge)

    events_by_charge: dict[int, list[PaymentEvent]] = {}
    advances_by_loan: dict[int, list[PaymentEvent]] = {}
    for event in events:
        if event.interest_charge_id is None:
            if event.payment_type == ADVANCE_PAYMENT_TYPE:
                advances_by_loan.setdefault(event.loan_id, []).append(event)
            continue
        events_by_charge.setdefault(event.interest_charge_id, []).append(event)

    return {
        loan.id: _build_loan_balance(
            loan=loan,
            charges=charges_by_loan.get(loan.id, []),
            events_by_charge=events_by_charge,
            advance_events=advances_by_loan.get(loan.id, []),
            as_of_date=as_of_date,
        )
        for loan in loans
    }


def pending_interest_for_loan(db: Session, loan: Loan, as_of_date: date) -> LoanInterestBalance:
    return pending_interest_for_loans(db, [loan], as_of_date)[loan.id]


def pending_interest_for_customer(
    db: Session,
    customer_id: int,
    as_of_date: date,
) -> list[LoanInterestBalance]:
    """Pending interest for every non closed loan of a customer, oldest due first."""
    loans = list(
        db.scalars(
            select(Loan)
            .where(Loan.customer_id == customer_id, Loan.status != LoanStatus.closed)
            .order_by(Loan.id.asc())
        ).all()
    )
    balances = pending_interest_for_loans(db, loans, as_of_date)
    return [balances[loan.id] for loan in loans]


def pending_interest_items_for_customer(
    db: Session,
    customer_id: int,
    as_of_date: date,
) -> list[PendingInterestItem]:
    """Flattened pending periods of a customer in allocation order (oldest first)."""
    items = [item for balance in pending_interest_for_customer(db, customer_id, as_of_date) for item in balance.items]
    return sorted(items, key=lambda item: (item.due_date, item.loan_id, item.interest_charge_id))


def pending_interest_total_for_loan(db: Session, loan: Loan, as_of_date: date) -> float:
    """Interest still owed on a loan, excluding penalties."""
    return pending_interest_for_loan(db, loan, as_of_date).pending_interest


def sync_interest_charge_statuses(db: Session, loan_id: int) -> None:
    """Refresh the cached ``InterestCharge.status`` from the active ledger rows."""
    charges = _charges_for_loans(db, [loan_id])
    events = _active_events_for_loans(db, [loan_id])

    events_by_charge: dict[int, list[PaymentEvent]] = {}
    for event in events:
        if event.interest_charge_id is not None:
            events_by_charge.setdefault(event.interest_charge_id, []).append(event)

    for charge in charges:
        paid_interest = _sum_interest(events_by_charge.get(charge.id, []))
        if paid_interest <= 0:
            charge.status = "generated"
        elif paid_interest >= round(charge.amount, 2):
            charge.status = "paid"
        else:
            charge.status = "partially_paid"
