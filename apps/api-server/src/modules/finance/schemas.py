from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class InterestGenerationRequest(BaseModel):
    as_of_date: date


class InterestChargeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    period_start: date
    period_end: date
    charge_date: date
    amount: float
    status: str
    penalty_amount: float | None = None
    penalty_rate_applied: float | None = None
    penalty_applied_at: date | None = None
    voided_at: datetime | None = None
    void_reason: str = ""
    created_at: datetime


class VoidInterestChargeRequest(BaseModel):
    """Voiding forgives interest that was already billed, so it has to be answerable.

    Same floor as a payment reversal and a forced close: three characters is not a real
    explanation, but it is enough to stop an empty string standing in for one.
    """

    reason: str = Field(..., min_length=3, max_length=500)


class LoanBalanceRead(BaseModel):
    loan_id: int
    principal_amount: float
    outstanding_principal: float
    total_interest_generated: float
    total_payments: float
