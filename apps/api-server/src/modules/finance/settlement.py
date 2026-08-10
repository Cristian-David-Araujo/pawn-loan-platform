"""Settling a loan for less than it owes.

The last resort: the customer cannot pay the debt in full, the operator takes what they can
get, and the rest is written off. It is deliberately not a payment path — a payment records
money moving, and this records money moving *and* a decision to stop pursuing the remainder.

Three things here are decisions rather than mechanics:

**The money is applied exactly as it would be at the counter.** `allocate_oldest_first` is
the single ordering rule in this system — oldest period first, penalty before interest — and
this calls it rather than carrying its own loop. The foreclosure sale already learned that
lesson; two copies of that ordering drifting apart is how the same debt starts reporting two
figures.

**The remainder is voided, not merely orphaned.** Closing the loan is not enough on its own:
`pending_interest_for_customer` deliberately keeps a closed loan that still owes, because
`pay_principal` closes a loan the moment its principal hits zero and that debt is still real.
So a settlement that only closed the loan would leave the forgiven interest sitting on the
collection screen forever, uncollectable and unremovable. Voiding each remaining charge is
what actually ends it, and it reuses the same mechanism an administrator uses to cancel a
single charge.

**A settlement cannot exceed the debt.** Paying more than is owed is not a settlement, it is
a normal payment with change, and letting it through here would write off a negative.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import (
    CollateralItem,
    InterestCharge,
    Loan,
    Payment,
    PaymentEvent,
    User,
)
from src.modules.finance.allocation import AllocationTarget, allocate_oldest_first
from src.modules.finance.interest_balance import pending_interest_for_loan
from src.modules.finance.locks import lock_loans

# Its own type, so a receipt and the payment history can tell a negotiated settlement from an
# ordinary collection. Anything added here must also be added to `paymentTypeKey()` in the web
# client, which is the only place a payment type is turned into words.
SETTLEMENT_PAYMENT_TYPE = "settlement_payment"

# What `InterestCharge.void_reason` carries when the write-off came from a settlement rather
# than from an administrator cancelling one charge by hand.
SETTLEMENT_VOID_REASON = "loan_settlement"

# What the operator chose to do with the pledges, if there are any.
RELEASE_COLLATERAL = "release"
KEEP_COLLATERAL_FOR_SALE = "for_sale"
COLLATERAL_ACTIONS = (RELEASE_COLLATERAL, KEEP_COLLATERAL_FOR_SALE)


class SettlementError(ValueError):
    """Refused, carrying a message fit to show the operator."""


@dataclass(frozen=True)
class SettlementResult:
    payment: Payment
    events: list[PaymentEvent]
    applied_to_penalty: float
    applied_to_interest: float
    applied_to_principal: float
    written_off_interest: float
    written_off_principal: float
    voided_charge_ids: list[int]
    collateral_ids: list[int]

    @property
    def written_off_total(self) -> float:
        return round(self.written_off_interest + self.written_off_principal, 2)

    def describe(self) -> str:
        """Compact audit representation, built before the commit it describes."""
        return (
            f"settled={self.payment.total_amount},"
            f"penalty={self.applied_to_penalty},interest={self.applied_to_interest},"
            f"principal={self.applied_to_principal},"
            f"written_off_interest={self.written_off_interest},"
            f"written_off_principal={self.written_off_principal},"
            f"voided_charges={len(self.voided_charge_ids)}"
        )


def settle_loan(
    db: Session,
    loan: Loan,
    *,
    amount: float,
    payment_date: date,
    payment_method: str,
    reason: str,
    collateral_action: str,
    user: User,
    now: datetime,
) -> SettlementResult:
    """Take ``amount`` against the loan, write off the rest, and close it.

    Nothing is committed here — the caller owns the transaction, so the payment, the
    write-off and the audit row all land together or not at all.
    """
    if loan.settled_at is not None:
        raise SettlementError("This loan has already been settled")

    if collateral_action not in COLLATERAL_ACTIONS:
        raise SettlementError(f"Unknown collateral action: {collateral_action}")

    amount = round(max(0.0, amount), 2)

    # Read the balance only after the row is held, or two operators settling at once both
    # decide their write-off against the same figure.
    lock_loans(db, [loan])
    balance = pending_interest_for_loan(db, loan, payment_date)

    outstanding_principal = round(loan.outstanding_principal, 2)
    total_debt = round(balance.outstanding + outstanding_principal, 2)

    if amount > total_debt:
        raise SettlementError(
            f"A settlement of {amount} is more than the {total_debt} this loan owes. "
            "Record a normal payment instead."
        )

    targets = [
        AllocationTarget(
            interest_charge_id=item.interest_charge_id,
            loan_id=item.loan_id,
            billing_period=item.billing_period,
            outstanding=item.outstanding,
            pending_penalty=item.pending_penalty,
            overdue=item.overdue,
            due_date=item.due_date,
        )
        for item in balance.items
    ]

    slices, leftover = allocate_oldest_first(targets, amount)

    # Whatever the periods did not absorb goes to principal, exactly as a counter payment
    # would apply it. It can never exceed the outstanding principal, because `amount` was
    # already checked against the whole debt.
    applied_to_principal = round(min(leftover, outstanding_principal), 2)

    payment = Payment(
        loan_id=loan.id,
        payment_date=payment_date,
        total_amount=amount,
        allocated_to_penalty=round(sum(item.allocated_penalty for item in slices), 2),
        allocated_to_interest=round(sum(item.allocated_interest for item in slices), 2),
        allocated_to_principal=applied_to_principal,
        allocated_to_fees=0.0,
        payment_method=payment_method,
        notes=reason,
        received_by=user.id,
    )
    db.add(payment)
    # The events reference the payment, so it needs an id before they are built.
    db.flush()

    events: list[PaymentEvent] = []
    for allocation in slices:
        event = PaymentEvent(
            payment_type=SETTLEMENT_PAYMENT_TYPE,
            payment_id=payment.id,
            loan_id=loan.id,
            interest_charge_id=allocation.target.interest_charge_id,
            billing_period=allocation.target.billing_period,
            total_entered_amount=amount,
            allocated_to_interest=allocation.allocated_interest,
            allocated_to_penalty=allocation.allocated_penalty,
            allocated_to_principal=0.0,
            payment_date=payment_date,
            operator_user_id=user.id,
            payment_method=payment_method,
            notes=reason,
        )
        db.add(event)
        events.append(event)

    if applied_to_principal > 0:
        event = PaymentEvent(
            payment_type=SETTLEMENT_PAYMENT_TYPE,
            payment_id=payment.id,
            loan_id=loan.id,
            interest_charge_id=None,
            billing_period="",
            total_entered_amount=amount,
            allocated_to_interest=0.0,
            allocated_to_penalty=0.0,
            allocated_to_principal=applied_to_principal,
            payment_date=payment_date,
            operator_user_id=user.id,
            payment_method=payment_method,
            notes=reason,
        )
        db.add(event)
        events.append(event)

    # ── The write-off ────────────────────────────────────────────────────────────────────
    covered_by_charge = {
        allocation.target.interest_charge_id: allocation.allocated_total for allocation in slices
    }

    charges_by_id = {
        charge.id: charge
        for charge in db.scalars(
            select(InterestCharge).where(
                InterestCharge.loan_id == loan.id,
                InterestCharge.voided_at.is_(None),
            )
        ).all()
    }

    written_off_interest = 0.0
    voided_charge_ids: list[int] = []
    for item in balance.items:
        remainder = round(item.outstanding - covered_by_charge.get(item.interest_charge_id, 0.0), 2)
        if remainder <= 0:
            continue

        charge = charges_by_id.get(item.interest_charge_id)
        if charge is None:
            continue

        charge.voided_at = now
        charge.voided_by = user.id
        charge.void_reason = SETTLEMENT_VOID_REASON
        written_off_interest = round(written_off_interest + remainder, 2)
        voided_charge_ids.append(charge.id)

    written_off_principal = round(outstanding_principal - applied_to_principal, 2)

    loan.outstanding_principal = 0.0
    loan.status = LoanStatus.closed
    loan.settled_at = now
    loan.settled_by = user.id
    loan.settlement_reason = reason
    loan.settlement_amount = amount
    loan.written_off_principal = written_off_principal
    loan.written_off_interest = written_off_interest
    # A settled loan owes nothing, so there is nothing left to stop the clock on — but the
    # flag would otherwise sit there claiming a pause that no longer means anything.
    loan.interest_paused = False

    # ── The pledges ──────────────────────────────────────────────────────────────────────
    collateral = list(
        db.scalars(
            select(CollateralItem).where(
                CollateralItem.loan_id == loan.id,
                CollateralItem.status == "in_custody",
            )
        ).all()
    )
    # Released, the pledge goes back to the customer: the debt is extinguished, so the goods
    # are theirs. Kept, it lands in `for_sale` exactly as a foreclosure would leave it, and
    # `POST /collateral-items/{id}/sell` can then run — with the debt already at zero, the
    # whole price is recorded as the house's in `allocated_to_fees`.
    for pledge in collateral:
        pledge.status = "released" if collateral_action == RELEASE_COLLATERAL else "for_sale"

    return SettlementResult(
        payment=payment,
        events=events,
        applied_to_penalty=payment.allocated_to_penalty,
        applied_to_interest=payment.allocated_to_interest,
        applied_to_principal=applied_to_principal,
        written_off_interest=written_off_interest,
        written_off_principal=written_off_principal,
        voided_charge_ids=voided_charge_ids,
        collateral_ids=[pledge.id for pledge in collateral],
    )
