import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, Date, DateTime, Enum, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    OTHER = "other"


class PaymentStatus(str, enum.Enum):
    COMPLETED = "completed"
    REVERSED = "reversed"
    PENDING = "pending"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    loan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    payment_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    allocated_to_penalty = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    allocated_to_interest = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    allocated_to_fees = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    allocated_to_principal = Column(Numeric(15, 2), default=Decimal("0"), nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    received_by = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.COMPLETED, nullable=False)
    reversal_reason = Column(Text, nullable=True)
    reversed_by = Column(UUID(as_uuid=True), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
