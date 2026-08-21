from datetime import UTC, date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
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


class CustomerIdentityDocument(Base):
    """A scanned side of the identity document supplied for a customer.

    The file deliberately lives in the database instead of a container path: a document is
    part of the customer record, must be protected by the same authorisation as the record,
    and must survive the application's existing export/restore workflow.
    """

    __tablename__ = "customer_identity_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    # A scan records both physical sides separately. `combined` preserves a PDF or legacy
    # one-file upload without pretending the application knows which page is which.
    side: Mapped[str] = mapped_column(String(12), default="front")
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)

    __table_args__ = (UniqueConstraint("customer_id", "side", name="uq_customer_identity_documents_customer_side"),)



class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
    # Closing a loan that still owes money forgives that money. Same reasoning as a payment
    # reversal: the audit table has no read path in the application, so without these you
    # could see a debt had been written off but not by whom, when, or on what grounds.
    force_closed_reason: Mapped[str] = mapped_column(Text, default="")
    force_closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    force_closed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Pausing stops the clock without ending the debt, so it is a flag rather than a status:
    # a paused loan is still `active` or `overdue`, and resuming must return it to whichever
    # it was. Folding it into `LoanStatus` would have destroyed that distinction — and it is
    # a native PG enum, so it would also need a migration that alters the type.
    #
    # It suspends only what is still to come: no new interest is generated and no new penalty
    # is frozen. Interest already billed stays owed, stays visible in collection and can still
    # turn the loan `overdue`, because hiding arrears that exist is not what a pause is for.
    interest_paused: Mapped[bool] = mapped_column(default=False)
    interest_paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interest_paused_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    interest_pause_reason: Mapped[str] = mapped_column(Text, default="")
    # A negotiated settlement: the customer pays what they can and the rest is written off.
    # The loan closes as `closed` — the write-off is what these columns record, so a report
    # can tell a settlement from a normal payoff without inventing a fifth loan status.
    # Same reasoning as `force_closed_*`: money was forgiven, and somebody's name belongs on
    # that decision where the application can actually read it.
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    settled_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    settlement_reason: Mapped[str] = mapped_column(Text, default="")
    settlement_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    written_off_principal: Mapped[float | None] = mapped_column(Float, nullable=True)
    written_off_interest: Mapped[float | None] = mapped_column(Float, nullable=True)
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


class CollateralPhoto(Base):
    """A compressed evidence photo for one pledged item."""

    __tablename__ = "collateral_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    collateral_item_id: Mapped[int] = mapped_column(
        ForeignKey("collateral_items.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)


class InterestCharge(Base):
    __tablename__ = "interest_charges"
    # A loan can only ever owe one charge per billing period. Without this the interest
    # scheduler racing the manual endpoint produced duplicates that customers then paid.
    __table_args__ = (UniqueConstraint("loan_id", "period_start", "period_end", name="uq_interest_charge_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), index=True)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    charge_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Float)
    # The principal this period was billed on. `amount` is derived from the loan's balance
    # at the time the cycle runs, which is only the balance the period actually carried
    # while the cycle is on time; recording the base is what makes a backdated generation
    # auditable instead of a number nobody can reconstruct. NULL on rows that predate it.
    principal_base: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="generated")
    # The late penalty is a fact, not a formula. It used to be derived on every read from
    # the interest still pending, so it shrank as the customer paid and a change of
    # `default_grace_days` erased it from the whole portfolio retroactively. It is fixed
    # once, when the period falls due, and then it is history: NULL until that happens.
    penalty_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    penalty_rate_applied: Mapped[float | None] = mapped_column(Float, nullable=True)
    penalty_applied_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Voiding forgives interest that was already billed, so it is marked, never deleted —
    # the same choice payment reversal makes, and for the same reason: the row is the
    # evidence of what was charged and then given back, and the audit table has no read path
    # in the application. The period stays on record, which is also what stops the generator
    # from deciding to bill that month again on the next cycle.
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    voided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    void_reason: Mapped[str] = mapped_column(Text, default="")
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
    # One key, one payment. There is no other defence against a double-clicked submit: the
    # row lock stops two cashiers racing on the same balance, but not the same cashier sending
    # the same collection twice because the connection was slow and the button still looked
    # live. The client mints a key per attempt; a retry carries the same one and gets the
    # original payment back instead of taking the money again.
    #
    # Nullable, because every payment recorded before this has none and a unique index must
    # not treat them as duplicates of each other.
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
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
    # The product name. An operator can rename this from the settings screen — it is what
    # the sidebar, the login card and the printed footer show — but a fresh installation
    # should say what the product is called rather than a placeholder.
    app_name: Mapped[str] = mapped_column(String(100), default="Mutuum")
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
    # Days after a period ends before it counts as late. Global on purpose: it used to be
    # taken from the day-of-month of each disbursement, so a loan signed on the 25th got 25
    # days of grace and one signed on the 3rd got three.
    default_grace_days: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class BackupSettings(Base):
    """Single row (``id=1``) holding the recurring backup schedule and its destination.

    Deliberately not part of ``GlobalSettings``: ``GET /settings`` is readable by every
    authenticated role, and these columns carry the OAuth client secret and refresh token of
    the Google account the archives land in. They live behind the admin-only ``/backup/*``
    routes and are never returned by the API — the schedule response reports whether a
    credential is present, never its value.
    """

    __tablename__ = "backup_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(default=False)
    # daily | weekly | monthly
    frequency: Mapped[str] = mapped_column(String(20), default="daily")
    # Local hour (GlobalSettings.timezone) the copy is taken at, outside business hours.
    hour: Mapped[int] = mapped_column(Integer, default=2)
    # 1 = Monday .. 7 = Sunday. Read only when frequency is weekly.
    day_of_week: Mapped[int] = mapped_column(Integer, default=1)
    # Capped at 28 so every month has the day. Read only when frequency is monthly.
    day_of_month: Mapped[int] = mapped_column(Integer, default=1)
    # local_directory | google_drive
    destination: Mapped[str] = mapped_column(String(30), default="local_directory")
    local_directory: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Copies to keep at the destination; 0 keeps everything.
    retention_copies: Mapped[int] = mapped_column(Integer, default=7)
    drive_client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_client_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Shown in the UI so the administrator can tell which Google account is connected.
    drive_account_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # New installations only. Existing rows are deliberately left alone by the rename
    # migration: this name is paired with drive_folder_id, and changing one without the
    # other would leave the screen naming a folder the uploads do not go to.
    drive_folder_name: Mapped[str] = mapped_column(String(255), default="Mutuum Backups")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)


class BackupRun(Base):
    """One attempt at a backup, successful or not.

    This table is the only record of whether the schedule is actually working: an operator
    reads "the last copy succeeded 9 days ago" from here. There is no denormalised
    ``last_status`` on ``BackupSettings`` on purpose — a cache of this would be one more thing
    that can disagree with what happened.
    """

    __tablename__ = "backup_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # success | failed
    status: Mapped[str] = mapped_column(String(20), default="success")
    # scheduled | manual
    trigger: Mapped[str] = mapped_column(String(20), default="scheduled")
    destination: Mapped[str] = mapped_column(String(30), default="local_directory")
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Where the copy ended up: an absolute path, or the Google Drive file id.
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Whole message, so a failure can be diagnosed without server access.
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
