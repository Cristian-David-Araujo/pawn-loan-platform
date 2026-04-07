from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, Loan, LoanApplication, User
from src.modules.finance.interest_generation import generate_missing_interest_charges_for_loan
from src.modules.loans.schemas import (
    CloseLoanRequest,
    LoanApplicationCreate,
    LoanApplicationRead,
    LoanCreate,
    LoanRead,
    LoanUpdate,
    RenewalRequest,
)
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["loans"])


@router.post("/loan-applications", response_model=LoanApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: LoanApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    _: User = Depends(get_current_user),
) -> list[LoanApplication]:
    return list(db.scalars(select(LoanApplication).order_by(LoanApplication.id.desc())).all())


@router.post("/loan-applications/{application_id}/approve", response_model=LoanApplicationRead)
def approve_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    effective_as_of_date = date.today() + timedelta(days=lead_days)
    generated_interest = generate_missing_interest_charges_for_loan(
        db=db,
        loan=loan,
        as_of_date=effective_as_of_date,
        charge_date=date.today(),
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
    _: User = Depends(get_current_user),
) -> list[Loan]:
    return list(db.scalars(select(Loan).order_by(Loan.id.desc())).all())


@router.get("/loans/{loan_id}", response_model=LoanRead)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
) -> Loan:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    loan.monthly_interest_rate = payload.monthly_interest_rate
    loan.due_day = payload.due_day
    loan.status = payload.status
    db.commit()
    db.refresh(loan)

    write_audit(
        db,
        action="update_loan",
        entity_type="Loan",
        entity_id=str(loan.id),
        user=current_user,
        new_data=f"rate={loan.monthly_interest_rate},due_day={loan.due_day},status={loan.status.value}",
    )

    return loan


@router.post("/loans/{loan_id}/renew", response_model=LoanRead, status_code=status.HTTP_201_CREATED)
def renew_loan(
    loan_id: int,
    payload: RenewalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        disbursement_date=date.today(),
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
    current_user: User = Depends(get_current_user),
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
