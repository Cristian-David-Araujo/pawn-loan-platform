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
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan, PaymentEvent

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
    """Due date of a billing period: the period end plus the grace days."""
    return period_end + timedelta(days=max(0, grace_days))


def default_grace_days(db: Session) -> int:
    """The configured grace period, shared by the whole portfolio.

    Grace used to come from ``Loan.due_day``, which the create form filled with the
    day-of-month of the disbursement — so a loan signed on the 25th silently got 25 days of
    grace and one signed on the 3rd got three. It is a policy, not a property of the loan.
    """
    settings = db.get(GlobalSettings, 1)
    return max(0, settings.default_grace_days) if settings is not None else 0


def grace_days_for_loan(loan: Loan, configured_grace_days: int) -> int:
    """Grace only exists to postpone the penalty, so a loan that charges none gets none.

    Otherwise a penalty-free loan would sit as "upcoming" for the whole grace window while
    its interest was already due, hiding the debt from the collection screens.
    """
    if loan.late_penalty_rate <= 0:
        return 0
    return max(0, configured_grace_days)


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
    """Charges that still count, which is every one that has not been voided.

    The filter belongs here and nowhere else. This is the single query every balance in the
    product is built from — the collection screens, `Loan.interest_due`, the penalty base,
    the overdue transition job and the cached charge status all come through it — so a voided
    period disappears from all of them at once. Filtering at each call site instead is how the
    same charge would start reading as owed on one screen and settled on another.

    Voiding is refused while a charge carries live payment events, so nothing that is excluded
    here can have money pointing at it.
    """
    if not loan_ids:
        return []

    return list(
        db.scalars(
            select(InterestCharge)
            .where(
                InterestCharge.loan_id.in_(loan_ids),
                InterestCharge.voided_at.is_(None),
            )
            .order_by(InterestCharge.period_end.asc(), InterestCharge.id.asc())
        ).all()
    )


@dataclass(frozen=True)
class _NettedBook:
    """A customer's charges with their advance pool already applied."""

    loans_by_id: dict[int, Loan]
    charges_by_loan: dict[int, list[InterestCharge]]
    events_by_charge: dict[int, list[PaymentEvent]]
    pending_by_charge: dict[int, float]
    advance_left_by_loan: dict[int, float]


def _split_events(
    events: list[PaymentEvent],
) -> tuple[dict[int, list[PaymentEvent]], dict[int, float]]:
    events_by_charge: dict[int, list[PaymentEvent]] = {}
    advances_by_loan: dict[int, float] = {}

    for event in events:
        if event.interest_charge_id is None:
            if event.payment_type == ADVANCE_PAYMENT_TYPE:
                advances_by_loan[event.loan_id] = round(
                    advances_by_loan.get(event.loan_id, 0.0) + event.allocated_to_interest, 2
                )
            continue
        events_by_charge.setdefault(event.interest_charge_id, []).append(event)

    return events_by_charge, advances_by_loan


def _customers_hold_advances(db: Session, loans: list[Loan]) -> bool:
    """Whether any customer behind these loans has unapplied advance money anywhere.

    One indexed lookup, so the answer is cheap enough to ask on every balance read.
    """
    customer_ids = {loan.customer_id for loan in loans}
    if not customer_ids:
        return False

    return db.scalar(
        select(PaymentEvent.id)
        .join(Loan, Loan.id == PaymentEvent.loan_id)
        .where(
            Loan.customer_id.in_(customer_ids),
            PaymentEvent.payment_type == ADVANCE_PAYMENT_TYPE,
            PaymentEvent.is_reversed.is_(False),
        )
        .limit(1)
    ) is not None


