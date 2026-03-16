from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.loan import DisbursementMethod, LoanApplicationStatus, LoanStatus, LoanType


class LoanApplicationCreate(BaseModel):
    customer_id: UUID
    loan_type: LoanType
    requested_amount: Decimal
    monthly_interest_rate: Decimal
    term_months: int
    notes: Optional[str] = None

    @field_validator("requested_amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Requested amount must be positive")
        return v

    @field_validator("monthly_interest_rate")
    @classmethod
    def rate_valid(cls, v: Decimal) -> Decimal:
        if v <= 0 or v > 1:
            raise ValueError("Monthly interest rate must be between 0 and 1 (e.g. 0.05 for 5%)")
        return v

    @field_validator("term_months")
    @classmethod
    def term_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Term must be positive")
        return v


class LoanApplicationUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[LoanApplicationStatus] = None
    rejection_reason: Optional[str] = None


class LoanApplicationRead(BaseModel):
    id: UUID
    customer_id: UUID
    loan_type: LoanType
    requested_amount: Decimal
    monthly_interest_rate: Decimal
    term_months: int
    notes: Optional[str] = None
    status: LoanApplicationStatus
    created_by: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    approved_by: Optional[UUID] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoanCreate(BaseModel):
    application_id: UUID
    principal_amount: Decimal
    monthly_interest_rate: Decimal
    disbursement_date: datetime
    due_day: int = 1
    term_months: int
    disbursement_method: DisbursementMethod = DisbursementMethod.CASH
    notes: Optional[str] = None

    @field_validator("due_day")
    @classmethod
    def due_day_valid(cls, v: int) -> int:
        if v < 1 or v > 28:
            raise ValueError("Due day must be between 1 and 28")
        return v


class LoanRead(BaseModel):
    id: UUID
    application_id: UUID
    customer_id: UUID
    loan_type: LoanType
    principal_amount: Decimal
    outstanding_principal: Decimal
    monthly_interest_rate: Decimal
    disbursement_date: Optional[datetime] = None
    due_day: int
    term_months: int
    disbursement_method: Optional[DisbursementMethod] = None
    status: LoanStatus
    renewal_of: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoanListResponse(BaseModel):
    items: List[LoanRead]
    total: int
    skip: int
    limit: int


class ApplicationListResponse(BaseModel):
    items: List[LoanApplicationRead]
    total: int
    skip: int
    limit: int
