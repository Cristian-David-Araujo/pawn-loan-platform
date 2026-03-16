from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.loan import LoanApplicationStatus
from app.repositories.loan_repository import LoanApplicationRepository
from app.schemas.loan import ApplicationListResponse, LoanApplicationCreate, LoanApplicationRead, LoanApplicationUpdate
from app.services.loan_service import LoanService

router = APIRouter(prefix="/api/v1/loan-applications", tags=["loan-applications"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get("", response_model=ApplicationListResponse)
def list_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[UUID] = None,
    status: Optional[LoanApplicationStatus] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = LoanApplicationRepository(db)
    items, total = repo.get_all(skip=skip, limit=limit, customer_id=customer_id, status=status)
    return ApplicationListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("", response_model=LoanApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = LoanService(db)
    user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
    return service.create_application(payload, created_by=user_id)


@router.get("/{app_id}", response_model=LoanApplicationRead)
def get_application(app_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = LoanApplicationRepository(db)
    app = repo.get_by_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.post("/{app_id}/approve", response_model=LoanApplicationRead)
def approve_application(
    app_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = LoanService(db)
    user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
    try:
        result = service.approve_application(app_id, approved_by=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result


@router.post("/{app_id}/reject", response_model=LoanApplicationRead)
def reject_application(
    app_id: UUID,
    payload: LoanApplicationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = LoanService(db)
    user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
    try:
        result = service.reject_application(
            app_id,
            reason=payload.rejection_reason or "No reason provided",
            reviewed_by=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Application not found")
    return result
