from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Customer, CustomerIdentityDocument, Loan, User
from src.modules.customers.schemas import (
    CustomerCreate,
    CustomerIdentityDocumentRead,
    CustomerRead,
    CustomerUpdate,
)
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit
from src.shared.utils.uploads import MAX_IDENTITY_DOCUMENT_BYTES, read_validated_upload

router = APIRouter(prefix="/customers", tags=["customers"])

IDENTITY_DOCUMENT_SIDES = {"front", "back", "combined"}


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


@router.get("/{customer_id}/identity-document", response_model=list[CustomerIdentityDocumentRead])
def get_identity_document(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> list[CustomerIdentityDocument]:
    if db.get(Customer, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return list(
        db.scalars(
            select(CustomerIdentityDocument)
            .where(CustomerIdentityDocument.customer_id == customer_id)
            .order_by(CustomerIdentityDocument.side.asc())
        ).all()
    )


@router.post(
    "/{customer_id}/identity-document",
    response_model=CustomerIdentityDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_identity_document(
    customer_id: int,
    file: UploadFile = File(...),
    side: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> CustomerIdentityDocument:
    if db.get(Customer, customer_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    if side not in IDENTITY_DOCUMENT_SIDES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identity document side")

    content, content_type, filename = read_validated_upload(
        file, max_bytes=MAX_IDENTITY_DOCUMENT_BYTES, allow_pdf=True
    )
    document = db.scalar(
        select(CustomerIdentityDocument).where(
            CustomerIdentityDocument.customer_id == customer_id,
            CustomerIdentityDocument.side == side,
        )
    )
    is_replacement = document is not None
    if document is None:
        document = CustomerIdentityDocument(customer_id=customer_id, side=side)
        db.add(document)

    document.filename = filename
    document.content_type = content_type
    document.size_bytes = len(content)
    document.content = content
    document.uploaded_by_id = current_user.id
    db.flush()
    write_audit(
        db,
        action="replace_customer_identity_document" if is_replacement else "upload_customer_identity_document",
        entity_type="CustomerIdentityDocument",
        entity_id=str(document.id),
        user=current_user,
        new_data=f"customer_id={customer_id},side={side},filename={filename},size_bytes={len(content)}",
    )
    db.refresh(document)
    return document


@router.get("/{customer_id}/identity-document/{side}/file")
def download_identity_document(
    customer_id: int,
    side: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> Response:
    document = db.scalar(
        select(CustomerIdentityDocument).where(
            CustomerIdentityDocument.customer_id == customer_id,
            CustomerIdentityDocument.side == side,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity document not found")
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{document.filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/{customer_id}/identity-document/{side}", status_code=status.HTTP_204_NO_CONTENT)
def delete_identity_document(
    customer_id: int,
    side: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Response:
    document = db.scalar(
        select(CustomerIdentityDocument).where(
            CustomerIdentityDocument.customer_id == customer_id,
            CustomerIdentityDocument.side == side,
        )
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity document not found")

    filename = document.filename
    db.delete(document)
    write_audit(
        db,
        action="delete_customer_identity_document",
        entity_type="CustomerIdentityDocument",
        entity_id=str(document.id),
        user=current_user,
        old_data=f"customer_id={customer_id},side={side},filename={filename}",
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
