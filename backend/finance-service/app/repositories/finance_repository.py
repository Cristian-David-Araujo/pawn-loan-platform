from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.finance import ChargeStatus, InterestCharge, PenaltyCharge, PenaltyStatus


class InterestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_loan(self, loan_id: UUID) -> List[InterestCharge]:
        return self.db.query(InterestCharge).filter(InterestCharge.loan_id == loan_id).order_by(InterestCharge.period_start).all()

    def get_pending_by_loan(self, loan_id: UUID) -> List[InterestCharge]:
        return self.db.query(InterestCharge).filter(
            InterestCharge.loan_id == loan_id,
            InterestCharge.status == ChargeStatus.PENDING,
        ).all()

    def has_charge_for_period(self, loan_id: UUID, period_start: date) -> bool:
        return self.db.query(InterestCharge).filter(
            InterestCharge.loan_id == loan_id,
            InterestCharge.period_start == period_start,
        ).first() is not None

    def create(self, **kwargs) -> InterestCharge:
        charge = InterestCharge(**kwargs)
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def total_pending(self, loan_id: UUID) -> Decimal:
        result = self.db.query(func.sum(InterestCharge.amount)).filter(
            InterestCharge.loan_id == loan_id,
            InterestCharge.status == ChargeStatus.PENDING,
        ).scalar()
        return result or Decimal("0")

    def update_status(self, charge: InterestCharge, status: ChargeStatus) -> InterestCharge:
        charge.status = status
        self.db.commit()
        self.db.refresh(charge)
        return charge


class PenaltyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_loan(self, loan_id: UUID) -> List[PenaltyCharge]:
        return self.db.query(PenaltyCharge).filter(PenaltyCharge.loan_id == loan_id).all()

    def create(self, **kwargs) -> PenaltyCharge:
        charge = PenaltyCharge(**kwargs)
        self.db.add(charge)
        self.db.commit()
        self.db.refresh(charge)
        return charge

    def total_pending(self, loan_id: UUID) -> Decimal:
        result = self.db.query(func.sum(PenaltyCharge.amount)).filter(
            PenaltyCharge.loan_id == loan_id,
            PenaltyCharge.status == PenaltyStatus.PENDING,
        ).scalar()
        return result or Decimal("0")
