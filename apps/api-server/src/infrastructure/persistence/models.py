from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.domain.enums.loan import LoanStatus, LoanType
from src.infrastructure.persistence.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="loan_officer")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    document_type: Mapped[str] = mapped_column(String(20))
    document_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    city: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType))
    requested_amount: Mapped[float] = mapped_column(Float)
    monthly_interest_rate: Mapped[float] = mapped_column(Float)
    term_months: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="submitted")
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("loan_applications.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType))
    principal_amount: Mapped[float] = mapped_column(Float)
    outstanding_principal: Mapped[float] = mapped_column(Float)
    monthly_interest_rate: Mapped[float] = mapped_column(Float)
    disbursement_date: Mapped[date] = mapped_column(Date)
    due_day: Mapped[int] = mapped_column(Integer)
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), default=LoanStatus.active)
    renewal_of: Mapped[int | None] = mapped_column(ForeignKey("loans.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CollateralItem(Base):
    __tablename__ = "collateral_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(80), default="general")
    description: Mapped[str] = mapped_column(String(255))
    serial_number: Mapped[str] = mapped_column(String(80), default="")
    appraised_value: Mapped[float] = mapped_column(Float)
    physical_condition: Mapped[str] = mapped_column(String(120), default="good")
    custody_code: Mapped[str] = mapped_column(String(40), unique=True)
    storage_location: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default="in_custody")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InterestCharge(Base):
    __tablename__ = "interest_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    charge_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date)
    total_amount: Mapped[float] = mapped_column(Float)
    allocated_to_penalty: Mapped[float] = mapped_column(Float, default=0)
    allocated_to_interest: Mapped[float] = mapped_column(Float, default=0)
    allocated_to_fees: Mapped[float] = mapped_column(Float, default=0)
    allocated_to_principal: Mapped[float] = mapped_column(Float, default=0)
    payment_method: Mapped[str] = mapped_column(String(40), default="cash")
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_reversed: Mapped[bool] = mapped_column(default=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    old_data: Mapped[str] = mapped_column(Text, default="")
    new_data: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
