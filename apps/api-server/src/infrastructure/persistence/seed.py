from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus, LoanType
from src.infrastructure.persistence.models import (
    CollateralItem,
    Customer,
    InterestCharge,
    Loan,
    LoanApplication,
    Payment,
    User,
)
from src.infrastructure.security.password import get_password_hash


def seed_database(db: Session, force: bool = False) -> bool:
    """Seed development data. Returns True when seeding is applied."""
    has_customers = db.scalar(select(Customer.id).limit(1)) is not None
    if has_customers and not force:
        return False

    if force:
        db.query(InterestCharge).delete()
        db.query(Payment).delete()
        db.query(CollateralItem).delete()
        db.query(Loan).delete()
        db.query(LoanApplication).delete()
        db.query(Customer).delete()

    users = _ensure_users(db)

    customer_1 = Customer(
        first_name="Ana",
        last_name="Torres",
        document_type="ID",
        document_number="AT-1001",
        phone="555-1001",
        email="ana.torres@example.com",
        address="Street 100",
        city="Monterrey",
        status="active",
    )
    customer_2 = Customer(
        first_name="Luis",
        last_name="Medina",
        document_type="ID",
        document_number="LM-2001",
        phone="555-2001",
        email="luis.medina@example.com",
        address="Street 200",
        city="Guadalajara",
        status="active",
    )
    customer_3 = Customer(
        first_name="Carla",
        last_name="Ramos",
        document_type="ID",
        document_number="CR-3001",
        phone="555-3001",
        email="carla.ramos@example.com",
        address="Street 300",
        city="CDMX",
        status="active",
    )
    db.add_all([customer_1, customer_2, customer_3])
    db.flush()

    app_1 = LoanApplication(
        customer_id=customer_1.id,
        loan_type=LoanType.pawn,
        requested_amount=1500,
        monthly_interest_rate=8,
        term_months=3,
        notes="Gold jewelry collateral",
        status="approved",
        reviewed_by=users["officer"].id,
        approved_by=users["officer"].id,
    )
    app_2 = LoanApplication(
        customer_id=customer_2.id,
        loan_type=LoanType.personal,
        requested_amount=1000,
        monthly_interest_rate=7,
        term_months=4,
        notes="Personal credit",
        status="approved",
        reviewed_by=users["officer"].id,
        approved_by=users["officer"].id,
    )
    db.add_all([app_1, app_2])
    db.flush()

    today = date.today()

    loan_1 = Loan(
        application_id=app_1.id,
        customer_id=customer_1.id,
        loan_type=LoanType.pawn,
        principal_amount=1500,
        outstanding_principal=1200,
        monthly_interest_rate=8,
        disbursement_date=today - timedelta(days=45),
        due_day=5,
        status=LoanStatus.active,
    )
    loan_2 = Loan(
        application_id=app_2.id,
        customer_id=customer_2.id,
        loan_type=LoanType.personal,
        principal_amount=1000,
        outstanding_principal=950,
        monthly_interest_rate=7,
        disbursement_date=today - timedelta(days=65),
        due_day=20,
        status=LoanStatus.overdue,
    )
    loan_3 = Loan(
        customer_id=customer_3.id,
        loan_type=LoanType.personal,
        principal_amount=700,
        outstanding_principal=0,
        monthly_interest_rate=6,
        disbursement_date=today - timedelta(days=120),
        due_day=10,
        status=LoanStatus.closed,
    )
    db.add_all([loan_1, loan_2, loan_3])
    db.flush()

    collateral = CollateralItem(
        loan_id=loan_1.id,
        item_type="jewelry",
        description="Gold chain 14k",
        serial_number="GOLD-14K-001",
        appraised_value=2200,
        physical_condition="good",
        custody_code="CUST-1001",
        storage_location="Vault A-01",
        status="in_custody",
    )

    payment_1 = Payment(
        loan_id=loan_1.id,
        payment_date=today - timedelta(days=10),
        total_amount=320,
        allocated_to_penalty=0,
        allocated_to_interest=90,
        allocated_to_fees=30,
        allocated_to_principal=200,
        payment_method="cash",
        received_by=users["cashier"].id,
    )
    payment_2 = Payment(
        loan_id=loan_2.id,
        payment_date=today - timedelta(days=5),
        total_amount=150,
        allocated_to_penalty=20,
        allocated_to_interest=60,
        allocated_to_fees=10,
        allocated_to_principal=60,
        payment_method="bank-transfer",
        received_by=users["cashier"].id,
    )

    interest_1 = InterestCharge(
        loan_id=loan_1.id,
        period_start=today - timedelta(days=30),
        period_end=today,
        charge_date=today,
        amount=96,
        status="generated",
    )
    interest_2 = InterestCharge(
        loan_id=loan_2.id,
        period_start=today - timedelta(days=30),
        period_end=today,
        charge_date=today,
        amount=66.5,
        status="generated",
    )

    db.add_all([collateral, payment_1, payment_2, interest_1, interest_2])
    db.commit()
    return True


def _ensure_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    required_users = {
        "officer": ("officer", "officer123", "loan_officer"),
        "cashier": ("cashier", "cashier123", "cashier"),
        "auditor": ("auditor", "auditor123", "auditor"),
    }

    for key, (username, password, role) in required_users.items():
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            user = User(
                username=username,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            )
            db.add(user)
            db.flush()
        users[key] = user

    return users
