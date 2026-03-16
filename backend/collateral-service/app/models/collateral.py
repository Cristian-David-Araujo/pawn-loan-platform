import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class CollateralStatus(str, enum.Enum):
    RECEIVED = "received"
    IN_CUSTODY = "in_custody"
    RELEASED = "released"
    UNDER_LIQUIDATION = "under_liquidation"
    SOLD = "sold"
    WRITTEN_OFF = "written_off"


class CollateralItem(Base):
    __tablename__ = "collateral_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    serial_number = Column(String(100), nullable=True)
    appraised_value = Column(Numeric(15, 2), nullable=False)
    physical_condition = Column(String(100), nullable=True)
    custody_code = Column(String(50), unique=True, nullable=True, index=True)
    storage_location = Column(String(255), nullable=True)
    status = Column(Enum(CollateralStatus), default=CollateralStatus.RECEIVED, nullable=False)
    release_date = Column(DateTime(timezone=True), nullable=True)
    released_by = Column(UUID(as_uuid=True), nullable=True)
    sale_amount = Column(Numeric(15, 2), nullable=True)
    liquidation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
