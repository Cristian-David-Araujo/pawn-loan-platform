from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, Loan, Payment, PaymentEvent, User
from src.infrastructure.utils.datetime_utils import get_local_date, get_local_datetime
from src.modules.collateral.schemas import CollateralCreate, CollateralRead, CollateralUpdate, CollateralSell
from src.modules.finance.allocation import AllocationTarget, allocate_oldest_first
from src.modules.finance.locks import lock_loans
from src.modules.finance.interest_balance import (
    pending_interest_for_loan,
    pending_interest_total_for_loan,
    sync_interest_charge_statuses,
)
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import get_current_user, require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/collateral-items", tags=["collateral"])


def _custody_code_for(item_id: int) -> str:
    """The vault label of a pledge, derived from its own row id.

    It used to be ``count() + 1``, which breaks the moment a pledge is deleted — and deleting
    a loan cascades to its pledges. With the counter behind, the next code either lands on one
    that still exists, and the unique index turns every further registration into a 500, or it
    lands on a gap and **reuses a label already printed on a customer's document**. Row ids are
    never reused, so neither can happen.
    """
    return f"CUST-{item_id:05d}"


@router.post("", response_model=CollateralRead, status_code=status.HTTP_201_CREATED)
def create_collateral_item(
    payload: CollateralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
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
        # A placeholder only until the row has an id: the column is unique and not nullable,
        # and the code is derived from that id so it can never collide with a retired one.
        custody_code=f"pending-{uuid4().hex}",
        status="in_custody",
    )
    db.add(item)
    db.flush()
    item.custody_code = _custody_code_for(item.id)
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
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
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


def _assert_loan_fully_settled(db: Session, loan: Loan) -> None:
    """Custody only goes back once the loan owes nothing at all.

    Principal alone is not enough: a loan closed with `force` can sit at zero principal
    while interest and penalties are still pending, and handing the pledge back then gives
    away the only leverage to collect the rest.
    """
    if loan.outstanding_principal > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan has outstanding balance")

    pending = pending_interest_total_for_loan(db, loan, get_local_date(db))
    if pending > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Loan has unpaid accrued interest",
        )


def _release_item(db: Session, item: CollateralItem, current_user: User) -> None:
    item.status = "released"
    write_audit(
        db,
        action="release_collateral",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data="status=released",
    )


@router.post("/{item_id}/release", response_model=CollateralRead)
def release_collateral(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)
    ),
) -> CollateralItem:
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")

    loan = db.get(Loan, item.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    _assert_loan_fully_settled(db, loan)

    _release_item(db, item, current_user)
    db.commit()
    db.refresh(item)
    return item


@router.post("/loans/{loan_id}/release", response_model=list[CollateralRead])
def release_collateral_for_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)
    ),
) -> list[CollateralItem]:
    """Hand back every item still in custody for a settled loan, in one transaction.

    A pawn loan usually holds several pledges and they are returned together, so releasing
    them one request at a time could leave the custody record half-updated if one failed.
    Already-released items are skipped rather than treated as an error, which keeps the
    call safe to retry.
    """
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    _assert_loan_fully_settled(db, loan)

    items = list(
        db.scalars(
            select(CollateralItem).where(
                CollateralItem.loan_id == loan_id,
                CollateralItem.status == "in_custody",
            )
        ).all()
    )
    for item in items:
        _release_item(db, item, current_user)

    db.commit()
    for item in items:
        db.refresh(item)

    return items


