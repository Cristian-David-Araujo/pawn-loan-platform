from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.loan import LoanStatus, LoanType
from app.repositories.loan_repository import LoanRepository
from app.schemas.loan import LoanCreate, LoanListResponse, LoanRead
from app.services.loan_service import LoanService

router = APIRouter(prefix="/api/v1/loans", tags=["loans"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get("", response_model=LoanListResponse)
def list_loans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[UUID] = None,
    status: Optional[LoanStatus] = None,
    loan_type: Optional[LoanType] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = LoanRepository(db)
    items, total = repo.get_all(skip=skip, limit=limit, customer_id=customer_id, status=status, loan_type=loan_type)
    return LoanListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan(
    payload: LoanCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    service = LoanService(db)
    try:
        return service.create_loan(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{loan_id}", response_model=LoanRead)
def get_loan(loan_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = LoanRepository(db)
    loan = repo.get_by_id(loan_id)
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    return loan


@router.post("/{loan_id}/renew", response_model=LoanRead)
def renew_loan(
    loan_id: UUID,
    term_months: int = Query(..., ge=1),
    new_rate: Optional[Decimal] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    service = LoanService(db)
    try:
        result = service.renew_loan(loan_id, term_months, new_rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Loan not found")
    return result


@router.post("/{loan_id}/close", response_model=LoanRead)
def close_loan(loan_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    service = LoanService(db)
    try:
        result = service.close_loan(loan_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Loan not found")
    return result
