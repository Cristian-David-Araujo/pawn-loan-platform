from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.collateral import CollateralStatus


class CollateralItemCreate(BaseModel):
    loan_id: UUID
    item_type: str
    description: str
    serial_number: Optional[str] = None
    appraised_value: Decimal
    physical_condition: Optional[str] = None
    custody_code: Optional[str] = None
    storage_location: Optional[str] = None


class CollateralItemUpdate(BaseModel):
    description: Optional[str] = None
    serial_number: Optional[str] = None
    appraised_value: Optional[Decimal] = None
    physical_condition: Optional[str] = None
    storage_location: Optional[str] = None
    status: Optional[CollateralStatus] = None


class CollateralItemRead(BaseModel):
    id: UUID
    loan_id: UUID
    item_type: str
    description: str
    serial_number: Optional[str] = None
    appraised_value: Decimal
    physical_condition: Optional[str] = None
    custody_code: Optional[str] = None
    storage_location: Optional[str] = None
    status: CollateralStatus
    release_date: Optional[datetime] = None
    released_by: Optional[UUID] = None
    sale_amount: Optional[Decimal] = None
    liquidation_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReleaseRequest(BaseModel):
    released_by: Optional[UUID] = None
    notes: Optional[str] = None


class LiquidateRequest(BaseModel):
    sale_amount: Optional[Decimal] = None
    notes: Optional[str] = None
