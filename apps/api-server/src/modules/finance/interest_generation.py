from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, PaymentEvent

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


def generate_missing_interest_charges_for_loan(
    db: Session,
    loan: Loan,
    as_of_date: date,
    charge_date: date,
) -> list[InterestCharge]:
    existing_periods = {
        (charge.period_start, charge.period_end)
        for charge in db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan.id)).all()
    }

    generated: list[InterestCharge] = []
    for period_start, period_end in _iter_due_periods(as_of_date, loan.disbursement_date):
        if (period_start, period_end) in existing_periods:
            continue

        amount = round(loan.outstanding_principal * (loan.monthly_interest_rate / 100), 2)
        charge = InterestCharge(
            loan_id=loan.id,
            period_start=period_start,
            period_end=period_end,
            charge_date=charge_date,
            amount=amount,
            status="generated",
        )
        db.add(charge)
        generated.append(charge)

    return generated


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
    """
    due_periods = set(_iter_due_periods(as_of_date, loan.disbursement_date))
    existing_charges = list(db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan.id)).all())

    preserved_periods: set[tuple[date, date]] = set()
    for charge in existing_charges:
        linked_events = list(db.scalars(select(PaymentEvent).where(PaymentEvent.interest_charge_id == charge.id)).all())
        paid_interest = round(sum(item.allocated_to_interest for item in linked_events), 2)

        period_key = (charge.period_start, charge.period_end)
        if period_key in due_periods:
            already_billed = charge.period_end <= charge_date or bool(linked_events)
            if already_billed:
                preserved_periods.add(period_key)
                continue

            charge.amount = round(loan.outstanding_principal * (loan.monthly_interest_rate / 100), 2)
            charge.charge_date = charge_date
            charge.status = "generated"
            preserved_periods.add(period_key)
            continue

        if linked_events:
            # Keep historical links but prevent obsolete periods from appearing as pending debt.
            charge.amount = max(0.0, paid_interest)
            charge.status = "paid"
            charge.charge_date = charge_date
            continue

        db.delete(charge)

    generated: list[InterestCharge] = []

    for period_start, period_end in due_periods:
        if (period_start, period_end) in preserved_periods:
            continue

        amount = round(loan.outstanding_principal * (loan.monthly_interest_rate / 100), 2)
        charge = InterestCharge(
            loan_id=loan.id,
            period_start=period_start,
            period_end=period_end,
            charge_date=charge_date,
            amount=amount,
            status="generated",
        )
        db.add(charge)
        generated.append(charge)

    return generated