from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import GlobalSettings, InterestCharge, Loan, Payment, User
from src.modules.finance.interest_generation import (
    accruing_loans,
    generate_missing_interest_charges,
)
from src.infrastructure.tasks.interest_scheduler import interest_cycle_lock
from src.modules.finance.loan_status import describe_transitions, refresh_overdue_loan_statuses
from src.modules.finance.penalties import describe_frozen_penalties, freeze_due_penalties
from src.modules.finance.schemas import (
    InterestChargeRead,
    InterestGenerationRequest,
    LoanBalanceRead,
    VoidInterestChargeRequest,
)
from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import PaymentEvent
from src.infrastructure.utils.datetime_utils import get_local_datetime
from src.shared.dependencies.auth import get_current_user, require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(tags=["finance"])


@router.post("/interest/charges/{charge_id}/void", response_model=InterestChargeRead)
def void_interest_charge(
    charge_id: int,
    payload: VoidInterestChargeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> InterestCharge:
    """Cancel a charge that should never have been billed.

    Administrator only. The rest of the finance module takes a plain `get_current_user`
    because reading a balance and running a generation cycle harm nothing, but this forgives
    money — the same class of decision as writing off a loan or disposing of a pledge.

    The row is marked, never deleted. Deleting it would free its `(period_start, period_end)`
    slot and the next cycle would bill the very month that was just cancelled, and it would
    destroy the only record that the month was charged and then given back.

    **A charge with live payment events cannot be voided.** Money is already pointing at it,
    and every balance in the product derives from those events against `InterestCharge.amount`
    — removing the charge from under them would leave allocations describing a period that no
    longer exists. Reverse the payments first; a reversed event does not block, which is the
    same rule `DELETE /loans/{id}` follows.
    """
    charge = db.get(InterestCharge, charge_id)
    if charge is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interest charge not found")

    if charge.voided_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This charge is already voided")

    live_event = db.scalar(
        select(PaymentEvent.id)
        .where(
            PaymentEvent.interest_charge_id == charge.id,
            PaymentEvent.is_reversed.is_(False),
        )
        .limit(1)
    )
    if live_event is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This charge has payments applied to it. Reverse them before voiding it.",
        )

    charge.voided_at = get_local_datetime(db)
    charge.voided_by = current_user.id
    charge.void_reason = payload.reason.strip()

    # Built before the commit that expires the row.
    summary = f"loan_id={charge.loan_id},period={charge.period_start}..{charge.period_end},amount={charge.amount}"

    write_audit(
        db,
        action="void_interest_charge",
        entity_type="InterestCharge",
        entity_id=str(charge.id),
        user=current_user,
        new_data=f"{summary},reason={charge.void_reason}",
        commit=False,
    )

    db.commit()
    db.refresh(charge)
    return charge


@router.post("/interest/generate", response_model=list[InterestChargeRead])
def generate_interest(
    payload: InterestGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterestCharge]:
    # The scheduler guards its cycle with this lock; running the manual endpoint without it
    # let both generate the same billing period at once. Nothing at the DB level rejected
    # the duplicate, so customers ended up charged — and in two cases paying — twice.
    with interest_cycle_lock(db) as acquired:
        if not acquired:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Interest generation is already running. Try again in a moment.",
            )

        settings = db.get(GlobalSettings, 1)
        lead_days = max(0, settings.interest_generation_lead_days) if settings is not None else 0
        effective_as_of_date = payload.as_of_date + timedelta(days=lead_days)

        loans = accruing_loans(db)
        generated: list[InterestCharge] = generate_missing_interest_charges(
            db=db,
            loans=loans,
            as_of_date=effective_as_of_date,
            charge_date=payload.as_of_date,
        )

        frozen = freeze_due_penalties(db, payload.as_of_date)
        db.commit()

    for charge in generated:
        db.refresh(charge)

    if frozen:
        write_audit(
            db,
            action="freeze_late_penalties",
            entity_type="InterestCharge",
            entity_id=f"count={len(frozen)}",
            user=current_user,
            new_data=f"as_of_date={payload.as_of_date},{describe_frozen_penalties(frozen)}",
        )

    write_audit(
        db,
        action="generate_interest",
        entity_type="InterestCharge",
        entity_id=f"count={len(generated)}",
        user=current_user,
        new_data=f"as_of_date={payload.as_of_date}",
    )

    transitions = refresh_overdue_loan_statuses(db, payload.as_of_date)
    if transitions:
        db.commit()
        write_audit(
            db,
            action="refresh_loan_statuses",
            entity_type="Loan",
            entity_id=f"count={len(transitions)}",
            user=current_user,
            new_data=f"as_of_date={payload.as_of_date},{describe_transitions(transitions)}",
        )

    return generated


@router.get("/loans/{loan_id}/balance", response_model=LoanBalanceRead)
def loan_balance(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> LoanBalanceRead:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    total_interest = sum(item.amount for item in db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)))
    total_payments = sum(item.total_amount for item in db.scalars(select(Payment).where(Payment.loan_id == loan_id)))

    return LoanBalanceRead(
        loan_id=loan.id,
        principal_amount=loan.principal_amount,
        outstanding_principal=loan.outstanding_principal,
        total_interest_generated=round(total_interest, 2),
        total_payments=round(total_payments, 2),
    )


@router.get("/loans/{loan_id}/ledger")
def loan_ledger(
    loan_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found")

    interest = list(db.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)).all())
    payments = list(db.scalars(select(Payment).where(Payment.loan_id == loan_id)).all())

    return {
        "loan_id": loan_id,
        "interest_charges": [
            {
                "id": item.id,
                "charge_date": item.charge_date,
                "amount": item.amount,
                "status": item.status,
            }
            for item in interest
        ],
        "payments": [
            {
                "id": item.id,
                "payment_date": item.payment_date,
                "total_amount": item.total_amount,
                "is_reversed": item.is_reversed,
            }
            for item in payments
        ],
    }
