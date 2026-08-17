from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field
from src.modules.authentication.schemas import UserSummary




class PaymentUpdate(BaseModel):
    """Correcting how a payment was recorded, never how much money it moved.

    The amounts used to be editable here, and the edit reached the `Payment` row without
    reaching the ledger it was derived from: a collection of 100.000 spread over two
    billing periods, edited down to 50.000, left the receipt saying 50.000 while the debt
    stayed reduced by 100.000. Money that was taken in wrongly is corrected by reversing
    the payment, which asks for a reason and keeps both sides in step.
    """

    payment_date: date
    payment_method: str = "cash"
    notes: str = ""


class PaymentReversalRequest(BaseModel):
    """Reversing is how a payment is removed, so the grounds are mandatory."""

    reason: str = Field(min_length=3, max_length=500)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    payment_date: date
    total_amount: float
    allocated_to_penalty: float
    allocated_to_interest: float
    allocated_to_fees: float
    allocated_to_principal: float
    payment_method: str
    notes: str
    received_by: int | None
    is_reversed: bool
    reversed_at: datetime | None = None
    reversal_reason: str = ""
    receiver: UserSummary | None = None
    reverser: UserSummary | None = None


class InterestPendingItem(BaseModel):
    interest_charge_id: int
    loan_id: int
    loan_type: str
    disbursement_date: date
    billing_period: str
    due_date: date
    original_interest_amount: float
    remaining_pending_amount: float
    overdue: bool
    penalty_amount: float
    current_outstanding_balance: float


class InterestPendingGroup(BaseModel):
    billing_period: str
    items: list[InterestPendingItem]


class InterestPendingResponse(BaseModel):
    customer_id: int
    groups: list[InterestPendingGroup]
    total_pending_interest: float
    total_pending_penalty: float
    total_outstanding: float
    available_advance_balance: float


class InterestPaymentRequest(BaseModel):
    customer_id: int
    selected_charge_ids: list[int] = []
    pay_all_pending: bool = False
    total_amount: float
    payment_date: date | None = None
    payment_method: str = "cash"
    notes: str = ""
    # A retry carries the key of the attempt it repeats, and gets that payment back rather
    # than taking the money a second time. Optional: a caller that does not send one keeps the
    # old behaviour, which is what every existing integration and the test suite rely on.
    idempotency_key: str | None = Field(default=None, max_length=64)


class InterestPaymentAllocation(BaseModel):
    payment_event_id: int
    payment_id: int
    loan_id: int
    interest_charge_id: int | None
    payment_type: str
    billing_period: str
    allocated_to_interest: float
    allocated_to_penalty: float
    allocated_total: float


class InterestPaymentResponse(BaseModel):
    customer_id: int
    total_entered_amount: float
    total_allocated_amount: float
    unallocated_amount: float
    allocations: list[InterestPaymentAllocation]


class PrincipalLoanContext(BaseModel):
    loan_id: int
    loan_type: str
    disbursement_date: date
    next_due_date: date
    original_principal: float
    outstanding_principal: float
    accrued_unpaid_interest: float
    penalties: float
    total_payoff_amount: float


class PrincipalContextResponse(BaseModel):
    customer_id: int
    items: list[PrincipalLoanContext]


class PrincipalPaymentRequest(BaseModel):
    """One principal payment, against a single loan or spread over several.

    Either form is accepted: `loan_id` targets one loan, or `selected_loan_ids` /
    `pay_all_outstanding` (with `customer_id`) spread the money over the customer's open
    loans oldest-disbursement-first. Unlike interest, the client's selection is honoured —
    an operator settling a specific loan must not have the money silently sent elsewhere.
    """

    loan_id: int | None = None
    customer_id: int | None = None
    selected_loan_ids: list[int] = []
    pay_all_outstanding: bool = False
    total_amount: float
    payment_date: date | None = None
    payment_method: str = "cash"
    allow_with_unpaid_interest: bool = False
    notes: str = ""
    # A retry carries the key of the attempt it repeats, and gets that payment back rather
    # than taking the money a second time. Optional: a caller that does not send one keeps the
    # old behaviour, which is what every existing integration and the test suite rely on.
    idempotency_key: str | None = Field(default=None, max_length=64)


class PrincipalAllocation(BaseModel):
    payment_event_id: int
    loan_id: int
    payment_type: str
    allocated_to_principal: float
    new_outstanding_principal: float
    loan_status: str


class PrincipalPaymentResponse(BaseModel):
    payment_id: int
    total_entered_amount: float
    total_allocated_amount: float
    allocations: list[PrincipalAllocation]

    # Flat mirror of the first allocation. The single-loan form produces exactly one, so
    # these describe it exactly; callers handling several loans should read `allocations`.
    payment_event_id: int
    loan_id: int
    payment_type: str
    allocated_to_principal: float
    new_outstanding_principal: float
    loan_status: str


class PaymentAllocationRead(BaseModel):
    """One line of the printed "how was this payment distributed" breakdown."""

    payment_event_id: int
    payment_type: str
    loan_id: int
    interest_charge_id: int | None
    billing_period: str
    charge_amount: float | None
    charge_due_date: date | None
    allocated_to_interest: float
    allocated_to_penalty: float
    allocated_to_principal: float
    allocated_total: float
    fully_covered: bool
    is_reversed: bool


class PaymentAllocationsResponse(BaseModel):
    payment_id: int
    payment_date: date
    loan_ids: list[int]
    total_amount: float
    total_allocated: float
    unallocated_amount: float
    is_reversed: bool
    allocations: list[PaymentAllocationRead]


class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_type: str
    payment_id: int | None
    loan_id: int
    interest_charge_id: int | None
    billing_period: str
    total_entered_amount: float
    allocated_to_interest: float
    allocated_to_penalty: float
    allocated_to_principal: float
    payment_date: date
    operator_user_id: int | None
    payment_method: str
    notes: str
    is_reversed: bool
    operator: UserSummary | None = None


class InterestChargeHistoryItem(BaseModel):
    """One billing period of a customer, whatever state it is in.

    Deliberately a different shape from `InterestPendingItem`. That one feeds the collection
    screen and the allocation preview, where every row is money about to move; a settled period
    appearing in it would be offered for payment. This one is a record, and says so by carrying
    `settled` and `paid_amount` instead of a "will receive" figure.
    """

    interest_charge_id: int
    loan_id: int
    billing_period: str
    period_start: date
    period_end: date
    due_date: date
    charge_amount: float
    penalty_amount: float
    paid_amount: float
    outstanding: float
    settled: bool
    overdue: bool
    voided: bool
    void_reason: str = ""


class InterestChargeHistoryResponse(BaseModel):
    customer_id: int
    items: list[InterestChargeHistoryItem]
    total_charged: float
    total_paid: float
    total_outstanding: float
