import random
from datetime import date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus, LoanType
from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import (
    CollateralItem,
    Customer,
    GlobalSettings,
    InterestCharge,
    Loan,
    LoanApplication,
    Payment,
    PaymentEvent,
    User,
)
from src.infrastructure.security.password import get_password_hash
from src.infrastructure.utils.datetime_utils import get_local_date


NAMES = ["Juan", "Maria", "Carlos", "Ana", "Luis", "Laura", "Pedro", "Sofia", "Diego", "Carmen", "Javier", "Isabel", "Jose", "Marta", "Miguel", "Lucia", "Andres", "Elena", "Fernando", "Patricia"]
LAST_NAMES = ["Garcia", "Martinez", "Rodriguez", "Lopez", "Hernandez", "Gonzalez", "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera", "Gomez", "Diaz", "Cruz", "Reyes", "Morales", "Ortiz"]
CITIES = ["CDMX", "Guadalajara", "Monterrey", "Puebla", "Tijuana", "Toluca", "Merida", "Cancun", "Queretaro", "Aguascalientes"]

ITEMS = [
    ("electronics", "Smart TV Samsung 55 4K", 450),
    ("electronics", "Nintendo Switch OLED", 250),
    ("electronics", "PlayStation 5", 400),
    ("jewelry", "Anillo de Oro 18k", 300),
    ("jewelry", "Cadena de Plata 925", 150),
    ("electronics", "iPhone 13 Pro 128GB", 600),
    ("electronics", "Laptop Dell XPS 13", 800),
    ("vehicles", "Bicicleta de Montaña Trek", 500),
    ("jewelry", "Reloj Rolex Vintage", 1500),
    ("tools", "Taladro Inalambrico DeWalt", 120),
    ("electronics", "iPad Air 5th Gen", 450),
    ("vehicles", "Motocicleta Italika 150cc", 900),
]

