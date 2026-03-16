from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.loan import Loan, LoanApplication, LoanApplicationStatus, LoanStatus, LoanType


class LoanApplicationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, app_id: UUID) -> Optional[LoanApplication]:
        return self.db.query(LoanApplication).filter(LoanApplication.id == app_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        customer_id: Optional[UUID] = None,
        status: Optional[LoanApplicationStatus] = None,
    ) -> Tuple[List[LoanApplication], int]:
        query = self.db.query(LoanApplication)
        if customer_id:
            query = query.filter(LoanApplication.customer_id == customer_id)
        if status:
            query = query.filter(LoanApplication.status == status)
        total = query.count()
        items = query.order_by(LoanApplication.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, **kwargs) -> LoanApplication:
        app = LoanApplication(**kwargs)
        self.db.add(app)
        self.db.commit()
        self.db.refresh(app)
        return app

    def update(self, application: LoanApplication, **kwargs) -> LoanApplication:
        for key, value in kwargs.items():
            setattr(application, key, value)
        self.db.commit()
        self.db.refresh(application)
        return application


class LoanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, loan_id: UUID) -> Optional[Loan]:
        return self.db.query(Loan).filter(Loan.id == loan_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        customer_id: Optional[UUID] = None,
        status: Optional[LoanStatus] = None,
        loan_type: Optional[LoanType] = None,
    ) -> Tuple[List[Loan], int]:
        query = self.db.query(Loan)
        if customer_id:
            query = query.filter(Loan.customer_id == customer_id)
        if status:
            query = query.filter(Loan.status == status)
        if loan_type:
            query = query.filter(Loan.loan_type == loan_type)
        total = query.count()
        items = query.order_by(Loan.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    def create(self, **kwargs) -> Loan:
        loan = Loan(**kwargs)
        self.db.add(loan)
        self.db.commit()
        self.db.refresh(loan)
        return loan

    def update(self, loan: Loan, **kwargs) -> Loan:
        for key, value in kwargs.items():
            setattr(loan, key, value)
        self.db.commit()
        self.db.refresh(loan)
        return loan
