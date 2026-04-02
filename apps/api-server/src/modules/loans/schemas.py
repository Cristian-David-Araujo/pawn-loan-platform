from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from src.domain.enums.loan import LoanStatus, LoanType


class LoanApplicationCreate(BaseModel):
    customer_id: int
    loan_type: LoanType
    requested_amount: float
    monthly_interest_rate: float
    term_months: int
    notes: str = ""


class LoanApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    loan_type: LoanType
    requested_amount: float
    monthly_interest_rate: float
    term_months: int
    notes: str
    status: str
    reviewed_by: int | None
    approved_by: int | None
    created_at: datetime


class LoanCreate(BaseModel):
    application_id: int | None = None
    customer_id: int
    loan_type: LoanType
    principal_amount: float
    monthly_interest_rate: float
    late_penalty_rate: float = 0
    disbursement_date: date
    due_day: int


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int | None
    customer_id: int
    loan_type: LoanType
    principal_amount: float
    outstanding_principal: float
    monthly_interest_rate: float
    late_penalty_rate: float
    disbursement_date: date
    due_day: int
    status: LoanStatus
    renewal_of: int | None
    created_at: datetime


class LoanUpdate(BaseModel):
    monthly_interest_rate: float
    due_day: int
    status: LoanStatus


class RenewalRequest(BaseModel):
    monthly_interest_rate: float | None = None
    due_day: int | None = None


class CloseLoanRequest(BaseModel):
    force: bool = False
