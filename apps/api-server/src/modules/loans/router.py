from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, GlobalSettings, InterestCharge, Loan, LoanApplication, Payment, PaymentEvent, User
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_generation import generate_missing_interest_charges_for_loan, recalculate_interest_charges_for_loan
from src.modules.loans.schemas import (
    CloseLoanRequest,
    LoanApplicationCreate,
    LoanApplicationRead,
    LoanCreate,
    LoanRead,
    LoanUpdate,
    RenewalRequest,
)
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import get_current_user, require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["loans"])


@router.post("/loan-applications", response_model=LoanApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> LoanApplication:
    application = LoanApplication(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)

    write_audit(
        db,
        action="create_loan_application",
        entity_type="LoanApplication",
        entity_id=str(application.id),
        user=current_user,
        new_data=f"customer_id={application.customer_id}",
    )

    return application


@router.get("/loan-applications", response_model=list[LoanApplicationRead])
def list_applications(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> list[LoanApplication]:
    return list(db.scalars(select(LoanApplication).order_by(LoanApplication.id.desc())).all())


@router.post("/loan-applications/{application_id}/approve", response_model=LoanApplicationRead)
def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> LoanApplication:
    application = db.get(LoanApplication, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    application.status = "approved"
    application.reviewed_by = current_user.id
    application.approved_by = current_user.id
    db.commit()
    db.refresh(application)

    write_audit(
        db,
        action="approve_loan_application",
        entity_type="LoanApplication",
        entity_id=str(application.id),
        user=current_user,
        new_data="status=approved",
    )

    return application


@router.post("/loans", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def create_loan(
    payload: LoanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Loan:
    if payload.application_id:
        application = db.get(LoanApplication, payload.application_id)
        if application is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        if application.status != "approved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application must be approved")

    loan = Loan(
        application_id=payload.application_id,
        customer_id=payload.customer_id,
        loan_type=payload.loan_type,
        description=payload.description,
        principal_amount=payload.principal_amount,
        outstanding_principal=payload.principal_amount,
        monthly_interest_rate=payload.monthly_interest_rate,
        late_penalty_rate=payload.late_penalty_rate,
        disbursement_date=payload.disbursement_date,
        due_day=payload.due_day,
        status=LoanStatus.active,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    settings = db.get(GlobalSettings, 1)
    lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
    local_today = get_local_date(db)
    effective_as_of_date = local_today + timedelta(days=lead_days)
    generated_interest = generate_missing_interest_charges_for_loan(
        db=db,
        loan=loan,
        as_of_date=effective_as_of_date,
        charge_date=local_today,
    )
    if generated_interest:
        db.commit()
        for charge in generated_interest:
            db.refresh(charge)

    write_audit(
        db,
        action="create_loan",
        entity_type="Loan",
        entity_id=str(loan.id),
        user=current_user,
        new_data=f"principal={loan.principal_amount},interest_charges_generated={len(generated_interest)}",
    )

    return loan


@router.get("/loans", response_model=list[LoanRead])
def list_loans(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> list[Loan]:
    return list(db.scalars(select(Loan).order_by(Loan.id.desc())).all())


@router.get("/loans/{loan_id}", response_model=LoanRead)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    return loan


@router.put("/loans/{loan_id}", response_model=LoanRead)
def update_loan(
    loan_id: int,
    payload: LoanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    next_principal_amount = payload.principal_amount if payload.principal_amount is not None else loan.principal_amount
    next_outstanding_principal = (
        payload.outstanding_principal if payload.outstanding_principal is not None else loan.outstanding_principal
    )

    if next_outstanding_principal > next_principal_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outstanding principal cannot be greater than principal amount",
        )

    loan.loan_type = payload.loan_type if payload.loan_type is not None else loan.loan_type
    loan.description = payload.description if payload.description is not None else loan.description
    loan.principal_amount = next_principal_amount
    loan.outstanding_principal = next_outstanding_principal
    loan.monthly_interest_rate = payload.monthly_interest_rate
    loan.late_penalty_rate = payload.late_penalty_rate if payload.late_penalty_rate is not None else loan.late_penalty_rate
    loan.disbursement_date = payload.disbursement_date if payload.disbursement_date is not None else loan.disbursement_date
    loan.due_day = payload.due_day
    loan.status = payload.status

    settings = db.get(GlobalSettings, 1)
    lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
    local_today = get_local_date(db)
    effective_as_of_date = local_today + timedelta(days=lead_days)
    recalculated_interest = recalculate_interest_charges_for_loan(
        db=db,
        loan=loan,
        as_of_date=effective_as_of_date,
        charge_date=local_today,
    )

    db.commit()
    db.refresh(loan)

    for charge in recalculated_interest:
        db.refresh(charge)

    write_audit(
        db,
        action="update_loan",
        entity_type="Loan",
        entity_id=str(loan.id),
        user=current_user,
        new_data=(
            f"type={loan.loan_type.value},principal={loan.principal_amount},"
            f"outstanding={loan.outstanding_principal},rate={loan.monthly_interest_rate},"
            f"late_penalty={loan.late_penalty_rate},disbursement_date={loan.disbursement_date},"
            f"due_day={loan.due_day},status={loan.status.value},"
            f"interest_charges_recalculated={len(recalculated_interest)}"
        ),
    )

    return loan


@router.delete("/loans/{loan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> None:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    has_payment = db.scalar(select(Payment.id).where(Payment.loan_id == loan_id).limit(1)) is not None
    has_payment_events = db.scalar(select(PaymentEvent.id).where(PaymentEvent.loan_id == loan_id).limit(1)) is not None
    has_renewals = db.scalar(select(Loan.id).where(Loan.renewal_of == loan_id).limit(1)) is not None

    if has_payment or has_payment_events or has_renewals:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete loan with related credit records")

    db.execute(delete(CollateralItem).where(CollateralItem.loan_id == loan_id))
    db.execute(delete(InterestCharge).where(InterestCharge.loan_id == loan_id))
    db.delete(loan)
    db.commit()

    write_audit(
        db,
        action="delete_loan",
        entity_type="Loan",
        entity_id=str(loan_id),
        user=current_user,
        old_data=f"loan_deleted_with_no_traceability=true",
    )


@router.post("/loans/{loan_id}/renew", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def renew_loan(
    loan_id: int,
    payload: RenewalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Loan:
    source = db.get(Loan, loan_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    renewed = Loan(
        customer_id=source.customer_id,
        application_id=source.application_id,
        loan_type=source.loan_type,
        principal_amount=source.outstanding_principal,
        outstanding_principal=source.outstanding_principal,
        monthly_interest_rate=payload.monthly_interest_rate or source.monthly_interest_rate,
        disbursement_date=get_local_date(db),
        due_day=payload.due_day or source.due_day,
        status=LoanStatus.active,
        renewal_of=source.id,
    )
    source.status = LoanStatus.closed
    db.add(renewed)
    db.commit()
    db.refresh(renewed)

    write_audit(
        db,
        action="renew_loan",
        entity_type="Loan",
        entity_id=str(renewed.id),
        user=current_user,
        old_data=f"source_loan={source.id}",
        new_data=f"renewal_of={source.id}",
    )

    return renewed


@router.post("/loans/{loan_id}/close", response_model=LoanRead)
def close_loan(
    loan_id: int,
    payload: CloseLoanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    if not payload.force and loan.outstanding_principal > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outstanding principal must be zero")

    loan.status = LoanStatus.closed
    db.commit()
    db.refresh(loan)

    write_audit(
        db,
        action="close_loan",
        entity_type="Loan",
        entity_id=str(loan.id),
        user=current_user,
        new_data="status=closed",
    )

    return loan

@router.post("/{loan_id}/foreclose", response_model=LoanRead)
def foreclose_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.loan_type != "pawn":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pawn loans can be foreclosed")
    if loan.status in [LoanStatus.closed, LoanStatus.defaulted]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan is already closed or defaulted")

    loan.status = LoanStatus.defaulted

    # Find associated collateral items and mark them for sale
    from src.infrastructure.persistence.models import CollateralItem
    collateral_items = db.query(CollateralItem).filter(CollateralItem.loan_id == loan.id).all()
    for item in collateral_items:
        if item.status == "in_custody":
            item.status = "for_sale"

    db.commit()
    db.refresh(loan)

    write_audit(
        db,
        action="foreclose_loan",
        entity_type="Loan",
        entity_id=str(loan.id),
        user=current_user,
        new_data="status=defaulted",
    )

    return loan
