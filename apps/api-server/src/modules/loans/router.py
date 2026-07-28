from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import AuditLog, CollateralItem, GlobalSettings, InterestCharge, Loan, LoanApplication, Payment, PaymentEvent, User
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_balance import default_grace_days
from src.modules.finance.interest_generation import generate_missing_interest_charges_for_loan, recalculate_interest_charges_for_loan
from src.modules.finance.penalties import freeze_due_penalties
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
from src.shared.dependencies.auth import require_roles
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
        # Grace is portfolio policy. The create form used to send the day-of-month of the
        # disbursement here, which handed a loan signed on the 25th a 25 day grace period.
        due_day=default_grace_days(db),
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
        # A loan registered with a backdated disbursement is born with periods that already
        # fell due. Their penalty is fixed here rather than left for the nightly cycle, so
        # an operator who collects right after registering it is not quoted a debt short.
        freeze_due_penalties(db, local_today)
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
    loan.monthly_interest_rate = (
        payload.monthly_interest_rate if payload.monthly_interest_rate is not None else loan.monthly_interest_rate
    )
    loan.late_penalty_rate = payload.late_penalty_rate if payload.late_penalty_rate is not None else loan.late_penalty_rate
    loan.disbursement_date = payload.disbursement_date if payload.disbursement_date is not None else loan.disbursement_date
    loan.due_day = default_grace_days(db)
    loan.status = payload.status if payload.status is not None else loan.status

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

    # Reversed money is undone money. A loan whose every payment was reversed never really
    # collected anything, so a mistake — wrong customer, wrong loan, paid off by accident —
    # can be undone completely. Live rows are what make a loan permanent.
    live_payment = db.scalar(
        select(Payment.id).where(Payment.loan_id == loan_id, Payment.is_reversed.is_(False)).limit(1)
    )
    live_event = db.scalar(
        select(PaymentEvent.id)
        .where(PaymentEvent.loan_id == loan_id, PaymentEvent.is_reversed.is_(False))
        .limit(1)
    )
    if live_payment is not None or live_event is not None:
        # 409 to match the customer endpoint: the request is well formed, the resource state
        # is what forbids it.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Loan has live payment records. Reverse them first to delete the loan.",
        )

    if db.scalar(select(Loan.id).where(Loan.renewal_of == loan_id).limit(1)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Loan was renewed into another loan and cannot be deleted.",
        )

    payments = list(db.scalars(select(Payment).where(Payment.loan_id == loan_id)).all())
    events = list(db.scalars(select(PaymentEvent).where(PaymentEvent.loan_id == loan_id)).all())
    payment_ids = {item.id for item in payments}

    # One payment can spread across several loans, so a ledger row on this loan may belong to
    # a payment recorded against a different one. Deleting it would leave that payment
    # describing money it no longer accounts for.
    if any(event.payment_id is not None and event.payment_id not in payment_ids for event in events):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A payment on this loan also covers other loans and cannot be unwound here.",
        )

    # Deleting takes the collateral, the accruals and the reversed payments with it, so the
    # audit row has to carry a full snapshot — it is the only surviving record of what
    # existed. This used to write the literal string
    # "loan_deleted_with_no_traceability=true" and nothing else.
    collaterals = list(db.scalars(select(CollateralItem).where(CollateralItem.loan_id == loan_id)).all())
    charges = list(db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)).all())
    snapshot = (
        f"customer={loan.customer_id},type={loan.loan_type.value},status={loan.status.value},"
        f"principal={loan.principal_amount},outstanding={loan.outstanding_principal},"
        f"rate={loan.monthly_interest_rate},penalty_rate={loan.late_penalty_rate},"
        f"disbursed={loan.disbursement_date},due_day={loan.due_day},"
        f"collaterals=[{'; '.join(f'{item.custody_code}:{item.description}:{item.appraised_value}:{item.status}' for item in collaterals)}],"
        f"interest_charges=[{'; '.join(f'{item.period_start}..{item.period_end}:{item.amount}' for item in charges)}],"
        f"reversed_payments=[{'; '.join(f'{item.id}:{item.payment_date}:{item.total_amount}:{item.payment_method}:{item.reversal_reason}' for item in payments)}]"
    )

    # Children before parents: events reference both payments and interest charges.
    db.execute(delete(PaymentEvent).where(PaymentEvent.loan_id == loan_id))
    db.execute(delete(Payment).where(Payment.loan_id == loan_id))
    db.execute(delete(CollateralItem).where(CollateralItem.loan_id == loan_id))
    db.execute(delete(InterestCharge).where(InterestCharge.loan_id == loan_id))
    db.delete(loan)

    # Same transaction as the delete: an audit row that can be lost while the delete
    # survives is worse than no audit at all, because it reads as "this never existed".
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="delete_loan",
            entity_type="Loan",
            entity_id=str(loan_id),
            old_data=snapshot,
            new_data=(
                f"deleted_collaterals={len(collaterals)},deleted_interest_charges={len(charges)},"
                f"deleted_reversed_payments={len(payments)},deleted_ledger_rows={len(events)}"
            ),
        )
    )
    db.commit()


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
    if source.status == LoanStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan is already closed")

    carried_principal = round(source.outstanding_principal, 2)

    renewed = Loan(
        customer_id=source.customer_id,
        application_id=source.application_id,
        loan_type=source.loan_type,
        # The pledge description and the penalty policy belong to the debt, not to the row
        # that happened to carry it: leaving them out started the new loan with an empty
        # description and a penalty rate of 0, which also silently zeroed its grace days.
        description=source.description,
        principal_amount=carried_principal,
        outstanding_principal=carried_principal,
        monthly_interest_rate=payload.monthly_interest_rate or source.monthly_interest_rate,
        late_penalty_rate=source.late_penalty_rate,
        disbursement_date=get_local_date(db),
        due_day=default_grace_days(db),
        status=LoanStatus.active,
        renewal_of=source.id,
    )
    db.add(renewed)
    db.flush()

    # The principal moved to the new loan, so the source must stop carrying it. It used to
    # keep its full outstanding while being closed, and `principal-context` reports any loan
    # that still owes — so one 1.000.000 loan renewed once showed the customer owing
    # 2.000.000 on screen and on the printed statement, while `_resolve_principal_targets`
    # refused to collect the closed half. The interest already accrued stays where it was
    # accrued: the source keeps owing it, and it is collected from the interest screen.
    source.outstanding_principal = 0.0
    source.status = LoanStatus.closed

    # A pawn loan without its pledge has no security. The items used to stay pointed at the
    # closed loan, which left the live debt with nothing behind it and made the custody
    # report attribute the goods to a loan that no longer existed for anyone.
    moved_pledges = list(
        db.scalars(
            select(CollateralItem).where(
                CollateralItem.loan_id == source.id,
                CollateralItem.status == "in_custody",
            )
        ).all()
    )
    for item in moved_pledges:
        item.loan_id = renewed.id

    db.commit()
    db.refresh(renewed)

    write_audit(
        db,
        action="renew_loan",
        entity_type="Loan",
        entity_id=str(renewed.id),
        user=current_user,
        old_data=f"source_loan={source.id},source_outstanding={carried_principal}",
        new_data=(
            f"renewal_of={source.id},principal={carried_principal},"
            f"rate={renewed.monthly_interest_rate},late_penalty={renewed.late_penalty_rate},"
            f"pledges_moved={[item.id for item in moved_pledges]}"
        ),
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

@router.post("/loans/{loan_id}/foreclose", response_model=LoanRead)
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
