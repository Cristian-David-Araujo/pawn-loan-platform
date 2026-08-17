from calendar import monthrange
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import InterestCharge, Loan, Payment, PaymentEvent, User
from src.infrastructure.utils.datetime_utils import get_local_date, get_local_datetime
from src.modules.finance.allocation import AllocationTarget, allocate_oldest_first
from src.modules.finance.locks import lock_customer_loans, lock_loans
from src.modules.finance.loan_status import describe_transitions, refresh_overdue_loan_statuses
from src.modules.finance.interest_balance import (
    charge_due_date,
    default_grace_days,
    grace_days_for_loan,
    pending_interest_by_charge_for_loans,
    pending_interest_for_customer,
    pending_interest_items_for_customer,
    sync_interest_charge_statuses,
)
from src.modules.payments.schemas import (
    InterestChargeHistoryItem,
    InterestChargeHistoryResponse,
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
    PaymentReversalRequest,
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


@router.get("/customers/{customer_id}/interest-history", response_model=InterestChargeHistoryResponse)
def get_interest_history(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer, UserRole.collector)),
) -> InterestChargeHistoryResponse:
    """Every billing period of a customer, settled or not.

    Separate from `interest-pending` on purpose. That endpoint feeds the collection screen and
    the allocation preview, where every row is money about to move — adding settled periods to
    it would put paid invoices in front of an operator taking a payment. This one is a record:
    it answers "which invoices does this customer have and which are paid", which until now the
    application could not answer at all.

    Two kinds of row are left out because they are not invoices. A zero-amount `not_billed`
    marker is a month deliberately never charged — it exists only so the generator does not
    fill the gap later. A voided charge *is* shown, marked as such with its reason, because an
    invoice that was cancelled is part of the customer's history and hiding it would make a
    period simply vanish between two statements.
    """
    today = get_local_date(db)
    loans = list(db.scalars(select(Loan).where(Loan.customer_id == customer_id).order_by(Loan.id)).all())
    if not loans:
        return InterestChargeHistoryResponse(
            customer_id=customer_id, items=[], total_charged=0, total_paid=0, total_outstanding=0
        )

    loan_ids = [loan.id for loan in loans]
    loans_by_id = {loan.id: loan for loan in loans}
    configured_grace = default_grace_days(db)

    charges = list(
        db.scalars(
            select(InterestCharge)
            .where(InterestCharge.loan_id.in_(loan_ids), InterestCharge.amount > 0)
            .order_by(InterestCharge.period_end.desc(), InterestCharge.id.desc())
        ).all()
    )
    if not charges:
        return InterestChargeHistoryResponse(
            customer_id=customer_id, items=[], total_charged=0, total_paid=0, total_outstanding=0
        )

    # The canonical balances, so a period reads the same here as on the collection screen.
    pending_by_charge = pending_interest_by_charge_for_loans(db, loans)

    events = list(
        db.scalars(
            select(PaymentEvent).where(
                PaymentEvent.loan_id.in_(loan_ids),
                PaymentEvent.is_reversed.is_(False),
                PaymentEvent.interest_charge_id.isnot(None),
            )
        ).all()
    )
    paid_by_charge: dict[int, float] = {}
    for event in events:
        paid_by_charge[event.interest_charge_id] = round(
            paid_by_charge.get(event.interest_charge_id, 0.0)
            + event.allocated_to_interest
            + event.allocated_to_penalty,
            2,
        )

    items: list[InterestChargeHistoryItem] = []
    for charge in charges:
        loan = loans_by_id[charge.loan_id]
        due_date = charge_due_date(charge.period_end, grace_days_for_loan(loan, configured_grace))
        penalty = round(charge.penalty_amount or 0.0, 2)
        voided = charge.voided_at is not None
        # A voided period owes nothing by definition; it is excluded from the canonical
        # balances, so its outstanding has to be zeroed here rather than looked up.
        outstanding = 0.0 if voided else round(pending_by_charge.get(charge.id, 0.0) + penalty, 2)

        items.append(
            InterestChargeHistoryItem(
                interest_charge_id=charge.id,
                loan_id=charge.loan_id,
                billing_period=charge.period_start.strftime("%Y-%m"),
                period_start=charge.period_start,
                period_end=charge.period_end,
                due_date=due_date,
                charge_amount=round(charge.amount, 2),
                penalty_amount=penalty,
                paid_amount=paid_by_charge.get(charge.id, 0.0),
                outstanding=outstanding,
                settled=outstanding <= 0 and not voided,
                overdue=outstanding > 0 and due_date < today,
                voided=voided,
                void_reason=charge.void_reason or "",
            )
        )

    return InterestChargeHistoryResponse(
        customer_id=customer_id,
        items=items,
        total_charged=round(sum(item.charge_amount + item.penalty_amount for item in items if not item.voided), 2),
        total_paid=round(sum(item.paid_amount for item in items), 2),
        total_outstanding=round(sum(item.outstanding for item in items), 2),
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

    # Allocation and the advance pool both span the customer's whole book, so the book is
    # what has to hold still between reading the balances and writing the ledger rows.
    lock_customer_loans(db, payload.customer_id)

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
        db.flush()
        write_audit(
            db,
            action="interest_advance_payment",
            entity_type="PaymentEvent",
            entity_id=str(event.id),
            user=current_user,
            new_data=f"customer={payload.customer_id},amount={advance_amount}",
            commit=False,
        )
        db.commit()
        db.refresh(event)

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

    # Oldest period first, penalty before interest — the shared rule, so money taken here and
    # money coming out of a foreclosure sale can never credit the same debt differently.
    targets = [
        AllocationTarget(
            interest_charge_id=item.interest_charge_id,
            loan_id=item.loan_id,
            billing_period=item.billing_period,
            outstanding=item.current_outstanding_balance,
            pending_penalty=item.penalty_amount,
            overdue=item.overdue,
            due_date=item.due_date,
        )
        for item in selected_items
        if item.interest_charge_id in charge_map
    ]
    interest_slices, remaining = allocate_oldest_first(targets, payload.total_amount)
    allocations: list[InterestPaymentAllocation] = []

    for item_slice in interest_slices:
        target = item_slice.target

        payment_type = "interest_payment"
        if not item_slice.fully_covered:
            payment_type = "partial_interest_payment"
        elif not target.overdue and target.due_date > payment_date:
            payment_type = "interest_advance_payment"

        event = PaymentEvent(
            payment_type=payment_type,
            payment_id=payment.id,
            loan_id=target.loan_id,
            interest_charge_id=target.interest_charge_id,
            billing_period=target.billing_period,
            total_entered_amount=item_slice.allocated_total,
            allocated_to_interest=item_slice.allocated_interest,
            allocated_to_penalty=item_slice.allocated_penalty,
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
                loan_id=target.loan_id,
                interest_charge_id=target.interest_charge_id,
                payment_type=payment_type,
                billing_period=target.billing_period,
                allocated_to_interest=item_slice.allocated_interest,
                allocated_to_penalty=item_slice.allocated_penalty,
                allocated_total=item_slice.allocated_total,
            )
        )

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

    # A loan that just cleared its past-due interest is no longer overdue, and it must say so
    # now. This used to be reached only by the interest cycle, so the label lagged the money
    # by up to AUTO_INTEREST_GENERATION_INTERVAL_MINUTES — a day, by default: the customer
    # paid at the counter, the receipt printed, and the loan still read "vencido".
    #
    # Scoped to the customer's whole book, not to the loans that received an event. Interest
    # is allocated oldest-first across every loan they hold and the advance pool is theirs
    # rather than any one loan's, so paying on #7 can settle a period on #12. The book is
    # already locked by `lock_customer_loans` above, so this costs no extra contention.
    customer_loan_ids = list(
        db.scalars(select(Loan.id).where(Loan.customer_id == payload.customer_id)).all()
    )
    transitions = refresh_overdue_loan_statuses(db, payment_date, loan_ids=customer_loan_ids)

    # Same transaction as the money: written after the commit, this row is a second
    # transaction that can fail while the payment stands, leaving a collection nobody
    # appears to have taken.
    write_audit(
        db,
        action="interest_payment",
        entity_type="PaymentEvent",
        entity_id=f"customer={payload.customer_id}",
        user=current_user,
        new_data=(
            f"entered={payload.total_amount},allocated={total_allocated},"
            f"{describe_transitions(transitions)}"
        ),
        commit=False,
    )
    db.commit()

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
    items: list[PrincipalLoanContext] = []
    today = get_local_date(db)

    configured_grace_days = default_grace_days(db)
    pending_items = _pending_interest_items_for_customer(db, customer_id, today)
    pending_by_loan: dict[int, list[InterestPendingItem]] = {}
    for pending in pending_items:
        pending_by_loan.setdefault(pending.loan_id, []).append(pending)

    # Open loans, plus any closed loan that still owes interest — a loan closed with
    # `allow_with_unpaid_interest` sits at zero principal with live charges, and leaving it
    # out made printed balances report zero interest on a debt that still exists. Such a
    # loan carries no outstanding principal, so it can never become a payment target.
    loans = list(
        db.scalars(
            select(Loan).where(
                Loan.customer_id == customer_id,
                or_(Loan.status != LoanStatus.closed, Loan.id.in_(pending_by_loan.keys() or [-1])),
            )
        ).all()
    )

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
                    grace_days_for_loan(loan, configured_grace_days),
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
    lock_loans(db, targets)

    total_capacity = round(sum(loan.outstanding_principal for loan in targets), 2)
    if round(payload.total_amount, 2) > total_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Principal payment cannot exceed outstanding principal",
        )

    if not payload.allow_with_unpaid_interest:
        # Canonical items rather than the API adapter, because the decision needs
        # `period_end`: `interest_generation_lead_days` bills a period up to ten days before
        # it ends, so the pending list deliberately shows the month in progress. Blocking on
        # that refused a customer's principal payment over interest that had not accrued yet.
        # A period only counts as accrued once it has run its course.
        accrued_items = [
            item
            for item in pending_interest_items_for_customer(db, targets[0].customer_id, payment_date)
            if item.period_end <= payment_date
        ]
        for loan in targets:
            unpaid_interest = round(
                sum(item.outstanding for item in accrued_items if item.loan_id == loan.id),
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

    total_allocated = round(sum(item.allocated_to_principal for item in allocations), 2)

    # Principal cannot by itself change whether a loan is overdue — that is decided by
    # past-due *interest*. This is here so the rule "every money path leaves the status
    # correct before it commits" holds without exception, and because this path does move a
    # loan to `closed` at zero principal: a loan that was `overdue` and is now closed must
    # not be re-examined, which the managed-status filter already guarantees.
    transitions = refresh_overdue_loan_statuses(
        db,
        payment_date,
        loan_ids=[item.loan_id for item in allocations],
    )

    write_audit(
        db,
        commit=False,
        action="principal_payment",
        entity_type="PaymentEvent",
        entity_id=str(allocations[0].payment_event_id),
        user=current_user,
        new_data=(
            f"payment={payment.id},loans={[item.loan_id for item in allocations]},"
            f"amount={total_allocated},{describe_transitions(transitions)}"
        ),
    )
    db.commit()

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

    old_payment_snapshot = {
        "payment_date": payment.payment_date,
        "payment_method": payment.payment_method,
        "notes": payment.notes,
    }

    payment.payment_date = payload.payment_date
    payment.payment_method = payload.payment_method
    payment.notes = payload.notes

    # Located by `payment_id`, not by matching six fields for an exact value: that lookup
    # updated a single row only when precisely one matched, so a collection spread over
    # several periods — or two identical payments on the same day — silently updated none.
    for event in db.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id)).all():
        event.payment_date = payment.payment_date
        event.payment_method = payment.payment_method
        event.notes = payment.notes

    db.commit()
    db.refresh(payment)

    write_audit(
        db,
        action="update_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        old_data=(
            f"date={old_payment_snapshot['payment_date']},method={old_payment_snapshot['payment_method']},"
            f"notes={old_payment_snapshot['notes']}"
        ),
        new_data=f"date={payment.payment_date},method={payment.payment_method},notes={payment.notes}",
    )

    return payment


