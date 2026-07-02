from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, Loan, User
from src.modules.collateral.schemas import CollateralCreate, CollateralRead, CollateralUpdate, CollateralSell
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import get_current_user, require_roles
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
    status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CollateralItem]:
    query = db.query(CollateralItem)
    if status:
        query = query.filter(CollateralItem.status == status)
    return list(query.order_by(CollateralItem.id.desc()).all())


@router.put("/{item_id}", response_model=CollateralRead)
def update_collateral_item(
    item_id: int,
    payload: CollateralUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")

    loan = db.get(Loan, payload.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.loan_type != "pawn":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Collateral is only allowed for pawn loans")
    if loan.status == LoanStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot register collateral for closed loan")

    item.loan_id = payload.loan_id
    item.description = payload.description
    item.appraised_value = payload.appraised_value
    item.storage_location = payload.storage_location
    item.status = payload.status
    db.commit()
    db.refresh(item)

    write_audit(
        db,
        action="update_collateral_item",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data=f"loan_id={item.loan_id},status={item.status}",
    )

    return item


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

@router.post("/{item_id}/sell", response_model=CollateralRead)
def sell_collateral(
    item_id: int,
    payload: CollateralSell,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")
    if item.status != "for_sale":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not for sale")

    loan = db.get(Loan, item.loan_id)
    
    # Register the payment
    from src.infrastructure.persistence.models import Payment, PaymentEvent, now_utc
    
    sale_date = now_utc()
    allocated_principal = min(payload.sale_price, loan.outstanding_principal)
    
    payment = Payment(
        loan_id=loan.id,
        payment_date=sale_date.date(),
        total_amount=payload.sale_price,
        allocated_to_principal=allocated_principal,
        payment_method="collateral_sale",
        notes=f"Collateral sold: {payload.notes}" if payload.notes else "Collateral sold",
        received_by=current_user.id
    )
    db.add(payment)
    db.flush()
    
    payment_event = PaymentEvent(
        payment_type="collateral_sale",
        payment_id=payment.id,
        loan_id=loan.id,
        total_entered_amount=payload.sale_price,
        allocated_to_principal=allocated_principal,
        payment_date=payment.payment_date,
        operator_user_id=current_user.id,
        payment_method="collateral_sale",
        notes=f"Collateral sold: {payload.notes}" if payload.notes else "Collateral sold"
    )
    db.add(payment_event)
    
    # Update loan principal and status
    loan.outstanding_principal = max(0, loan.outstanding_principal - allocated_principal)
    if loan.outstanding_principal <= 0:
        loan.status = LoanStatus.closed
    
    # Update item status and sale fields
    item.status = "sold"
    item.sale_price = payload.sale_price
    item.sold_at = sale_date
    
    db.commit()
    db.refresh(item)
    
    write_audit(
        db,
        action="sell_collateral",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data=f"status=sold,price={payload.sale_price}",
    )
    
    return item
