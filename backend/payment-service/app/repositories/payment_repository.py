from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: UUID) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def get_by_loan_id(self, loan_id: UUID) -> List[Payment]:
        return self.db.query(Payment).filter(Payment.loan_id == loan_id).order_by(Payment.payment_date.desc()).all()

    def get_all(self, skip: int = 0, limit: int = 100) -> Tuple[List[Payment], int]:
        query = self.db.query(Payment)
        total = query.count()
        items = query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, **kwargs) -> Payment:
        payment = Payment(**kwargs)
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def reverse(self, payment: Payment, reason: str, reversed_by: Optional[UUID] = None) -> Payment:
        payment.status = PaymentStatus.REVERSED
        payment.reversal_reason = reason
        payment.reversed_by = reversed_by
        payment.reversed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(payment)
        return payment