@router.post("/{payment_id}/reverse", response_model=PaymentRead)
def reverse_payment(
    payment_id: int,
    payload: PaymentReversalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> Payment:
    """Remove a payment's effect while keeping the record.

    This is the only way a payment is ever taken out of the books — the rows are never
    deleted, because the ledger is what proves what was collected and returned. The reason,
    the operator and the timestamp are stored on the payment so the removal is answerable
    without digging through audit rows the application never displays.
    """
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

    # Principal goes back per ledger row. One payment can pay down several loans, so adding
    # `payment.allocated_to_principal` to `payment.loan_id` alone would over-credit that loan
    # and leave every other one short by what it had received.
    restored_by_loan: dict[int, float] = {}
    for event in linked_events:
        event.is_reversed = True
        if event.allocated_to_principal:
            restored_by_loan[event.loan_id] = round(
                restored_by_loan.get(event.loan_id, 0.0) + event.allocated_to_principal, 2
            )

    # Payments written through the plain POST /payments path have no ledger rows, so fall
    # back to the flat allocation against the payment's own loan.
    if not linked_events and payment.allocated_to_principal:
        restored_by_loan[payment.loan_id] = round(payment.allocated_to_principal, 2)

    affected_loan_ids = {event.loan_id for event in linked_events} | {loan.id} | set(restored_by_loan)
    loans = {item.id: item for item in db.scalars(select(Loan).where(Loan.id.in_(affected_loan_ids))).all()}

    for loan_id, amount in restored_by_loan.items():
        target = loans.get(loan_id)
        if target is None:
            continue
        target.outstanding_principal = round(target.outstanding_principal + amount, 2)
        # Reopen only what this reversal put back into debt; a loan closed by some other
        # payment has no business being reopened here.
        if target.status == LoanStatus.closed and target.outstanding_principal > 0:
            target.status = LoanStatus.active

    payment.is_reversed = True
    payment.reversed_at = get_local_datetime(db)
    payment.reversed_by = current_user.id
    payment.reversal_reason = payload.reason.strip()

    db.flush()
    for loan_id in affected_loan_ids:
        sync_interest_charge_statuses(db, loan_id)

    # The mirror of the collection: putting the interest back can make a loan overdue again,
    # and the operator who just reversed a payment is the one who needs to see that. It runs
    # after the `closed` -> `active` reopening above, so a loan restored to active is judged
    # on the debt it now carries rather than staying active by default.
    reversal_transitions = refresh_overdue_loan_statuses(
        db,
        get_local_date(db),
        loan_ids=affected_loan_ids,
    )

    write_audit(
        db,
        commit=False,
        action="reverse_payment",
        entity_type="Payment",
        entity_id=str(payment.id),
        user=current_user,
        old_data=(
            f"total={payment.total_amount},principal={payment.allocated_to_principal},"
            f"interest={payment.allocated_to_interest},penalty={payment.allocated_to_penalty},"
            f"date={payment.payment_date},method={payment.payment_method}"
        ),
        new_data=(
            f"is_reversed=true,reversed_events={len(linked_events)},"
            f"principal_restored={restored_by_loan},reason={payment.reversal_reason},"
            f"{describe_transitions(reversal_transitions)}"
        ),
    )

    db.commit()
    db.refresh(payment)

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
                    charge_due_date(
                        charge.period_end, grace_days_for_loan(loan, default_grace_days(db))
                    )
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
