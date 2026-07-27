from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, Payment, PaymentEvent, User
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_balance import (
    charge_due_date,
    pending_interest_for_customer,
    pending_interest_items_for_customer,
    sync_interest_charge_statuses,
)
from src.modules.payments.schemas import (
    InterestPaymentAllocation,
    InterestPaymentRequest,
    InterestPaymentResponse,
    InterestPendingGroup,
    InterestPendingItem,
    InterestPendingResponse,
    PaymentAllocationRead,
    PaymentAllocationsResponse,
    PaymentCreate,
    PaymentEventRead,
    PaymentRead,
    PaymentUpdate,
    PrincipalContextResponse,
    PrincipalLoanContext,
    PrincipalAllocation,
    PrincipalPaymentRequest,
    PrincipalPaymentResponse,
)
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/payments", tags=["payments"])


def _month_anchor(year: int, month: int, anchor_day: int) -> date:
    last_day = monthrange(year, month)[1]
    day = min(max(1, anchor_day), last_day)
    return date(year, month, day)


def _add_months(base_date: date, months: int, anchor_day: int) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    return _month_anchor(year, month, anchor_day)


def _next_interest_generation_date(as_of_date: date, disbursement_date: date) -> date:
    anchor_day = disbursement_date.day
    current_anchor = _month_anchor(as_of_date.year, as_of_date.month, anchor_day)

    if as_of_date <= current_anchor:
        return current_anchor

    return _add_months(current_anchor, 1, anchor_day)


def _pending_interest_items_for_customer(db: Session, customer_id: int, today: date) -> list[InterestPendingItem]:
    """Adapt the canonical pending interest items to the API schema."""
    return [
        InterestPendingItem(
            interest_charge_id=item.interest_charge_id,
            loan_id=item.loan_id,
            loan_type=item.loan_type,
            disbursement_date=item.disbursement_date,
            billing_period=item.billing_period,
            due_date=item.due_date,
            original_interest_amount=item.original_interest_amount,
            remaining_pending_amount=item.pending_interest,
            overdue=item.overdue,
            penalty_amount=item.pending_penalty,
            current_outstanding_balance=item.outstanding,
        )
        for item in pending_interest_items_for_customer(db, customer_id, today)
    ]