def _net_customer_book(db: Session, loans: list[Loan], configured_grace_days: int) -> _NettedBook:
    """Work out what each period still owes once the customer's advances are applied.

    **An advance belongs to the customer, not to the loan it was filed against.** It is
    recorded against one loan only because a ledger row needs a loan, and the netting used to
    happen inside that loan: a customer with loans #7 and #12 who paid 200.000 ahead had it
    all parked on #7, so when #12 was billed 50.000 a month later it found no advance of its
    own, went overdue and started accruing a penalty while the customer's own money sat
    unused next door — the statement showing "200.000 in credit" and "50.000 overdue" at once.

    So the pool is pooled across every loan of **one** customer, and consumed in the same
    order money is applied at the counter: oldest due date first, across their loans. It is
    never pooled further than that: the batch handed in here routinely spans the whole
    portfolio (the penalty freeze, the overdue transition job and the arrears report all
    call this with every loan they are looking at), and a single global pool meant one
    customer's credit silently settled another customer's period — erasing the second
    customer's late penalty for good, keeping their loan out of `overdue`, and dropping
    them from the arrears report, while their own screen still showed the debt.
    """
    loans_by_id = {loan.id: loan for loan in loans}

    # Expanding to the whole book costs three more queries, and `Loan.interest_due` evaluates
    # this once per row of a listing. With no advance to share there is nothing to net across
    # loans and per-loan arithmetic gives the identical answer, so the expansion is bought
    # only when a pool actually exists — which is rare, since an advance is only created when
    # a customer pays interest with no period pending.
    if _customers_hold_advances(db, loans):
        customer_ids = {loan.customer_id for loan in loans}
        for loan in db.scalars(select(Loan).where(Loan.customer_id.in_(customer_ids))).all():
            # A caller can hand us a loan in a different session state; keep theirs authoritative.
            loans_by_id.setdefault(loan.id, loan)

    charges = _charges_for_loans(db, list(loans_by_id))
    events_by_charge, advances_by_loan = _split_events(_active_events_for_loans(db, list(loans_by_id)))

    pending_by_charge = {
        charge.id: round(max(0.0, charge.amount - _sum_interest(events_by_charge.get(charge.id, []))), 2)
        for charge in charges
    }

    def _due(charge: InterestCharge) -> date:
        loan = loans_by_id[charge.loan_id]
        return charge_due_date(charge.period_end, grace_days_for_loan(loan, configured_grace_days))

    loan_ids_by_customer: dict[int, set[int]] = {}
    for loan in loans_by_id.values():
        loan_ids_by_customer.setdefault(loan.customer_id, set()).add(loan.id)

    advance_left_by_loan: dict[int, float] = {}
    for customer_loan_ids in loan_ids_by_customer.values():
        pool = round(sum(advances_by_loan.get(loan_id, 0.0) for loan_id in customer_loan_ids), 2)
        if pool > 0:
            customer_charges = [charge for charge in charges if charge.loan_id in customer_loan_ids]
            for charge in sorted(customer_charges, key=lambda item: (_due(item), item.loan_id, item.id)):
                if pool <= 0:
                    break
                owed = pending_by_charge[charge.id]
                if owed <= 0:
                    continue
                applied = round(min(pool, owed), 2)
                pending_by_charge[charge.id] = round(owed - applied, 2)
                pool = round(pool - applied, 2)

        # Hand the unused remainder back to the loans that hold the advance rows, so summing
        # it across a customer's loans still equals their one credit balance.
        remaining = pool
        for loan_id in sorted(loan_id for loan_id in customer_loan_ids if loan_id in advances_by_loan):
            share = round(min(advances_by_loan[loan_id], remaining), 2)
            advance_left_by_loan[loan_id] = share
            remaining = round(remaining - share, 2)

    charges_by_loan: dict[int, list[InterestCharge]] = {}
    for charge in charges:
        charges_by_loan.setdefault(charge.loan_id, []).append(charge)

    return _NettedBook(
        loans_by_id=loans_by_id,
        charges_by_loan=charges_by_loan,
        events_by_charge=events_by_charge,
        pending_by_charge=pending_by_charge,
        advance_left_by_loan=advance_left_by_loan,
    )


