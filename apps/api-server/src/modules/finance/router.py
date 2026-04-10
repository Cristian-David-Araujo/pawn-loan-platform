from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan, Payment, User
from src.modules.finance.interest_generation import generate_missing_interest_charges_for_loan
from src.modules.finance.schemas import InterestChargeRead, InterestGenerationRequest, LoanBalanceRead
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["finance"])


@router.post("/interest/generate", response_model=list[InterestChargeRead])
def generate_interest(
    payload: InterestGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterestCharge]:
    settings = db.get(GlobalSettings, 1)
    lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
    effective_as_of_date = payload.as_of_date + timedelta(days=lead_days)

    loans = list(db.scalars(select(Loan).where(Loan.status == LoanStatus.active)).all())
    generated: list[InterestCharge] = []

    for loan in loans:
        generated.extend(
            generate_missing_interest_charges_for_loan(
                db=db,
                loan=loan,
                as_of_date=effective_as_of_date,
                charge_date=payload.as_of_date,
            )
        )

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
