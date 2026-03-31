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
    created_at: datetime