def _build_loan_balance(
    loan: Loan,
    charges: list[InterestCharge],
    events_by_charge: dict[int, list[PaymentEvent]],
    pending_by_charge: dict[int, float],
    advance_pool: float,
    as_of_date: date,
    configured_grace_days: int,
) -> LoanInterestBalance:
    items: list[PendingInterestItem] = []

    for charge in charges:
        charge_events = events_by_charge.get(charge.id, [])
        pending_interest = pending_by_charge[charge.id]

        due_date = charge_due_date(charge.period_end, grace_days_for_loan(loan, configured_grace_days))
        overdue = due_date < as_of_date
        # Read, never recompute: the penalty was fixed by `freeze_due_penalties` on the day
        # this period fell due, against the balance it owed then and the rate in force then.
        # A period past its due date with nothing recorded yet is one the cycle has not
        # reached; it shows no penalty rather than an amount that would move on the next read.
        penalty_amount = round(charge.penalty_amount, 2) if charge.penalty_amount is not None else 0.0
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
    """Pending interest for several loans using a fixed number of queries.

    The netting spans the whole book of the customers involved, so asking about one loan and
    asking about all of them can never report that loan differently.
    """
    if not loans:
        return {}

    configured_grace_days = default_grace_days(db)
    book = _net_customer_book(db, loans, configured_grace_days)

    return {
        loan.id: _build_loan_balance(
            loan=book.loans_by_id.get(loan.id, loan),
            charges=book.charges_by_loan.get(loan.id, []),
            events_by_charge=book.events_by_charge,
            pending_by_charge=book.pending_by_charge,
            advance_pool=book.advance_left_by_loan.get(loan.id, 0.0),
            as_of_date=as_of_date,
            configured_grace_days=configured_grace_days,
        )
        for loan in loans
    }


def pending_interest_by_charge_for_loans(db: Session, loans: list[Loan]) -> dict[int, float]:
    """Interest still owed by every charge of these loans, keyed by charge id.

    Same derivation as the balances above — it is what the penalty freeze uses as its base,
    so a frozen penalty and the screen it came from can never disagree.
    """
    if not loans:
        return {}

    book = _net_customer_book(db, loans, default_grace_days(db))
    return {
        charge.id: book.pending_by_charge[charge.id]
        for loan in loans
        for charge in book.charges_by_loan.get(loan.id, [])
    }


def pending_interest_for_loan(db: Session, loan: Loan, as_of_date: date) -> LoanInterestBalance:
    return pending_interest_for_loans(db, [loan], as_of_date)[loan.id]


def pending_interest_for_customer(
    db: Session,
    customer_id: int,
    as_of_date: date,
) -> list[LoanInterestBalance]:
    """Pending interest per loan of a customer, oldest due first.

    A closed loan is included when it *still owes interest*. `pay_principal` closes a loan
    the moment its principal hits zero, so paying principal with `allow_with_unpaid_interest`
    leaves a closed loan with live interest charges. Filtering every closed loan out here
    made that debt vanish from the collection screens, from the printed balances and from
    the interest allocation itself — the money was neither collectable nor visible.

    Loans that are closed *and* settled stay out, which is what keeps history from piling
    up in the collection views.
    """
    loans = list(
        db.scalars(select(Loan).where(Loan.customer_id == customer_id).order_by(Loan.id.asc())).all()
    )
    balances = pending_interest_for_loans(db, loans, as_of_date)
    return [
        balances[loan.id]
        for loan in loans
        if loan.status != LoanStatus.closed or balances[loan.id].outstanding > 0
    ]


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
    """Refresh the cached ``InterestCharge.status`` from what the period actually still owes.

    Derived from the netted balance rather than from the charge's own ledger rows, so a
    period covered by the customer's advance reads as ``paid`` instead of sitting at
    ``generated`` while every balance in the system agreed it owed nothing.
    """
    loan = db.get(Loan, loan_id)
    if loan is None:
        return

    book = _net_customer_book(db, [loan], default_grace_days(db))

    for charge in book.charges_by_loan.get(loan_id, []):
        # A zero charge is a period that was never billed, marked as such so the generator
        # does not decide to bill it years later. There is nothing to keep in sync, and
        # overwriting its status would erase the only record of why the month is missing.
        if charge.amount <= 0:
            continue

        pending = book.pending_by_charge.get(charge.id, 0.0)
        if pending <= 0:
            charge.status = "paid"
        elif pending >= round(charge.amount, 2):
            charge.status = "generated"
        else:
            charge.status = "partially_paid"