@router.post("/{item_id}/liquidate", response_model=CollateralRead)
def liquidate_collateral(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> CollateralItem:
    """Write a pledge off as unsellable. Only ever a pledge foreclosure already released.

    This used to flip the status with no check at all, so a pledge held for a loan the
    customer was paying on time could be written off — the goods are the customer's until a
    foreclosure says otherwise, and `for_sale` is the only state that says so.
    """
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")
    if item.status != "for_sale":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only a foreclosed item can be liquidated",
        )

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
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> CollateralItem:
    """Apply the proceeds of a foreclosure sale to everything the loan owes.

    The money lands the same way it would at the counter — penalty, then interest, oldest
    period first, then principal — through the shared allocator, so a sale and a payment can
    never credit the same debt differently. It used to send the whole price straight to
    principal: the loan was closed while its accrued interest stayed live, and the surplus
    was recorded in ``total_amount`` without being assigned to anything, leaving a payment
    whose buckets did not add up to itself.

    Anything left after the debt is settled belongs to the house, and is recorded as such.
    """
    item = db.get(CollateralItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collateral item not found")
    if item.status != "for_sale":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is not for sale")

    loan = db.get(Loan, item.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    lock_loans(db, [loan])

    today = get_local_date(db)
    balance = pending_interest_for_loan(db, loan, today)
    targets = [
        AllocationTarget(
            interest_charge_id=pending.interest_charge_id,
            loan_id=pending.loan_id,
            billing_period=pending.billing_period,
            outstanding=pending.outstanding,
            pending_penalty=pending.pending_penalty,
            overdue=pending.overdue,
            due_date=pending.due_date,
        )
        for pending in balance.items
    ]
    interest_slices, after_interest = allocate_oldest_first(targets, payload.sale_price)

    allocated_principal = round(min(after_interest, loan.outstanding_principal), 2)
    # Whatever the pledge fetched above the debt is the house's, recorded here rather than
    # left implicit: a payment that does not account for the money it received cannot be
    # reconciled against the till.
    house_surplus = round(max(0.0, after_interest - allocated_principal), 2)
    notes = f"Collateral sold: {payload.notes}" if payload.notes else "Collateral sold"

    payment = Payment(
        loan_id=loan.id,
        payment_date=today,
        total_amount=round(payload.sale_price, 2),
        allocated_to_penalty=round(sum(item_slice.allocated_penalty for item_slice in interest_slices), 2),
        allocated_to_interest=round(sum(item_slice.allocated_interest for item_slice in interest_slices), 2),
        allocated_to_fees=house_surplus,
        allocated_to_principal=allocated_principal,
        payment_method="collateral_sale",
        notes=notes,
        received_by=current_user.id,
    )
    db.add(payment)
    db.flush()

    for item_slice in interest_slices:
        db.add(
            PaymentEvent(
                payment_type="collateral_sale",
                payment_id=payment.id,
                loan_id=loan.id,
                interest_charge_id=item_slice.target.interest_charge_id,
                billing_period=item_slice.target.billing_period,
                total_entered_amount=item_slice.allocated_total,
                allocated_to_interest=item_slice.allocated_interest,
                allocated_to_penalty=item_slice.allocated_penalty,
                allocated_to_principal=0,
                payment_date=today,
                operator_user_id=current_user.id,
                payment_method="collateral_sale",
                notes=notes,
            )
        )

    if allocated_principal > 0 or not interest_slices:
        db.add(
            PaymentEvent(
                payment_type="collateral_sale",
                payment_id=payment.id,
                loan_id=loan.id,
                billing_period=today.strftime("%Y-%m"),
                total_entered_amount=round(allocated_principal + house_surplus, 2),
                allocated_to_principal=allocated_principal,
                payment_date=today,
                operator_user_id=current_user.id,
                payment_method="collateral_sale",
                notes=notes,
            )
        )

    loan.outstanding_principal = round(max(0.0, loan.outstanding_principal - allocated_principal), 2)
    if loan.outstanding_principal <= 0:
        loan.status = LoanStatus.closed

    item.status = "sold"
    item.sale_price = round(payload.sale_price, 2)
    item.sold_at = get_local_datetime(db)

    db.flush()
    sync_interest_charge_statuses(db, loan.id)
    db.commit()
    db.refresh(item)

    write_audit(
        db,
        action="sell_collateral",
        entity_type="CollateralItem",
        entity_id=str(item.id),
        user=current_user,
        new_data=(
            f"status=sold,price={item.sale_price},penalty={payment.allocated_to_penalty},"
            f"interest={payment.allocated_to_interest},principal={allocated_principal},"
            f"house_surplus={house_surplus},loan_status={loan.status.value}"
        ),
    )

    return item
