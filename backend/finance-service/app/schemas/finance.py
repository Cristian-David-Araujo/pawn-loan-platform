from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.finance import ChargeStatus, PenaltyStatus


class InterestGenerateRequest(BaseModel):
    loan_id: UUID
    principal_base: Decimal
    interest_rate: Decimal
    period_start: date
    period_end: date
    charge_date: date


class InterestChargeRead(BaseModel):
    id: UUID
    loan_id: UUID
    period_start: date
    period_end: date
    charge_date: date
    principal_base: Decimal
    interest_rate: Decimal
    amount: Decimal
    status: ChargeStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class PenaltyChargeCreate(BaseModel):
    loan_id: UUID
    charge_date: date
    amount: Decimal
    reason: Optional[str] = None


class PenaltyChargeRead(BaseModel):
    id: UUID
    loan_id: UUID
    charge_date: date
    amount: Decimal
    reason: Optional[str] = None
    status: PenaltyStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanBalanceResponse(BaseModel):
    loan_id: UUID
    total_pending_interest: Decimal
    total_pending_penalties: Decimal
    total_outstanding: Decimal
