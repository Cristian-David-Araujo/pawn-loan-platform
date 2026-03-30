from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import Loan, Payment, User
from src.modules.payments.schemas import PaymentCreate, PaymentRead
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentRead])
def list_payments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Payment]:
    return list(db.query(Payment).order_by(Payment.id.desc()).all())


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    loan = db.get(Loan, payload.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    allocated_sum = (
        payload.allocated_to_penalty
        + payload.allocated_to_interest
        + payload.allocated_to_fees
        + payload.allocated_to_principal
    )
    if round(allocated_sum, 2) != round(payload.total_amount, 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation sum must match total amount")

    payment = Payment(**payload.model_dump(), received_by=current_user.id)
    db.add(payment)

    loan.outstanding_principal = max(0, loan.outstanding_principal - payload.allocated_to_principal)
    if loan.outstanding_principal == 0:
        loan.status = LoanStatus.closed

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="create_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        new_data=f"amount={payment.total_amount}",
    )

    return payment


@router.post("/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already reversed")

    loan = db.get(Loan, payment.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    payment.is_reversed = True
    loan.outstanding_principal += payment.allocated_to_principal
    if loan.status == LoanStatus.closed:
        loan.status = LoanStatus.active

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="reverse_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        new_data="is_reversed=true",
    )

    return payment
