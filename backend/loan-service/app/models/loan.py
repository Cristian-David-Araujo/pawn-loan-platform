import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class LoanType(str, enum.Enum):
    PAWN = "pawn"
    PERSONAL = "personal"


class LoanApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LoanStatus(str, enum.Enum):
    APPROVED = "approved"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    OVERDUE = "overdue"
    RENEWED = "renewed"
    CLOSED = "closed"
    DEFAULTED = "defaulted"
    LIQUIDATED = "liquidated"


class DisbursementMethod(str, enum.Enum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    loan_type = Column(Enum(LoanType), nullable=False)
    requested_amount = Column(Numeric(15, 2), nullable=False)
    monthly_interest_rate = Column(Numeric(5, 4), nullable=False)
    term_months = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(Enum(LoanApplicationStatus), default=LoanApplicationStatus.DRAFT, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    loans = relationship("Loan", back_populates="application")


class Loan(Base):
    __tablename__ = "loans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    loan_type = Column(Enum(LoanType), nullable=False)
    principal_amount = Column(Numeric(15, 2), nullable=False)
    outstanding_principal = Column(Numeric(15, 2), nullable=False)
    monthly_interest_rate = Column(Numeric(5, 4), nullable=False)
    disbursement_date = Column(DateTime(timezone=True), nullable=True)
    due_day = Column(Integer, nullable=False, default=1)
    term_months = Column(Integer, nullable=False)
    disbursement_method = Column(Enum(DisbursementMethod), nullable=True)
    status = Column(Enum(LoanStatus), default=LoanStatus.APPROVED, nullable=False)
    renewal_of = Column(UUID(as_uuid=True), ForeignKey("loans.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    application = relationship("LoanApplication", back_populates="loans")
    renewal_source = relationship("Loan", remote_side=[id])
