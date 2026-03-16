from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.payment import PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    loan_id: UUID
    payment_date: date
    total_amount: Decimal
    allocated_to_penalty: Decimal = Decimal("0")
    allocated_to_interest: Decimal = Decimal("0")
    allocated_to_fees: Decimal = Decimal("0")
    allocated_to_principal: Decimal = Decimal("0")
    payment_method: PaymentMethod
    received_by: Optional[UUID] = None
    notes: Optional[str] = None

    @field_validator("total_amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Payment amount must be positive")
        return v


class PaymentRead(BaseModel):
    id: UUID
    loan_id: UUID
    payment_date: date
    total_amount: Decimal
    allocated_to_penalty: Decimal
    allocated_to_interest: Decimal
    allocated_to_fees: Decimal
    allocated_to_principal: Decimal
    payment_method: PaymentMethod
    received_by: Optional[UUID] = None
    status: PaymentStatus
    reversal_reason: Optional[str] = None
    reversed_by: Optional[UUID] = None
    reversed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReversalRequest(BaseModel):
    reason: str
    reversed_by: Optional[UUID] = None


class PaymentListResponse(BaseModel):
    items: List[PaymentRead]
    total: int
    skip: int
    limit: int
