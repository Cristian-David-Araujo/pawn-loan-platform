from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, PaymentEvent

# One `Repayment` per principal allocation that is still standing, used to rebuild what a
# loan owed at the end of a period the cycle is only getting to now.
Repayment = tuple[date, float]

# Interest accrues while the debt is alive, and falling behind does not make it less alive.
# Generation used to run over `active` only, so the moment a loan turned `overdue` it stopped
# billing: a customer five months behind kept a debt frozen at the two months billed before
# the transition. The debt was not lost, only hidden — `_iter_due_periods` walks from the
# disbursement, so the day that loan returned to `active` the whole backlog landed at once,
# and until then the portfolio reports understated the arrears of the worst-off customers.
#
# `closed` and `defaulted` stay out: a settled loan has nothing to bill, and a foreclosure
# is the operator's decision to collect through the pledge instead of through more interest.
ACCRUING_STATUSES = (LoanStatus.active, LoanStatus.overdue)


def accruing_loans(db: Session) -> list[Loan]:
    """The loans a generation cycle looks at.

    One definition, called by both the scheduler and `POST /interest/generate`. They each
    spelled this query out, and the two drifting apart is precisely what produced the defect
    described above — so the query lives here beside the statuses it uses.

    **Paused loans are included.** They accrue nothing, but they still need a zero-amount
    marker written for each month that passes, or the gap would be filled with real charges
    the moment the pause ended. The pause is applied per loan, inside the generation loop.
    """
    return list(db.scalars(select(Loan).where(Loan.status.in_(ACCRUING_STATUSES))).all())


def _month_anchor(year: int, month: int, anchor_day: int) -> date:
    last_day = monthrange(year, month)[1]
    day = min(max(1, anchor_day), last_day)
    return date(year, month, day)


def _add_months(base_date: date, months: int, anchor_day: int) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    return _month_anchor(year, month, anchor_day)


def _iter_due_periods(as_of_date: date, disbursement_date: date) -> list[tuple[date, date]]:
    anchor_day = disbursement_date.day
    period_start = disbursement_date
    period_end = _add_months(disbursement_date, 1, anchor_day)

    periods: list[tuple[date, date]] = []
    while period_end <= as_of_date:
        periods.append((period_start, period_end))
        period_start = period_end
        period_end = _add_months(period_end, 1, anchor_day)

    return periods


def existing_periods_by_loan(db: Session, loan_ids: list[int]) -> dict[int, set[tuple[date, date]]]:
    """Billing periods already on record, for a whole batch of loans in one query."""
    periods: dict[int, set[tuple[date, date]]] = {loan_id: set() for loan_id in loan_ids}
    if not loan_ids:
        return periods

    rows = db.execute(
        select(InterestCharge.loan_id, InterestCharge.period_start, InterestCharge.period_end).where(
            InterestCharge.loan_id.in_(loan_ids)
        )
    ).all()
    for loan_id, period_start, period_end in rows:
        periods.setdefault(loan_id, set()).add((period_start, period_end))

    return periods


def repayments_by_loan(db: Session, loan_ids: list[int]) -> dict[int, list[Repayment]]:
    """Standing principal repayments per loan, in one query, newest first."""
    repayments: dict[int, list[Repayment]] = {loan_id: [] for loan_id in loan_ids}
    if not loan_ids:
        return repayments

    rows = db.execute(
        select(PaymentEvent.loan_id, PaymentEvent.payment_date, PaymentEvent.allocated_to_principal).where(
            PaymentEvent.loan_id.in_(loan_ids),
            PaymentEvent.is_reversed.is_(False),
            PaymentEvent.allocated_to_principal > 0,
        )
    ).all()
    for loan_id, payment_date, allocated in rows:
        repayments.setdefault(loan_id, []).append((payment_date, allocated))

    return repayments


def principal_base_for_period(loan: Loan, period_end: date, repayments: list[Repayment]) -> float:
    """What the loan owed at the end of a billing period.

    A charge used to be `outstanding_principal * rate` against the principal **as it stands
    when the cycle runs**, which is the same thing only while the cycle is on time. With the
    scheduler stopped for three months, a customer who paid 700.000 off a 1.000.000 loan in
    between had all three backlogged months billed on the remaining 300.000: the two months
    they actually owed the full principal for were quietly billed at a third of their value.

    Repayments recorded *after* the period ended are added back, so the period is billed on
    the balance it really carried. Money paid during the period lowers it, as it should.
    """
    repaid_after = round(sum(amount for paid_on, amount in repayments if paid_on > period_end), 2)
    return round(loan.outstanding_principal + repaid_after, 2)


def _new_charge(loan: Loan, period_start: date, period_end: date, charge_date: date, principal_base: float) -> InterestCharge:
    return InterestCharge(
        loan_id=loan.id,
        period_start=period_start,
        period_end=period_end,
        charge_date=charge_date,
        amount=round(principal_base * (loan.monthly_interest_rate / 100), 2),
        principal_base=principal_base,
        status="generated",
    )


def _paused_marker(loan: Loan, period_start: date, period_end: date, charge_date: date) -> InterestCharge:
    """A month that ran while the loan was paused, recorded as deliberately not billed.

    This is the same zero-amount `not_billed` row [migration 0010] used to close the holes an
    earlier defect left behind, and it is here for exactly the reason it existed there: this
    generator is self-healing. `_iter_due_periods` walks from the disbursement every cycle,
    so a month with no charge is a gap it will fill — and the day a loan resumed, every month
    of the pause would be billed at once, which is the opposite of what pausing was for.

    Writing the marker as the period passes, rather than reconstructing the gap on resume,
    means there is never an instant where the loan has a hole in its record. `_is_invoiced`
    already treats a zero-amount charge as immutable, and both the balance calculation and
    `sync_interest_charge_statuses` already skip it, so the marker reaches no screen and no
    printed statement.
    """
    return InterestCharge(
        loan_id=loan.id,
        period_start=period_start,
        period_end=period_end,
        charge_date=charge_date,
        amount=0.0,
        principal_base=loan.outstanding_principal,
        status="not_billed",
    )


