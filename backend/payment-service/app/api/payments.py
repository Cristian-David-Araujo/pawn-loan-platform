from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentCreate, PaymentListResponse, PaymentRead, ReversalRequest

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get("", response_model=PaymentListResponse)
def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    loan_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = PaymentRepository(db)
    if loan_id:
        items = repo.get_by_loan_id(loan_id)
        return PaymentListResponse(items=items, total=len(items), skip=skip, limit=limit)
    items, total = repo.get_all(skip=skip, limit=limit)
    return PaymentListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    repo = PaymentRepository(db)
    data = payload.model_dump()
    if not data.get("received_by") and current_user.get("sub"):
        data["received_by"] = UUID(current_user["sub"])
    return repo.create(**data)


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = PaymentRepository(db)
    payment = repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: UUID,
    payload: ReversalRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    repo = PaymentRepository(db)
    payment = repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status.value == "reversed":
        raise HTTPException(status_code=400, detail="Payment already reversed")
    reversed_by = payload.reversed_by or (UUID(current_user["sub"]) if current_user.get("sub") else None)
    return repo.reverse(payment, reason=payload.reason, reversed_by=reversed_by)
