from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, Payment, PaymentEvent, User
from src.modules.payments.schemas import (
    InterestPaymentAllocation,
    InterestPaymentRequest,
    InterestPaymentResponse,
    InterestPendingGroup,
    InterestPendingItem,
    InterestPendingResponse,
    PaymentCreate,
    PaymentEventRead,
    PaymentRead,
    PrincipalContextResponse,
    PrincipalLoanContext,
    PrincipalPaymentRequest,
    PrincipalPaymentResponse,
)
from src.shared.dependencies.auth import get_current_user
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/payments", tags=["payments"])


def _compute_charge_pending(db: Session, charge: InterestCharge, today: date) -> dict[str, float | bool]:
    events = list(db.scalars(select(PaymentEvent).where(PaymentEvent.interest_charge_id == charge.id)).all())
    paid_interest = round(sum(item.allocated_to_interest for item in events), 2)
    paid_penalty = round(sum(item.allocated_to_penalty for item in events), 2)

    base_pending = round(max(0.0, charge.amount - paid_interest), 2)
    overdue = charge.period_end < today
    penalty_amount = round(base_pending * 0.02, 2) if overdue and base_pending > 0 else 0.0
    pending_penalty = round(max(0.0, penalty_amount - paid_penalty), 2)
    outstanding = round(base_pending + pending_penalty, 2)
    return {
        "base_pending": base_pending,
        "pending_penalty": pending_penalty,
        "penalty_amount": penalty_amount,
        "overdue": overdue,
        "outstanding": outstanding,
    }


def _pending_interest_items_for_customer(db: Session, customer_id: int, today: date) -> list[InterestPendingItem]:
    loans = list(
        db.scalars(select(Loan).where(Loan.customer_id == customer_id, Loan.status != LoanStatus.closed)).all()
    )
    if not loans:
        return []

    loan_by_id = {loan.id: loan for loan in loans}
    items: list[InterestPendingItem] = []
    for loan in loans:
        charges = list(
            db.scalars(
                select(InterestCharge)
                .where(
                    InterestCharge.loan_id == loan.id,
                    InterestCharge.status.in_(["generated", "partially_paid"]),
                )
                .order_by(InterestCharge.period_end.asc(), InterestCharge.id.asc())
            ).all()
        )

        advance_pool = round(
            sum(
                event.allocated_to_interest
                for event in db.scalars(
                    select(PaymentEvent).where(
                        PaymentEvent.loan_id == loan.id,
                        PaymentEvent.interest_charge_id.is_(None),
                        PaymentEvent.payment_type == "interest_advance_payment",
                    )
                ).all()
            ),
            2,
        )

        for charge in charges:
            charge_events = list(
                db.scalars(select(PaymentEvent).where(PaymentEvent.interest_charge_id == charge.id)).all()
            )

            paid_interest = round(sum(item.allocated_to_interest for item in charge_events), 2)
            paid_penalty = round(sum(item.allocated_to_penalty for item in charge_events), 2)

            base_pending = round(max(0.0, charge.amount - paid_interest), 2)
            if advance_pool > 0 and base_pending > 0:
                advance_applied = round(min(advance_pool, base_pending), 2)
                base_pending = round(base_pending - advance_applied, 2)
                advance_pool = round(advance_pool - advance_applied, 2)

            overdue = charge.period_end < today
            penalty_amount = round(base_pending * 0.02, 2) if overdue and base_pending > 0 else 0.0
            pending_penalty = round(max(0.0, penalty_amount - paid_penalty), 2)
            outstanding = round(base_pending + pending_penalty, 2)
            if outstanding <= 0:
                continue

            items.append(
                InterestPendingItem(
                    interest_charge_id=charge.id,
                    loan_id=charge.loan_id,
                    loan_type=loan.loan_type.value,
                    disbursement_date=loan.disbursement_date,
                    billing_period=charge.period_start.strftime("%Y-%m"),
                    due_date=charge.period_end,
                    original_interest_amount=round(charge.amount, 2),
                    remaining_pending_amount=round(base_pending, 2),
                    overdue=overdue,
                    penalty_amount=round(pending_penalty, 2),
                    current_outstanding_balance=round(outstanding, 2),
                )
            )

    return sorted(items, key=lambda item: (item.due_date, item.loan_id, item.interest_charge_id))


