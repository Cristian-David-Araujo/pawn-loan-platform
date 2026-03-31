from datetime import date

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    loan_id: int
    payment_date: date
    total_amount: float
    allocated_to_penalty: float = 0
    allocated_to_interest: float = 0
    allocated_to_fees: float = 0
    allocated_to_principal: float = 0
    payment_method: str = "cash"


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
    received_by: int | None
    is_reversed: bool


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
    payment_date: date = date.today()
    payment_method: str = "cash"
    notes: str = ""


class InterestPaymentAllocation(BaseModel):
    payment_event_id: int
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
    loan_id: int
    total_amount: float
    payment_date: date = date.today()
    payment_method: str = "cash"
    allow_with_unpaid_interest: bool = False
    notes: str = ""


class PrincipalPaymentResponse(BaseModel):
    payment_event_id: int
    loan_id: int
    payment_type: str
    total_entered_amount: float
    allocated_to_principal: float
    new_outstanding_principal: float
    loan_status: str


class PaymentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_type: str
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