@router.get("/customers/{customer_id}/interest-pending", response_model=InterestPendingResponse)
def get_pending_interest(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> InterestPendingResponse:
    today = get_local_date(db)
    balances = pending_interest_for_customer(db, customer_id, today)
    if not balances:
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
    # Advance balance left after the pending periods above already consumed their part.
    available_advance_balance = round(sum(balance.available_advance_balance for balance in balances), 2)

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
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> InterestPaymentResponse:
    if payload.total_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Total amount must be greater than zero")

    payment_date = payload.payment_date or get_local_date(db)

    items = _pending_interest_items_for_customer(db, payload.customer_id, payment_date)
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
            payment_date=payment_date,
            total_amount=advance_amount,
            allocated_to_penalty=0,
            allocated_to_interest=advance_amount,
            allocated_to_fees=0,
            allocated_to_principal=0,
            payment_method=payload.payment_method,
            received_by=current_user.id,
        )
        db.add(payment)
        db.flush()

        event = PaymentEvent(
            payment_type="interest_advance_payment",
            payment_id=payment.id,
            loan_id=loan.id,
            interest_charge_id=None,
            billing_period=payment_date.strftime("%Y-%m"),
            total_entered_amount=advance_amount,
            allocated_to_interest=advance_amount,
            allocated_to_penalty=0,
            allocated_to_principal=0,
            payment_date=payment_date,
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
                    payment_id=payment.id,
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

    # Business rule: every interest payment must be allocated oldest-first.
    # Selection hints are accepted for compatibility but allocation order is never overridden.
    selected_items = items

    selected_ids = [item.interest_charge_id for item in selected_items]
    charge_map = {
        charge.id: charge
        for charge in db.scalars(select(InterestCharge).where(InterestCharge.id.in_(selected_ids))).all()
    }

    payment = Payment(
        loan_id=selected_items[0].loan_id,
        payment_date=payment_date,
        total_amount=round(payload.total_amount, 2),
        allocated_to_penalty=0,
        allocated_to_interest=0,
        allocated_to_fees=0,
        allocated_to_principal=0,
        payment_method=payload.payment_method,
        received_by=current_user.id,
    )
    db.add(payment)
    db.flush()

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
        elif not item.overdue and item.due_date > payment_date:
            payment_type = "interest_advance_payment"

        event = PaymentEvent(
            payment_type=payment_type,
            payment_id=payment.id,
            loan_id=item.loan_id,
            interest_charge_id=item.interest_charge_id,
            billing_period=item.billing_period,
            total_entered_amount=allocated_total,
            allocated_to_interest=allocated_interest,
            allocated_to_penalty=allocated_penalty,
            allocated_to_principal=0,
            payment_date=payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.flush()

        allocations.append(
            InterestPaymentAllocation(
                payment_event_id=event.id,
                payment_id=payment.id,
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

        event = PaymentEvent(
            payment_type="interest_advance_payment",
            payment_id=payment.id,
            loan_id=target_loan_id,
            interest_charge_id=None,
            billing_period=payment_date.strftime("%Y-%m"),
            total_entered_amount=advance_amount,
            allocated_to_interest=advance_amount,
            allocated_to_penalty=0,
            allocated_to_principal=0,
            payment_date=payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.flush()

        allocations.append(
            InterestPaymentAllocation(
                payment_event_id=event.id,
                payment_id=payment.id,
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

    payment.allocated_to_interest = round(sum(item.allocated_to_interest for item in allocations), 2)
    payment.allocated_to_penalty = round(sum(item.allocated_to_penalty for item in allocations), 2)
    payment.allocated_to_principal = 0
    payment.allocated_to_fees = 0

    for loan_id in {item.loan_id for item in allocations}:
        sync_interest_charge_statuses(db, loan_id)

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
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> PrincipalContextResponse:
    loans = list(
        db.scalars(select(Loan).where(Loan.customer_id == customer_id, Loan.status != LoanStatus.closed)).all()
    )
    items: list[PrincipalLoanContext] = []
    today = get_local_date(db)

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
                next_due_date=charge_due_date(
                    _next_interest_generation_date(today, loan.disbursement_date),
                    loan.due_day,
                ),
                original_principal=loan.principal_amount,
                outstanding_principal=loan.outstanding_principal,
                accrued_unpaid_interest=unpaid_interest,
                penalties=penalties,
                total_payoff_amount=total_payoff,
            )
        )

    return PrincipalContextResponse(customer_id=customer_id, items=items)


def _resolve_principal_targets(db: Session, payload: PrincipalPaymentRequest) -> list[Loan]:
    """The loans a principal payment applies to, oldest disbursement first.

    Raises rather than quietly narrowing the list: a request naming a closed or foreign
    loan is an operator mistake worth surfacing, not something to drop from the allocation
    and let the money land somewhere else.
    """
    if payload.loan_id is not None:
        loan = db.get(Loan, payload.loan_id)
        if loan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
        if loan.status == LoanStatus.closed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Loan is already closed")
        return [loan]

    if payload.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either loan_id or customer_id is required",
        )

    open_loans = list(
        db.scalars(
            select(Loan).where(
                Loan.customer_id == payload.customer_id,
                Loan.status != LoanStatus.closed,
            )
        ).all()
    )
    by_id = {loan.id: loan for loan in open_loans}

    if payload.selected_loan_ids:
        targets = []
        for loan_id in payload.selected_loan_ids:
            loan = by_id.get(loan_id)
            if loan is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Loan {loan_id} is not an open loan of this customer",
                )
            targets.append(loan)
    elif payload.pay_all_outstanding:
        targets = open_loans
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one loan or set pay_all_outstanding",
        )

    targets = [loan for loan in targets if loan.outstanding_principal > 0]
    if not targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected loans have no outstanding principal",
        )

    # Oldest first, matching the rule interest allocation already follows.
    targets.sort(key=lambda loan: (loan.disbursement_date, loan.id))
    return targets


@router.post("/principal", response_model=PrincipalPaymentResponse)
def pay_principal(
    payload: PrincipalPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> PrincipalPaymentResponse:
    """Apply money to principal on one loan or across several.

    Targets are settled oldest-disbursement-first, each capped at its own outstanding
    principal, and every target is validated before a single row is written: a payment
    that cannot be fully applied is rejected instead of landing halfway. Principal has no
    equivalent of the interest advance pool, so leftover money is an error, not a credit.
    """
    if payload.total_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Total amount must be greater than zero")

    payment_date = payload.payment_date or get_local_date(db)
    targets = _resolve_principal_targets(db, payload)

    total_capacity = round(sum(loan.outstanding_principal for loan in targets), 2)
    if round(payload.total_amount, 2) > total_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Principal payment cannot exceed outstanding principal",
        )

    if not payload.allow_with_unpaid_interest:
        pending_items = _pending_interest_items_for_customer(db, targets[0].customer_id, payment_date)
        for loan in targets:
            unpaid_interest = round(
                sum(item.current_outstanding_balance for item in pending_items if item.loan_id == loan.id),
                2,
            )
            if unpaid_interest > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Principal payment blocked: unpaid accrued interest exists on loan {loan.id}",
                )

    payment = Payment(
        loan_id=targets[0].id,
        payment_date=payment_date,
        total_amount=round(payload.total_amount, 2),
        allocated_to_penalty=0,
        allocated_to_interest=0,
        allocated_to_fees=0,
        allocated_to_principal=round(payload.total_amount, 2),
        payment_method=payload.payment_method,
        received_by=current_user.id,
    )
    db.add(payment)
    db.flush()

    remaining = round(payload.total_amount, 2)
    allocations: list[PrincipalAllocation] = []

    for loan in targets:
        if remaining <= 0:
            break

        applied = round(min(loan.outstanding_principal, remaining), 2)
        if applied <= 0:
            continue

        loan.outstanding_principal = round(max(0.0, loan.outstanding_principal - applied), 2)
        if loan.outstanding_principal == 0:
            loan.status = LoanStatus.closed

        payment_type = "full_settlement" if loan.outstanding_principal == 0 else "partial_principal_payment"
        event = PaymentEvent(
            payment_type=payment_type,
            payment_id=payment.id,
            loan_id=loan.id,
            interest_charge_id=None,
            billing_period="",
            total_entered_amount=applied,
            allocated_to_interest=0,
            allocated_to_penalty=0,
            allocated_to_principal=applied,
            payment_date=payment_date,
            operator_user_id=current_user.id,
            payment_method=payload.payment_method,
            notes=payload.notes,
        )
        db.add(event)
        db.flush()

        allocations.append(
            PrincipalAllocation(
                payment_event_id=event.id,
                loan_id=loan.id,
                payment_type=payment_type,
                allocated_to_principal=applied,
                new_outstanding_principal=loan.outstanding_principal,
                loan_status=loan.status.value,
            )
        )

        remaining = round(remaining - applied, 2)

    if not allocations:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to allocate payment")

    db.commit()

    total_allocated = round(sum(item.allocated_to_principal for item in allocations), 2)
    write_audit(
        db,
        action="principal_payment",
        entity_type="PaymentEvent",
        entity_id=str(allocations[0].payment_event_id),
        user=current_user,
        new_data=(
            f"payment={payment.id},loans={[item.loan_id for item in allocations]},"
            f"amount={total_allocated}"
        ),
    )

    first = allocations[0]
    return PrincipalPaymentResponse(
        payment_id=payment.id,
        total_entered_amount=round(payload.total_amount, 2),
        total_allocated_amount=total_allocated,
        allocations=allocations,
        payment_event_id=first.payment_event_id,
        loan_id=first.loan_id,
        payment_type=first.payment_type,
        allocated_to_principal=first.allocated_to_principal,
        new_outstanding_principal=first.new_outstanding_principal,
        loan_status=first.loan_status,
    )



