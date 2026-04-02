from calendar import monthrange
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, Payment, User
from src.modules.finance.schemas import InterestChargeRead, InterestGenerationRequest, LoanBalanceRead
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["finance"])


def _month_anchor(year: int, month: int, due_day: int) -> date:
    last_day = monthrange(year, month)[1]
    day = min(max(1, due_day), last_day)
    return date(year, month, day)


def _add_months(base_date: date, months: int, due_day: int) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    return _month_anchor(year, month, due_day)


def _interest_period_for_as_of(as_of_date: date, due_day: int) -> tuple[date, date]:
    current_anchor = _month_anchor(as_of_date.year, as_of_date.month, due_day)
    if as_of_date >= current_anchor:
        period_end = current_anchor
    else:
        period_end = _add_months(current_anchor, -1, due_day)

    period_start = _add_months(period_end, -1, due_day)
    return period_start, period_end


@router.post("/interest/generate", response_model=list[InterestChargeRead])
def generate_interest(
    payload: InterestGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterestCharge]:
    loans = list(db.scalars(select(Loan).where(Loan.status == LoanStatus.active)).all())
    generated: list[InterestCharge] = []

    for loan in loans:
        period_start, period_end = _interest_period_for_as_of(payload.as_of_date, loan.due_day)

        exists = db.scalar(
            select(InterestCharge).where(
                InterestCharge.loan_id == loan.id,
                InterestCharge.period_start == period_start,
                InterestCharge.period_end == period_end,
            )
        )
        if exists is not None:
            continue

        amount = round(loan.outstanding_principal * (loan.monthly_interest_rate / 100), 2)
        charge = InterestCharge(
            loan_id=loan.id,
            period_start=period_start,
            period_end=period_end,
            charge_date=payload.as_of_date,
            amount=amount,
            status="generated",
        )
        db.add(charge)
        generated.append(charge)

    db.commit()

    for charge in generated:
        db.refresh(charge)

    write_audit(
        db,
        action="generate_interest",
        entity_type="InterestCharge",
        entity_id=f"count={len(generated)}",
        user=current_user,
        new_data=f"as_of_date={payload.as_of_date}",
    )

    return generated


@router.get("/loans/{loan_id}/balance", response_model=LoanBalanceRead)
def loan_balance(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> LoanBalanceRead:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    total_interest = sum(item.amount for item in db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)))
    total_payments = sum(item.total_amount for item in db.scalars(select(Payment).where(Payment.loan_id == loan_id)))

    return LoanBalanceRead(
        loan_id=loan.id,
        principal_amount=loan.principal_amount,
        outstanding_principal=loan.outstanding_principal,
        total_interest_generated=round(total_interest, 2),
        total_payments=round(total_payments, 2),
    )


@router.get("/loans/{loan_id}/ledger")
def loan_ledger(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    interest = list(db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)).all())
    payments = list(db.scalars(select(Payment).where(Payment.loan_id == loan_id)).all())

    return {
        "loan_id": loan_id,
        "interest_charges": [
            {
                "id": item.id,
                "charge_date": item.charge_date,
                "amount": item.amount,
                "status": item.status,
            }
            for item in interest
        ],
        "payments": [
            {
                "id": item.id,
                "payment_date": item.payment_date,
                "total_amount": item.total_amount,
                "is_reversed": item.is_reversed,
            }
            for item in payments
        ],
    }
