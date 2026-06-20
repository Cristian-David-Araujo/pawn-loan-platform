from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CollateralCreate(BaseModel):
    loan_id: int
    item_type: str = "general"
    description: str
    serial_number: str = ""
    appraised_value: float
    physical_condition: str = "good"
    storage_location: str = ""


class CollateralUpdate(BaseModel):
    loan_id: int
    description: str
    appraised_value: float
    storage_location: str
    status: str


class CollateralRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    loan_id: int
    item_type: str
    description: str
    serial_number: str
    appraised_value: float
    physical_condition: str
    custody_code: str
    storage_location: str
    status: str
    loan_status: str | None = None
    sale_price: float | None = None
    sold_at: datetime | None = None
    created_at: datetime

class CollateralSell(BaseModel):
    sale_price: float
    notes: str | None = ""
