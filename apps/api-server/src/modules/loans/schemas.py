from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

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
    # Exposed so a written-off loan can say so on screen instead of just reading as closed.
    force_closed_reason: str = ""
    force_closed_at: datetime | None = None
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
    """Closing over an outstanding balance writes the rest off, so it has to be answerable.

    Same shape as a payment reversal: the grounds are mandatory and they travel with the row,
    not only into an audit table nothing in the application reads back.
    """

    force: bool = False
    reason: str | None = Field(default=None, min_length=3, max_length=500)
