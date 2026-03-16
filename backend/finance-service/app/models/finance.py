import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ChargeStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"
    OVERDUE = "overdue"


class PenaltyStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    WAIVED = "waived"


class InterestCharge(Base):
    __tablename__ = "interest_charges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    charge_date = Column(Date, nullable=False)
    principal_base = Column(Numeric(15, 2), nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(Enum(ChargeStatus), default=ChargeStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class PenaltyCharge(Base):
    __tablename__ = "penalty_charges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    charge_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    reason = Column(String(255), nullable=True)
    status = Column(Enum(PenaltyStatus), default=PenaltyStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