@router.get("/customers/{customer_id}/history", response_model=list[PaymentEventRead])
def customer_payment_history(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
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
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> list[Payment]:
    return list(db.query(Payment).order_by(Payment.id.desc()).all())


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
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


@router.put("/{payment_id}", response_model=PaymentRead)
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reversed payments cannot be edited")

    loan = db.get(Loan, payment.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    allocated_sum = (
        payload.allocated_to_penalty
        + payload.allocated_to_interest
        + payload.allocated_to_fees
        + payload.allocated_to_principal
    )
    if round(allocated_sum, 2) != round(payload.total_amount, 2):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Allocation sum must match total amount")

    old_allocated_principal = payment.allocated_to_principal
    old_payment_snapshot = {
        "payment_date": payment.payment_date,
        "total_amount": payment.total_amount,
        "allocated_to_interest": payment.allocated_to_interest,
        "allocated_to_penalty": payment.allocated_to_penalty,
        "allocated_to_principal": payment.allocated_to_principal,
        "payment_method": payment.payment_method,
    }

    payment.payment_date = payload.payment_date
    payment.total_amount = round(payload.total_amount, 2)
    payment.allocated_to_penalty = round(payload.allocated_to_penalty, 2)
    payment.allocated_to_interest = round(payload.allocated_to_interest, 2)
    payment.allocated_to_fees = round(payload.allocated_to_fees, 2)
    payment.allocated_to_principal = round(payload.allocated_to_principal, 2)
    payment.payment_method = payload.payment_method
    payment.notes = payload.notes

    principal_delta = round(payment.allocated_to_principal - old_allocated_principal, 2)
    loan.outstanding_principal = round(max(0.0, loan.outstanding_principal - principal_delta), 2)
    if loan.outstanding_principal == 0:
        loan.status = LoanStatus.closed
    elif loan.status == LoanStatus.closed:
        loan.status = LoanStatus.active

    matching_events = list(
        db.scalars(
            select(PaymentEvent).where(
                PaymentEvent.loan_id == payment.loan_id,
                PaymentEvent.payment_date == old_payment_snapshot["payment_date"],
                PaymentEvent.total_entered_amount == old_payment_snapshot["total_amount"],
                PaymentEvent.allocated_to_interest == old_payment_snapshot["allocated_to_interest"],
                PaymentEvent.allocated_to_penalty == old_payment_snapshot["allocated_to_penalty"],
                PaymentEvent.allocated_to_principal == old_payment_snapshot["allocated_to_principal"],
                PaymentEvent.payment_method == old_payment_snapshot["payment_method"],
            )
        ).all()
    )
    if len(matching_events) == 1:
        event = matching_events[0]
        event.total_entered_amount = payment.total_amount
        event.allocated_to_interest = payment.allocated_to_interest
        event.allocated_to_penalty = payment.allocated_to_penalty
        event.allocated_to_principal = payment.allocated_to_principal
        event.payment_date = payment.payment_date
        event.payment_method = payment.payment_method

    db.flush()
    sync_interest_charge_statuses(db, payment.loan_id)

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="update_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        old_data=(
            f"total={old_payment_snapshot['total_amount']},principal={old_payment_snapshot['allocated_to_principal']},"
            f"date={old_payment_snapshot['payment_date']},method={old_payment_snapshot['payment_method']}"
        ),
        new_data=(
            f"total={payment.total_amount},principal={payment.allocated_to_principal},"
            f"date={payment.payment_date},method={payment.payment_method},"
            f"linked_event_updated={len(matching_events) == 1}"
        ),
    )

    return payment


