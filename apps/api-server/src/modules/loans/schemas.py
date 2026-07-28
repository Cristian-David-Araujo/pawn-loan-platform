from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from src.domain.enums.loan import LoanStatus, LoanType
from src.modules.authentication.schemas import UserSummary


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
    created_by: UserSummary | None = None


class LoanCreate(BaseModel):
    application_id: int | None = None
    customer_id: int
    loan_type: LoanType
    description: str = ""
    principal_amount: float
    monthly_interest_rate: float
    late_penalty_rate: float = 0
    disbursement_date: date
    # Grace days come from GlobalSettings; accepted for compatibility, ignored on write.
    due_day: int | None = None


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int | None
    customer_id: int
    loan_type: LoanType
    description: str
    principal_amount: float
    outstanding_principal: float
    monthly_interest_rate: float
    interest_due: float | None = None
    collaterals_count: int | None = None
    late_penalty_rate: float
    disbursement_date: date
    due_day: int
    status: LoanStatus
    renewal_of: int | None
    created_at: datetime
    created_by: UserSummary | None = None


class LoanUpdate(BaseModel):
    loan_type: LoanType | None = None
    description: str | None = None
    principal_amount: float | None = None
    outstanding_principal: float | None = None
    monthly_interest_rate: float | None = None
    late_penalty_rate: float | None = None
    disbursement_date: date | None = None
    due_day: int | None = None
    # Optional so an edit can carry only what changed: a required rate and status meant
    # every form submit resent the whole loan and triggered a full charge recalculation.
    status: LoanStatus | None = None


class RenewalRequest(BaseModel):
    monthly_interest_rate: float | None = None
    due_day: int | None = None


class CloseLoanRequest(BaseModel):
    force: bool = False
