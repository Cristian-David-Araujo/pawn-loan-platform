from calendar import monthrange
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import InterestCharge, Loan


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