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