def generate_missing_interest_charges(
    db: Session,
    loans: list[Loan],
    as_of_date: date,
    charge_date: date,
) -> list[InterestCharge]:
    """Generate the missing periods of many loans with a fixed number of queries.

    The per-loan version issued one lookup per loan and the cycle called it in a loop, so a
    portfolio of two thousand loans meant two thousand round trips before anything was
    billed — and every one of them inside the window where the cycle holds its lock.
    """
    if not loans:
        return []

    loan_ids = [loan.id for loan in loans]
    existing = existing_periods_by_loan(db, loan_ids)
    repayments = repayments_by_loan(db, loan_ids)

    generated: list[InterestCharge] = []
    for loan in loans:
        known = existing.get(loan.id, set())
        loan_repayments = repayments.get(loan.id, [])
        for period_start, period_end in _iter_due_periods(as_of_date, loan.disbursement_date):
            if (period_start, period_end) in known:
                continue

            if loan.interest_paused:
                # Still written, still zero. Skipping the row entirely would leave a gap the
                # next cycle fills in with a real charge.
                charge = _paused_marker(loan, period_start, period_end, charge_date)
            else:
                charge = _new_charge(
                    loan,
                    period_start,
                    period_end,
                    charge_date,
                    principal_base_for_period(loan, period_end, loan_repayments),
                )
            db.add(charge)
            generated.append(charge)

    return generated


def generate_missing_interest_charges_for_loan(
    db: Session,
    loan: Loan,
    as_of_date: date,
    charge_date: date,
) -> list[InterestCharge]:
    """Single loan entry point, for the paths that only ever touch one (loan creation)."""
    return generate_missing_interest_charges(db, [loan], as_of_date, charge_date)


def recalculate_interest_charges_for_loan(
    db: Session,
    loan: Loan,
    as_of_date: date,
    charge_date: date,
) -> list[InterestCharge]:
    """Refresh the charges of a loan after its principal or rate changed.

    A change of principal or rate only reaches **future** periods. A period that has
    already ended was invoiced at the amount it was invoiced at, and no edit of the loan
    can rewrite it: this used to overwrite every due period with the current numbers, so
    correcting a pledge description turned a charge of 50.000 the customer had already
    paid into one of 30.000 and left the ledger claiming money the invoice no longer
    accounted for.

    ``charge_date`` is today: it is what separates a period that has run its course from
    one still open (``interest_generation_lead_days`` means ``as_of_date`` reaches into
    the future, so it cannot be used for that).

    **An invoiced period is never deleted and never rewritten.** Moving a loan's
    disbursement date re-anchors every period, and this used to delete every old charge that
    had no payment against it — taking with it the late penalties already frozen on them
    (``penalty_amount``, the rate and the date it fell due, all reset to NULL) and the
    zero-amount markers that record a month which was deliberately never billed. A two-day
    correction to a date thereby rewrote penalties from months earlier against today's
    balance and today's rate, which is the exact thing `penalties.py` exists to prevent.
    Periods that are still in the future and untouched are the only ones that may move.
    """
    due_periods = set(_iter_due_periods(as_of_date, loan.disbursement_date))
    existing_charges = list(db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan.id)).all())
    loan_repayments = repayments_by_loan(db, [loan.id]).get(loan.id, [])

    # Spans of time that already carry an invoice. Nothing may be billed over them again,
    # whatever the new anchor day says.
    invoiced_spans: list[tuple[date, date]] = []
    preserved_periods: set[tuple[date, date]] = set()

    for charge in existing_charges:
        linked_events = list(db.scalars(select(PaymentEvent).where(PaymentEvent.interest_charge_id == charge.id)).all())
        period_key = (charge.period_start, charge.period_end)

        if _is_invoiced(charge, linked_events, charge_date):
            invoiced_spans.append(period_key)
            preserved_periods.add(period_key)
            continue

        if period_key in due_periods:
            base = principal_base_for_period(loan, charge.period_end, loan_repayments)
            charge.amount = round(base * (loan.monthly_interest_rate / 100), 2)
            charge.principal_base = base
            charge.charge_date = charge_date
            charge.status = "generated"
            preserved_periods.add(period_key)
            continue

        # Still in the future, never billed, nothing recorded against it: safe to drop.
        db.delete(charge)

    generated: list[InterestCharge] = []

    for period_start, period_end in sorted(due_periods):
        if (period_start, period_end) in preserved_periods:
            continue
        if any(period_start < end and start < period_end for start, end in invoiced_spans):
            # The new anchor would bill a stretch of time an existing invoice already covers.
            continue

        base = principal_base_for_period(loan, period_end, loan_repayments)
        charge = _new_charge(loan, period_start, period_end, charge_date, base)
        db.add(charge)
        generated.append(charge)

    return generated


def _is_invoiced(charge: InterestCharge, linked_events: list[PaymentEvent], charge_date: date) -> bool:
    """Whether this period is already a fact rather than a forecast.

    Any of: money was allocated to it, its period has run out, its late penalty was frozen,
    it is a zero-amount marker for a month that was deliberately never billed, or it was
    voided. A voided charge is the most immutable of all — deleting it would free its
    `(period_start, period_end)` slot, and the next cycle would bill the very month an
    administrator just decided should never have been charged.
    """
    return (
        bool(linked_events)
        or charge.period_end <= charge_date
        or charge.penalty_applied_at is not None
        or charge.amount <= 0
        or charge.voided_at is not None
    )