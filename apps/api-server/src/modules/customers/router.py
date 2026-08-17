from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Customer, Loan, User
from src.modules.customers.schemas import CustomerCreate, CustomerRead, CustomerUpdate
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> list[Customer]:
    statement = select(Customer)
    if q:
        query = f"%{q}%"
        statement = statement.where(
            or_(
                Customer.first_name.ilike(query),
                Customer.last_name.ilike(query),
                Customer.document_number.ilike(query),
                Customer.city.ilike(query),
            )
        )
    return list(db.scalars(statement.order_by(Customer.id.desc())).all())


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Customer:
    duplicate = db.scalar(select(Customer).where(Customer.document_number == payload.document_number))
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")

    customer = Customer(**payload.model_dump())
    customer.created_by_id = current_user.id
    db.add(customer)
    db.commit()
    db.refresh(customer)

    write_audit(
        db,
        action="create_customer",
        entity_type="Customer",
        entity_id=str(customer.id),
        user=current_user,
        new_data=f"document={customer.document_number}",
    )

    return customer


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    update_data = payload.model_dump(exclude_none=True)

    next_document_number = update_data.get("document_number")
    if next_document_number and next_document_number != customer.document_number:
        duplicate = db.scalar(select(Customer).where(Customer.document_number == next_document_number))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Customer already exists")

    for field, value in update_data.items():
        setattr(customer, field, value)

    db.commit()
    db.refresh(customer)

    write_audit(
        db,
        action="update_customer",
        entity_type="Customer",
        entity_id=str(customer.id),
        user=current_user,
        new_data="profile updated",
    )

    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Response:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    has_related_loans = db.scalar(select(Loan.id).where(Loan.customer_id == customer_id).limit(1)) is not None
    has_related_applications = (
    )

    if has_related_loans or has_related_applications:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer has related credit records. Archive instead to preserve traceability.",
        )

    db.delete(customer)
    db.commit()

    write_audit(
        db,
        action="delete_customer",
        entity_type="Customer",
        entity_id=str(customer_id),
        user=current_user,
        new_data="customer deleted without credit traceability",
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
