from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


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
    created_at: datetime


class LoanBalanceRead(BaseModel):
    loan_id: int
    principal_amount: float
    outstanding_principal: float
    total_interest_generated: float
    total_payments: float
