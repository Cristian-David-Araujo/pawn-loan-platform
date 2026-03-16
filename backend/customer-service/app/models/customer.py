import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DocumentType(str, enum.Enum):
    CC = "CC"
    CE = "CE"
    PASSPORT = "PASSPORT"
    NIT = "NIT"
    OTHER = "OTHER"


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    document_number = Column(String(50), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(CustomerStatus), default=CustomerStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