@router.get("/customers/{customer_id}/interest-pending", response_model=InterestPendingResponse)
def get_pending_interest(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> InterestPendingResponse:
    today = date.today()
    loans = list(
        db.scalars(select(Loan).where(Loan.customer_id == customer_id, Loan.status != LoanStatus.closed)).all()
    )
    loan_ids = [loan.id for loan in loans]
    if not loan_ids:
        return InterestPendingResponse(
            customer_id=customer_id,
            groups=[],
            total_pending_interest=0,
            total_pending_penalty=0,
            total_outstanding=0,
            available_advance_balance=0,
        )

    items = _pending_interest_items_for_customer(db, customer_id, today)

    grouped: dict[str, list[InterestPendingItem]] = {}
    for item in items:
        grouped.setdefault(item.billing_period, []).append(item)

    groups = [
        InterestPendingGroup(billing_period=period, items=period_items)
        for period, period_items in sorted(grouped.items())
    ]

    total_pending_interest = round(sum(item.remaining_pending_amount for item in items), 2)
    total_pending_penalty = round(sum(item.penalty_amount for item in items), 2)
    total_outstanding = round(sum(item.current_outstanding_balance for item in items), 2)
    total_available_advance = round(
        sum(
            event.allocated_to_interest
            for event in db.scalars(
                select(PaymentEvent).where(
                    PaymentEvent.loan_id.in_(loan_ids),
                    PaymentEvent.interest_charge_id.is_(None),
                    PaymentEvent.payment_type == "interest_advance_payment",
                )
            ).all()
        ),
        2,
    )

    total_generated_interest = round(
        sum(
            charge.amount
            for charge in db.scalars(
                select(InterestCharge).where(
                    InterestCharge.loan_id.in_(loan_ids),
                )
            ).all()
        ),
        2,
    )

    total_linked_interest_paid = round(
        sum(
            event.allocated_to_interest
            for event in db.scalars(
                select(PaymentEvent).where(
                    PaymentEvent.loan_id.in_(loan_ids),
                    PaymentEvent.interest_charge_id.is_not(None),
                )
            ).all()
        ),
        2,
    )

    consumed_advance = max(0.0, total_generated_interest - total_linked_interest_paid - total_pending_interest)
    available_advance_balance = round(max(0.0, total_available_advance - consumed_advance), 2)

    return InterestPendingResponse(
        customer_id=customer_id,
        groups=groups,
        total_pending_interest=total_pending_interest,
        total_pending_penalty=total_pending_penalty,
        total_outstanding=total_outstanding,
        available_advance_balance=available_advance_balance,
    )


@router.post("/interest", response_model=InterestPaymentResponse)
def pay_interest(
    payload: InterestPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterestPaymentResponse:
    if payload.total_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Total amount must be greater than zero")

    items = _pending_interest_items_for_customer(db, payload.customer_id, payload.payment_date)
    if not items:
        loan = db.scalar(
            select(Loan)
            .where(Loan.customer_id == payload.customer_id, Loan.status != LoanStatus.closed)
            .order_by(Loan.id.asc())
        )
        if loan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer has no active loans")

        advance_amount = round(payload.total_amount, 2)
        payment = Payment(
            loan_id=loan.id,
            payment_date=payload.payment_date,
            total_amount=advance_amount,
            allocated_to_penalty=0,
            allocated_to_interest=advance_amount,
            allocated_to_fees=0,
            allocated_to_principal=0,
            payment_method=payload.payment_method,
            received_by=current_user.id,
        )
        db.add(payment)

        event = PaymentEvent(
            payment_type="interest_advance_payment",
            loan_id=loan.id,
            interest_charge_id=None,
            billing_period=payload.payment_date.strftime("%Y-%m"),
            total_entered_amount=advance_amount,
            allocated_to_interest=advance_amount,
            allocated_to_penalty=0,
            allocated_to_principal=0,
            payment_date=payload.payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        write_audit(
            db,
            action="interest_advance_payment",
            entity_type="PaymentEvent",
            entity_id=str(event.id),
            user=current_user,
            new_data=f"customer={payload.customer_id},amount={advance_amount}",
        )

        return InterestPaymentResponse(
            customer_id=payload.customer_id,
            total_entered_amount=advance_amount,
            total_allocated_amount=advance_amount,
            unallocated_amount=0,
            allocations=[
                InterestPaymentAllocation(
                    payment_event_id=event.id,
                    loan_id=loan.id,
                    interest_charge_id=None,
                    payment_type="interest_advance_payment",
                    billing_period=event.billing_period,
                    allocated_to_interest=advance_amount,
                    allocated_to_penalty=0,
                    allocated_total=advance_amount,
                )
            ],
        )

    if payload.pay_all_pending:
        selected_items = items
    elif payload.selected_charge_ids:
        selected = set(payload.selected_charge_ids)
        selected_items = [item for item in items if item.interest_charge_id in selected]
    else:
        loan = db.scalar(
            select(Loan)
            .where(Loan.customer_id == payload.customer_id, Loan.status != LoanStatus.closed)
            .order_by(Loan.id.asc())
        )
        if loan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer has no active loans")

        advance_amount = round(payload.total_amount, 2)
        payment = Payment(
            loan_id=loan.id,
            payment_date=payload.payment_date,
            total_amount=advance_amount,
            allocated_to_penalty=0,
            allocated_to_interest=advance_amount,
            allocated_to_fees=0,
            allocated_to_principal=0,
            payment_method=payload.payment_method,
            received_by=current_user.id,
        )
        db.add(payment)

        event = PaymentEvent(
            payment_type="interest_advance_payment",
            loan_id=loan.id,
            interest_charge_id=None,
            billing_period=payload.payment_date.strftime("%Y-%m"),
            total_entered_amount=advance_amount,
            allocated_to_interest=advance_amount,
            allocated_to_penalty=0,
            allocated_to_principal=0,
            payment_date=payload.payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.commit()
        db.refresh(event)

        write_audit(
            db,
            action="interest_advance_payment",
            entity_type="PaymentEvent",
            entity_id=str(event.id),
            user=current_user,
            new_data=f"customer={payload.customer_id},amount={advance_amount}",
        )

        return InterestPaymentResponse(
            customer_id=payload.customer_id,
            total_entered_amount=advance_amount,
            total_allocated_amount=advance_amount,
            unallocated_amount=0,
            allocations=[
                InterestPaymentAllocation(
                    payment_event_id=event.id,
                    loan_id=loan.id,
                    interest_charge_id=None,
                    payment_type="interest_advance_payment",
                    billing_period=event.billing_period,
                    allocated_to_interest=advance_amount,
                    allocated_to_penalty=0,
                    allocated_total=advance_amount,
                )
            ],
        )

    if not selected_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid pending charges selected")

    selected_ids = [item.interest_charge_id for item in selected_items]
    charge_map = {
        charge.id: charge
        for charge in db.scalars(select(InterestCharge).where(InterestCharge.id.in_(selected_ids))).all()
    }
    remaining = round(payload.total_amount, 2)
    allocations: list[InterestPaymentAllocation] = []

    for item in selected_items:
        if remaining <= 0:
            break

        charge = charge_map.get(item.interest_charge_id)
        if charge is None:
            continue

        max_allocatable = item.current_outstanding_balance
        allocated_total = round(min(max_allocatable, remaining), 2)
        if allocated_total <= 0:
            continue

        allocated_penalty = round(min(item.penalty_amount, allocated_total), 2)
        allocated_interest = round(max(0.0, allocated_total - allocated_penalty), 2)

        payment_type = "interest_payment"
        if allocated_total < max_allocatable:
            payment_type = "partial_interest_payment"
        elif not item.overdue and item.due_date > payload.payment_date:
            payment_type = "interest_advance_payment"

        payment = Payment(
            loan_id=item.loan_id,
            payment_date=payload.payment_date,
            total_amount=allocated_total,
            allocated_to_penalty=allocated_penalty,
            allocated_to_interest=allocated_interest,
            allocated_to_fees=0,
            allocated_to_principal=0,
            payment_method=payload.payment_method,
            received_by=current_user.id,
        )
        db.add(payment)

        event = PaymentEvent(
            payment_type=payment_type,
            loan_id=item.loan_id,
            interest_charge_id=item.interest_charge_id,
            billing_period=item.billing_period,
            total_entered_amount=allocated_total,
            allocated_to_interest=allocated_interest,
            allocated_to_penalty=allocated_penalty,
            allocated_to_principal=0,
            payment_date=payload.payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.flush()

        current_outstanding = round(item.current_outstanding_balance - allocated_total, 2)
        charge.status = "paid" if current_outstanding <= 0 else "partially_paid"

        allocations.append(
            InterestPaymentAllocation(
                payment_event_id=event.id,
                loan_id=item.loan_id,
                interest_charge_id=item.interest_charge_id,
                payment_type=payment_type,
                billing_period=item.billing_period,
                allocated_to_interest=allocated_interest,
                allocated_to_penalty=allocated_penalty,
                allocated_total=allocated_total,
            )
        )

        remaining = round(remaining - allocated_total, 2)

    if remaining > 0:
        target_loan_id = selected_items[0].loan_id
        advance_amount = remaining

        payment = Payment(
            loan_id=target_loan_id,
            payment_date=payload.payment_date,
            total_amount=advance_amount,
            allocated_to_penalty=0,
            allocated_to_interest=advance_amount,
            allocated_to_fees=0,
            allocated_to_principal=0,
            payment_method=payload.payment_method,
            received_by=current_user.id,
        )
        db.add(payment)

        event = PaymentEvent(
            payment_type="interest_advance_payment",
            loan_id=target_loan_id,
            interest_charge_id=None,
            billing_period=payload.payment_date.strftime("%Y-%m"),
            total_entered_amount=advance_amount,
            allocated_to_interest=advance_amount,
            allocated_to_penalty=0,
            allocated_to_principal=0,
            payment_date=payload.payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.flush()

        allocations.append(
            InterestPaymentAllocation(
                payment_event_id=event.id,
                loan_id=target_loan_id,
                interest_charge_id=None,
                payment_type="interest_advance_payment",
                billing_period=event.billing_period,
                allocated_to_interest=advance_amount,
                allocated_to_penalty=0,
                allocated_total=advance_amount,
            )
        )

        remaining = 0

    total_allocated = round(sum(item.allocated_total for item in allocations), 2)
    if total_allocated <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to allocate payment")

    db.commit()

    write_audit(
        db,
        action="interest_payment",
        entity_type="PaymentEvent",
        entity_id=f"customer={payload.customer_id}",
        user=current_user,
        new_data=f"entered={payload.total_amount},allocated={total_allocated}",
    )

    return InterestPaymentResponse(
        customer_id=payload.customer_id,
        total_entered_amount=round(payload.total_amount, 2),
        total_allocated_amount=total_allocated,
        unallocated_amount=round(max(0.0, payload.total_amount - total_allocated), 2),
        allocations=allocations,
    )


@router.get("/customers/{customer_id}/principal-context", response_model=PrincipalContextResponse)
def principal_context(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PrincipalContextResponse:
    loans = list(
        db.scalars(select(Loan).where(Loan.customer_id == customer_id, Loan.status != LoanStatus.closed)).all()
    )
    items: list[PrincipalLoanContext] = []
    today = date.today()

    pending_items = _pending_interest_items_for_customer(db, customer_id, today)
    pending_by_loan: dict[int, list[InterestPendingItem]] = {}
    for pending in pending_items:
        pending_by_loan.setdefault(pending.loan_id, []).append(pending)

    for loan in loans:
        pending_loan = pending_by_loan.get(loan.id, [])
        unpaid_interest = round(sum(item.remaining_pending_amount for item in pending_loan), 2)
        penalties = round(sum(item.penalty_amount for item in pending_loan), 2)
        total_payoff = round(loan.outstanding_principal + unpaid_interest + penalties, 2)

        items.append(
            PrincipalLoanContext(
                loan_id=loan.id,
                loan_type=loan.loan_type.value,
                disbursement_date=loan.disbursement_date,
                next_due_date=today + timedelta(days=max(1, loan.due_day)),
                original_principal=loan.principal_amount,
                outstanding_principal=loan.outstanding_principal,
                accrued_unpaid_interest=unpaid_interest,
                penalties=penalties,
                total_payoff_amount=total_payoff,
            )
        )

    return PrincipalContextResponse(customer_id=customer_id, items=items)


@router.post("/principal", response_model=PrincipalPaymentResponse)
def pay_principal(
    payload: PrincipalPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrincipalPaymentResponse:
    if payload.total_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Total amount must be greater than zero")

    loan = db.get(Loan, payload.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status == LoanStatus.closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan is already closed")

    pending_items = _pending_interest_items_for_customer(db, loan.customer_id, payload.payment_date)
    unpaid_interest = round(
        sum(item.current_outstanding_balance for item in pending_items if item.loan_id == loan.id),
        2,
    )
    if unpaid_interest > 0 and not payload.allow_with_unpaid_interest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Principal payment blocked: unpaid accrued interest exists",
        )

    if round(payload.total_amount, 2) > round(loan.outstanding_principal, 2):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Principal payment cannot exceed outstanding principal",
        )

    applied_principal = round(payload.total_amount, 2)
    loan.outstanding_principal = round(max(0.0, loan.outstanding_principal - applied_principal), 2)
    if loan.outstanding_principal == 0:
        loan.status = LoanStatus.closed

    payment = Payment(
        loan_id=loan.id,
        payment_date=payload.payment_date,
        total_amount=applied_principal,
        allocated_to_penalty=0,
        allocated_to_interest=0,
        allocated_to_fees=0,
        allocated_to_principal=applied_principal,
        payment_method=payload.payment_method,
        received_by=current_user.id,
    )
    db.add(payment)

    payment_type = "full_settlement" if loan.outstanding_principal == 0 else "partial_principal_payment"
    event = PaymentEvent(
        payment_type=payment_type,
        loan_id=loan.id,
        interest_charge_id=None,
        billing_period="",
        total_entered_amount=applied_principal,
        allocated_to_interest=0,
        allocated_to_penalty=0,
        allocated_to_principal=applied_principal,
        payment_date=payload.payment_date,
        operator_user_id=current_user.id,
        payment_method=payload.payment_method,
        notes=payload.notes,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    db.refresh(loan)

    write_audit(
        db,
        action="principal_payment",
        entity_type="PaymentEvent",
        entity_id=str(event.id),
        user=current_user,
        new_data=f"loan_id={loan.id},amount={applied_principal}",
    )

    return PrincipalPaymentResponse(
        payment_event_id=event.id,
        loan_id=loan.id,
        payment_type=payment_type,
        total_entered_amount=applied_principal,
        allocated_to_principal=applied_principal,
        new_outstanding_principal=loan.outstanding_principal,
        loan_status=loan.status.value,
    )


@router.get("/customers/{customer_id}/history", response_model=list[PaymentEventRead])
def customer_payment_history(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PaymentEvent]:
    loan_ids = [
        item.id
        for item in db.scalars(select(Loan).where(Loan.customer_id == customer_id)).all()
    ]
    if not loan_ids:
        return []

    return list(
        db.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.loan_id.in_(loan_ids))
            .order_by(PaymentEvent.payment_date.desc(), PaymentEvent.id.desc())
        ).all()
    )


@router.get("", response_model=list[PaymentRead])
def list_payments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Payment]:
    return list(db.query(Payment).order_by(Payment.id.desc()).all())


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    loan = db.get(Loan, payload.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")

    allocated_sum = (
        payload.allocated_to_penalty
        + payload.allocated_to_interest
        + payload.allocated_to_fees
        + payload.allocated_to_principal
    )
    if round(allocated_sum, 2) != round(payload.total_amount, 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation sum must match total amount")

    payment = Payment(**payload.model_dump(), received_by=current_user.id)
    db.add(payment)

    loan.outstanding_principal = max(0, loan.outstanding_principal - payload.allocated_to_principal)
    if loan.outstanding_principal == 0:
        loan.status = LoanStatus.closed

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="create_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        new_data=f"amount={payment.total_amount}",
    )

    return payment


@router.post("/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already reversed")

    loan = db.get(Loan, payment.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    payment.is_reversed = True
    loan.outstanding_principal += payment.allocated_to_principal
    if loan.status == LoanStatus.closed:
        loan.status = LoanStatus.active

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="reverse_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        new_data="is_reversed=true",
    )

    return payment
