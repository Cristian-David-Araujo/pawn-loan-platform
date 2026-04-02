from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, Loan, User
from src.modules.collateral.schemas import CollateralCreate, CollateralRead
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/collateral-items", tags=["collateral"])


def _next_custody_code(db: Session) -> str:
    count = db.query(CollateralItem).count() + 1
    return f"CUST-{count:05d}"


@router.post("", response_model=CollateralRead, status_code=status.HTTP_201_CREATED)
def create_collateral_item(
    payload: CollateralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollateralItem:
    loan = db.get(Loan, payload.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.loan_type != "pawn":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Collateral is only allowed for pawn loans")
    if loan.status == LoanStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot register collateral for closed loan")

    item = CollateralItem(
        **payload.model_dump(),
        custody_code=_next_custody_code(db),
        status="in_custody",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    write_audit(
        db,
        action="create_collateral_item",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data=f"loan_id={item.loan_id}",
    )

    return item


@router.get("/{item_id}", response_model=CollateralRead)
def get_collateral_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")
    return item


@router.get("", response_model=list[CollateralRead])
def list_collateral_items(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CollateralItem]:
    return list(db.query(CollateralItem).order_by(CollateralItem.id.desc()).all())


@router.post("/{item_id}/release", response_model=CollateralRead)
def release_collateral(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")

    loan = db.get(Loan, item.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")
    if loan.outstanding_principal > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan has outstanding balance")

    item.status = "released"
    db.commit()
    db.refresh(item)

    write_audit(
        db,
        action="release_collateral",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data="status=released",
    )

    return item


@router.post("/{item_id}/liquidate", response_model=CollateralRead)
def liquidate_collateral(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")

    item.status = "liquidated"
    db.commit()
    db.refresh(item)

    write_audit(
        db,
        action="liquidate_collateral",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data="status=liquidated",
    )

    return item