@router.post("/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.is_reversed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment already reversed")

    loan = db.get(Loan, payment.loan_id)
    if loan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked loan not found")

    # Reversing the payment must also reverse its ledger rows, otherwise their
    # allocations would keep cancelling interest that was returned to the customer.
    linked_events = list(db.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id)).all())
    affected_loan_ids = {event.loan_id for event in linked_events} | {loan.id}
    for event in linked_events:
        event.is_reversed = True

    payment.is_reversed = True
    loan.outstanding_principal = round(loan.outstanding_principal + payment.allocated_to_principal, 2)
    if loan.status == LoanStatus.closed:
        loan.status = LoanStatus.active

    db.flush()
    for loan_id in affected_loan_ids:
        sync_interest_charge_statuses(db, loan_id)

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="reverse_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        new_data=f"is_reversed=true,reversed_events={len(linked_events)}",
    )

    return payment


@router.get("/{payment_id}/allocations", response_model=PaymentAllocationsResponse)
def payment_allocations(
    payment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> PaymentAllocationsResponse:
    """The ledger rows behind one payment, in the order the money was applied.

    A single payment can settle several interest charges across several loans, because
    allocation is oldest-charge-first and ignores any client selection. ``Payment`` only
    keeps the per-bucket totals and points at the *first* loan, so the printed receipt
    needs this breakdown to be traceable. Payments created through the plain
    ``POST /payments`` path have no ledger rows and return an empty list.
    """
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    events = list(
        db.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.payment_id == payment.id)
            .order_by(PaymentEvent.id.asc())
        ).all()
    )

    charge_ids = [event.interest_charge_id for event in events if event.interest_charge_id is not None]
    charges = (
        {
            charge.id: charge
            for charge in db.scalars(select(InterestCharge).where(InterestCharge.id.in_(charge_ids))).all()
        }
        if charge_ids
        else {}
    )

    loan_ids = sorted({event.loan_id for event in events} | {payment.loan_id})
    loans = {loan.id: loan for loan in db.scalars(select(Loan).where(Loan.id.in_(loan_ids))).all()}

    allocations: list[PaymentAllocationRead] = []
    for event in events:
        charge = charges.get(event.interest_charge_id) if event.interest_charge_id is not None else None
        loan = loans.get(event.loan_id)
        allocations.append(
            PaymentAllocationRead(
                payment_event_id=event.id,
                payment_type=event.payment_type,
                loan_id=event.loan_id,
                interest_charge_id=event.interest_charge_id,
                billing_period=event.billing_period,
                charge_amount=charge.amount if charge is not None else None,
                charge_due_date=(
                    charge_due_date(charge.period_end, loan.due_day)
                    if charge is not None and loan is not None
                    else None
                ),
                allocated_to_interest=event.allocated_to_interest,
                allocated_to_penalty=event.allocated_to_penalty,
                allocated_to_principal=event.allocated_to_principal,
                allocated_total=round(
                    event.allocated_to_interest + event.allocated_to_penalty + event.allocated_to_principal,
                    2,
                ),
                # "partial_interest_payment" is stamped precisely when the allocation did
                # not clear the charge, so it is the authoritative signal here.
                fully_covered=event.payment_type != "partial_interest_payment",
                is_reversed=event.is_reversed,
            )
        )

    # Reversal is a separate axis from allocation: a reversed payment keeps its rows but
    # they no longer count, so totals only sum live rows while `is_reversed` explains the gap.
    total_allocated = round(
        sum(item.allocated_total for item in allocations if not item.is_reversed), 2
    )
    never_allocated = round(
        payment.total_amount - sum(item.allocated_total for item in allocations), 2
    )

    return PaymentAllocationsResponse(
        payment_id=payment.id,
        payment_date=payment.payment_date,
        loan_ids=loan_ids,
        total_amount=round(payment.total_amount, 2),
        total_allocated=total_allocated,
        unallocated_amount=max(0.0, never_allocated),
        is_reversed=payment.is_reversed,
        allocations=allocations,
    )


@router.get("/events/{event_id}", response_model=PaymentEventRead)
def get_payment_event(
    event_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> PaymentEvent:
    event = db.get(PaymentEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment event not found")
    return event
