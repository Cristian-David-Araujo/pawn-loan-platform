from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.enums.loan import LoanStatus, LoanType
from src.domain.enums.user import UserRole
from src.infrastructure.persistence.database import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(120), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    document_number: Mapped[str] = mapped_column(String(40), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, native_enum=False, length=50), default=UserRole.loan_officer)
    is_active: Mapped[bool] = mapped_column(default=True)
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reset_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


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
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
    
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("loan_applications.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    loan_type: Mapped[LoanType] = mapped_column(Enum(LoanType))
    description: Mapped[str] = mapped_column(Text, default="")
    principal_amount: Mapped[float] = mapped_column(Float)
    outstanding_principal: Mapped[float] = mapped_column(Float)
    monthly_interest_rate: Mapped[float] = mapped_column(Float)
    late_penalty_rate: Mapped[float] = mapped_column(Float, default=0)
    disbursement_date: Mapped[date] = mapped_column(Date)
    due_day: Mapped[int] = mapped_column(Integer)
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), default=LoanStatus.active)
    renewal_of: Mapped[int | None] = mapped_column(ForeignKey("loans.id"), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], lazy="selectin")

    @property
    def interest_due(self) -> float:
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if not session:
            return 0.0

        # Delegated so listings and collection screens share one calculation.
        from src.infrastructure.utils.datetime_utils import get_local_date
        from src.modules.finance.interest_balance import pending_interest_total_for_loan

        return pending_interest_total_for_loan(session, self, get_local_date(session))

    @property
    def collaterals_count(self) -> int:
        from sqlalchemy.orm import object_session
        from sqlalchemy import select, func
        session = object_session(self)
        if not session:
            return 0
            
        return session.scalar(
            select(func.count(CollateralItem.id))
            .where(CollateralItem.loan_id == self.id)
        ) or 0


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
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    
    loan: Mapped["Loan"] = relationship("Loan", lazy="selectin")

    @property
    def loan_status(self) -> str | None:
        if self.loan and hasattr(self.loan, 'status'):
            return self.loan.status.value
        return None

    @property
    def loan_principal(self) -> float | None:
        if self.loan and hasattr(self.loan, 'principal_amount'):
            return self.loan.principal_amount
        return None

    @property
    def loan_outstanding(self) -> float | None:
        if self.loan and hasattr(self.loan, 'outstanding_principal'):
            return self.loan.outstanding_principal
        return None

    @property
    def loan_rate(self) -> float | None:
        if self.loan and hasattr(self.loan, 'monthly_interest_rate'):
            return self.loan.monthly_interest_rate
        return None

    @property
    def loan_interest_due(self) -> float | None:
        if not self.loan_id or self.loan is None:
            return None
        from sqlalchemy.orm import object_session
        session = object_session(self)
        if not session:
            return None

        from src.infrastructure.utils.datetime_utils import get_local_date
        from src.modules.finance.interest_balance import pending_interest_total_for_loan

        return pending_interest_total_for_loan(session, self.loan, get_local_date(session))


class InterestCharge(Base):
    __tablename__ = "interest_charges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    charge_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


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
    notes: Mapped[str] = mapped_column(Text, default="")
    received_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_reversed: Mapped[bool] = mapped_column(default=False)
    # Reversal is how a payment gets "deleted", so who/when/why lives on the row itself
    # rather than only in the audit log, which has no read path in the application.
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reversal_reason: Mapped[str] = mapped_column(Text, default="")

    receiver: Mapped["User"] = relationship("User", foreign_keys=[received_by], lazy="selectin")
    reverser: Mapped["User"] = relationship("User", foreign_keys=[reversed_by], lazy="selectin")


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    payment_type: Mapped[str] = mapped_column(String(60), index=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    interest_charge_id: Mapped[int | None] = mapped_column(ForeignKey("interest_charges.id"), nullable=True)
    billing_period: Mapped[str] = mapped_column(String(30), default="")
    total_entered_amount: Mapped[float] = mapped_column(Float)
    allocated_to_interest: Mapped[float] = mapped_column(Float, default=0)
    allocated_to_penalty: Mapped[float] = mapped_column(Float, default=0)
    allocated_to_principal: Mapped[float] = mapped_column(Float, default=0)
    payment_date: Mapped[date] = mapped_column(Date)
    operator_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    payment_method: Mapped[str] = mapped_column(String(40), default="cash")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_reversed: Mapped[bool] = mapped_column(default=False)
    audit_timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    
    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_user_id], lazy="selectin")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(80))
    old_data: Mapped[str] = mapped_column(Text, default="")
    new_data: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class GlobalSettings(Base):
    __tablename__ = "global_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    app_name: Mapped[str] = mapped_column(String(100), default="PawnPlatform")
    company_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    company_document_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company_document_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency_code: Mapped[str] = mapped_column(String(3), default="COP")
    timezone: Mapped[str] = mapped_column(String(80), default="America/Bogota")
    date_format: Mapped[str] = mapped_column(String(20), default="DD/MM/YYYY")
    default_late_penalty_rate: Mapped[float] = mapped_column(Float, default=0)
    interest_generation_lead_days: Mapped[int] = mapped_column(Integer, default=10)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
