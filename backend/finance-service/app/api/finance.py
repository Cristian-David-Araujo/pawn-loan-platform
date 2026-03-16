from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.repositories.finance_repository import InterestRepository, PenaltyRepository
from app.schemas.finance import (
    InterestChargeRead,
    InterestGenerateRequest,
    LoanBalanceResponse,
    PenaltyChargeCreate,
    PenaltyChargeRead,
)
from app.services.finance_service import FinanceService

router = APIRouter(prefix="/api/v1", tags=["finance"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.post("/interest/generate", response_model=InterestChargeRead, status_code=status.HTTP_201_CREATED)
def generate_interest(
    payload: InterestGenerateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    service = FinanceService(db)
    try:
        return service.generate_interest(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/loans/{loan_id}/ledger", response_model=List[InterestChargeRead])
def get_ledger(loan_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = InterestRepository(db)
    return repo.get_by_loan(loan_id)


@router.get("/loans/{loan_id}/balance", response_model=LoanBalanceResponse)
def get_balance(
    loan_id: UUID,
    outstanding_principal: Decimal = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    service = FinanceService(db)
    return service.get_loan_balance(loan_id, outstanding_principal)


@router.post("/penalties", response_model=PenaltyChargeRead, status_code=status.HTTP_201_CREATED)
def create_penalty(
    payload: PenaltyChargeCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = PenaltyRepository(db)
    return repo.create(**payload.model_dump())


@router.get("/loans/{loan_id}/penalties", response_model=List[PenaltyChargeRead])
def get_penalties(loan_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = PenaltyRepository(db)
    return repo.get_by_loan(loan_id)
