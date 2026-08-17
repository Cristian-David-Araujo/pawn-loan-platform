from datetime import datetime

from src.domain.enums.collateral import CollateralStatus
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
    # Accepted so a client can round-trip the item it loaded, but it may only carry the
    # status the pledge already has: custody moves through the dedicated endpoints, which
    # are the ones that check the debt first.
    status: CollateralStatus | None = None


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
    status: CollateralStatus = CollateralStatus.in_custody
    loan_status: str | None = None
    loan_principal: float | None = None
    loan_outstanding: float | None = None
    loan_interest_due: float | None = None
    loan_rate: float | None = None
    sale_price: float | None = None
    sold_at: datetime | None = None
    created_at: datetime

class CollateralSell(BaseModel):
    sale_price: float
    notes: str | None = ""
