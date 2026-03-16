from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.collateral import CollateralStatus
from app.repositories.collateral_repository import CollateralRepository
from app.schemas.collateral import (
    CollateralItemCreate,
    CollateralItemRead,
    CollateralItemUpdate,
    LiquidateRequest,
    ReleaseRequest,
)

router = APIRouter(prefix="/api/v1/collateral-items", tags=["collateral"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


@router.get("", response_model=dict)
def list_collateral(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    loan_id: Optional[UUID] = None,
    status: Optional[CollateralStatus] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = CollateralRepository(db)
    if loan_id:
        items = repo.get_by_loan_id(loan_id)
        return {"items": items, "total": len(items), "skip": skip, "limit": limit}
    items, total = repo.get_all(skip=skip, limit=limit, status=status)
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=CollateralItemRead, status_code=status.HTTP_201_CREATED)
def create_collateral_item(
    payload: CollateralItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = CollateralRepository(db)
    return repo.create(**payload.model_dump())


@router.get("/{item_id}", response_model=CollateralItemRead)
def get_collateral_item(item_id: UUID, db: Session = Depends(get_db), _=Depends(get_current_user)):
    repo = CollateralRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collateral item not found")
    return item


@router.put("/{item_id}", response_model=CollateralItemRead)
def update_collateral_item(
    item_id: UUID,
    payload: CollateralItemUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = CollateralRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collateral item not found")
    return repo.update(item, **payload.model_dump(exclude_none=True))


@router.post("/{item_id}/release", response_model=CollateralItemRead)
def release_collateral(
    item_id: UUID,
    payload: ReleaseRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = CollateralRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collateral item not found")
    if item.status == CollateralStatus.RELEASED:
        raise HTTPException(status_code=400, detail="Item already released")
    return repo.release(item, released_by=payload.released_by)


@router.post("/{item_id}/liquidate", response_model=CollateralItemRead)
def liquidate_collateral(
    item_id: UUID,
    payload: LiquidateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    repo = CollateralRepository(db)
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Collateral item not found")
    if item.status in (CollateralStatus.RELEASED, CollateralStatus.SOLD):
        raise HTTPException(status_code=400, detail="Item cannot be liquidated in current status")
    return repo.liquidate(item, sale_amount=payload.sale_amount, notes=payload.notes)