def seed_database(db: Session, force: bool = False) -> bool:
    """Seed development data. Returns True when seeding is applied."""
    has_customers = db.scalar(select(Customer.id).limit(1)) is not None
    if has_customers and not force:
        return False

    if force:
        db.query(PaymentEvent).delete()
        db.query(InterestCharge).delete()
        db.query(Payment).delete()
        db.query(CollateralItem).delete()
        db.query(Loan).delete()
        db.query(LoanApplication).delete()
        db.query(Customer).delete()
        db.query(GlobalSettings).delete()

    users = _ensure_users(db)

    if db.get(GlobalSettings, 1) is None:
        db.add(
            GlobalSettings(
                id=1,
                currency_code="COP",
                timezone="America/Bogota",
                date_format="DD/MM/YYYY",
                default_late_penalty_rate=2,
                interest_generation_lead_days=10,
            )
        )
        db.flush()

    today = get_local_date(db)
    random.seed(42)  # Deterministic seed

    # 1. Generate 20 Customers
    customers = []
    for i in range(1, 21):
        c = Customer(
            first_name=random.choice(NAMES),
            last_name=f"{random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}",
            document_type="ID",
            document_number=f"DOC-{10000+i}",
            phone=f"555-{random.randint(1000, 9999)}",
            email=f"user{i}@example.com",
            address=f"Calle {random.randint(1, 100)}",
            city=random.choice(CITIES),
            status="active" if random.random() > 0.1 else "inactive",
        )
        db.add(c)
        customers.append(c)
    db.flush()

    # 2. Generate 60 Loans
    for i in range(1, 61):
        customer = random.choice(customers)
        is_pawn = random.random() > 0.3  # 70% Pawn, 30% Personal
        loan_type = LoanType.pawn if is_pawn else LoanType.personal
        
        principal = random.choice([500, 800, 1000, 1500, 2000, 3000, 5000])
        interest_rate = random.choice([5, 6, 7, 8, 10])
        term = random.choice([3, 6, 9, 12])
        
        # Application
        app = LoanApplication(
            customer_id=customer.id,
            loan_type=loan_type,
            requested_amount=principal,
            monthly_interest_rate=interest_rate,
            term_months=term,
            notes=f"Solicitud generada auto {i}",
            status="approved",
            reviewed_by=users["officer"].id,
            approved_by=users["officer"].id,
        )
        db.add(app)
        db.flush()

        # Decide status
        rand_status = random.random()
        if rand_status < 0.4:
            status = LoanStatus.active
            days_ago = random.randint(5, 60)
        elif rand_status < 0.6:
            status = LoanStatus.overdue
            days_ago = random.randint(45, 120)
        elif rand_status < 0.8:
            # Defaulted ONLY for pawn, else overdue
            status = LoanStatus.defaulted if is_pawn else LoanStatus.overdue
            days_ago = random.randint(90, 150)
        else:
            status = LoanStatus.closed
            days_ago = random.randint(100, 300)

        disbursement_date = today - timedelta(days=days_ago)

        # Build Loan
        loan = Loan(
            application_id=app.id,
            customer_id=customer.id,
            loan_type=loan_type,
            description=f"Prestamo {loan_type} autogenerado #{i}",
            principal_amount=principal,
            outstanding_principal=principal if status != LoanStatus.closed else 0,
            monthly_interest_rate=interest_rate,
            late_penalty_rate=2,
            disbursement_date=disbursement_date,
            due_day=disbursement_date.day if disbursement_date.day <= 28 else 28,
            status=status,
        )
        db.add(loan)
        db.flush()

        # Collateral
        item_cat, item_desc, item_val = random.choice(ITEMS)
        # Scale value based on principal (rough approximation)
        scaled_val = principal * random.uniform(1.2, 1.8)
        
        if is_pawn:
            c_status = "in_custody"
            if status == LoanStatus.defaulted:
                c_status = "for_sale"
            elif status == LoanStatus.closed:
                # 50% sold, 50% returned
                c_status = random.choice(["sold", "returned"])

            collateral = CollateralItem(
                loan_id=loan.id,
                item_type=item_cat,
                description=item_desc,
                serial_number=f"SN-{random.randint(1000, 9999)}",
                appraised_value=round(scaled_val, 2),
                physical_condition="good",
                custody_code=f"CUST-{1000+i}",
                storage_location=f"Rack {random.choice(['A','B','C'])}-{random.randint(1,20)}",
                status=c_status,
                sale_price=round(scaled_val * 0.8, 2) if c_status == "sold" else None,
                sold_at=today - timedelta(days=random.randint(1, 10)) if c_status == "sold" else None,
            )
            db.add(collateral)
            db.flush()

            # If closed via sale, add payment event
            if c_status == "sold":
                payment = Payment(
                    loan_id=loan.id,
                    payment_date=collateral.sold_at,
                    total_amount=collateral.sale_price,
                    allocated_to_penalty=0,
                    allocated_to_interest=0,
                    allocated_to_fees=max(0, collateral.sale_price - principal),
                    allocated_to_principal=principal,
                    payment_method="collateral_sale",
                    notes="Venta de remate",
                    received_by=users["collector"].id,
                )
                db.add(payment)
                db.flush()
                pe = PaymentEvent(
                    payment_type="collateral_sale",
                    payment_id=payment.id,
                    loan_id=loan.id,
                    total_entered_amount=collateral.sale_price,
                    allocated_to_principal=principal,
                    payment_date=payment.payment_date,
                    operator_user_id=users["collector"].id,
                    payment_method="collateral_sale",
                    notes="Venta de remate"
                )
                db.add(pe)
                db.flush()

        # Generate History (Interest Charges & Partial Payments)
        months_passed = days_ago // 30
        for m in range(months_passed):
            period_start = disbursement_date + timedelta(days=m*30)
            charge_date = period_start + timedelta(days=30)
            
            amt = round(principal * (interest_rate / 100), 2)
            ic = InterestCharge(
                loan_id=loan.id,
                period_start=period_start,
                period_end=charge_date,
                charge_date=charge_date,
                amount=amt,
                status="generated",
            )
            db.add(ic)
            db.flush()

            # If it's an active or closed loan, they probably paid it
            if status in [LoanStatus.active, LoanStatus.closed] or (status == LoanStatus.overdue and m < months_passed - 1):
                p_date = charge_date + timedelta(days=random.randint(0, 5))
                payment = Payment(
                    loan_id=loan.id,
                    payment_date=p_date,
                    total_amount=amt,
                    allocated_to_penalty=0,
                    allocated_to_interest=amt,
                    allocated_to_fees=0,
                    allocated_to_principal=0,
                    payment_method="cash",
                    notes=f"Pago interes mes {m+1}",
                    received_by=users["collector"].id,
                )
                db.add(payment)
                db.flush()
                pe = PaymentEvent(
                    payment_type="mixed_payment",
                    payment_id=payment.id,
                    loan_id=loan.id,
                    interest_charge_id=ic.id,
                    billing_period=ic.period_start.strftime("%Y-%m"),
                    total_entered_amount=amt,
                    allocated_to_interest=amt,
                    allocated_to_penalty=0,
                    allocated_to_principal=0,
                    payment_date=payment.payment_date,
                    operator_user_id=users["collector"].id,
                    payment_method="cash",
                    notes=payment.notes
                )
                db.add(pe)
                db.flush()

        # If it's a closed loan, and not closed by sale, we need a final payment
        if status == LoanStatus.closed and (not is_pawn or collateral.status != "sold"):
            p_date = today - timedelta(days=random.randint(1, 10))
            payment = Payment(
                loan_id=loan.id,
                payment_date=p_date,
                total_amount=principal,
                allocated_to_penalty=0,
                allocated_to_interest=0,
                allocated_to_fees=0,
                allocated_to_principal=principal,
                payment_method="bank-transfer",
                notes="Pago final (Liquidacion)",
                received_by=users["collector"].id,
            )
            db.add(payment)
            db.flush()
            pe = PaymentEvent(
                payment_type="mixed_payment",
                payment_id=payment.id,
                loan_id=loan.id,
                total_entered_amount=principal,
                allocated_to_interest=0,
                allocated_to_penalty=0,
                allocated_to_principal=principal,
                payment_date=payment.payment_date,
                operator_user_id=users["collector"].id,
                payment_method="bank-transfer",
                notes=payment.notes
            )
            db.add(pe)
            db.flush()

    db.commit()
    return True


def _ensure_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    required_users = {
        "officer": ("officer", "officer123", UserRole.loan_officer),
        "collector": ("collector", "collector123", UserRole.collector),
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
