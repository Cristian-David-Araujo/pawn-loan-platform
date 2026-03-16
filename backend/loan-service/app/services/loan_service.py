from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.loan import (
    DisbursementMethod,
    Loan,
    LoanApplication,
    LoanApplicationStatus,
    LoanStatus,
    LoanType,
)
from app.repositories.loan_repository import LoanApplicationRepository, LoanRepository
from app.schemas.loan import LoanApplicationCreate, LoanCreate


class LoanService:
    def __init__(self, db: Session):
        self.app_repo = LoanApplicationRepository(db)
        self.loan_repo = LoanRepository(db)

    def create_application(self, payload: LoanApplicationCreate, created_by: Optional[UUID] = None) -> LoanApplication:
        return self.app_repo.create(
            customer_id=payload.customer_id,
            loan_type=payload.loan_type,
            requested_amount=payload.requested_amount,
            monthly_interest_rate=payload.monthly_interest_rate,
            term_months=payload.term_months,
            notes=payload.notes,
            status=LoanApplicationStatus.SUBMITTED,
            created_by=created_by,
        )

    def approve_application(self, app_id: UUID, approved_by: Optional[UUID] = None) -> Optional[LoanApplication]:
        application = self.app_repo.get_by_id(app_id)
        if not application:
            return None
        if application.status not in (LoanApplicationStatus.SUBMITTED, LoanApplicationStatus.UNDER_REVIEW):
            raise ValueError(f"Cannot approve application with status {application.status}")
        return self.app_repo.update(
            application,
            status=LoanApplicationStatus.APPROVED,
            approved_by=approved_by,
        )

    def reject_application(self, app_id: UUID, reason: str, reviewed_by: Optional[UUID] = None) -> Optional[LoanApplication]:
        application = self.app_repo.get_by_id(app_id)
        if not application:
            return None
        if application.status not in (LoanApplicationStatus.SUBMITTED, LoanApplicationStatus.UNDER_REVIEW):
            raise ValueError(f"Cannot reject application with status {application.status}")
        return self.app_repo.update(
            application,
            status=LoanApplicationStatus.REJECTED,
            rejection_reason=reason,
            reviewed_by=reviewed_by,
        )

    def create_loan(self, payload: LoanCreate) -> Loan:
        application = self.app_repo.get_by_id(payload.application_id)
        if not application:
            raise ValueError("Application not found")
        if application.status != LoanApplicationStatus.APPROVED:
            raise ValueError("Application must be approved before creating a loan")
        loan = self.loan_repo.create(
            application_id=application.id,
            customer_id=application.customer_id,
            loan_type=application.loan_type,
            principal_amount=payload.principal_amount,
            outstanding_principal=payload.principal_amount,
            monthly_interest_rate=payload.monthly_interest_rate,
            disbursement_date=payload.disbursement_date,
            due_day=payload.due_day,
            term_months=payload.term_months,
            disbursement_method=payload.disbursement_method,
            status=LoanStatus.ACTIVE,
            notes=payload.notes,
        )
        return loan

    def renew_loan(self, loan_id: UUID, new_term_months: int, new_rate: Optional[Decimal] = None) -> Optional[Loan]:
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            return None
        if loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            raise ValueError(f"Cannot renew loan with status {loan.status}")
        rate = new_rate if new_rate is not None else loan.monthly_interest_rate
        new_loan = self.loan_repo.create(
            application_id=loan.application_id,
            customer_id=loan.customer_id,
            loan_type=loan.loan_type,
            principal_amount=loan.outstanding_principal,
            outstanding_principal=loan.outstanding_principal,
            monthly_interest_rate=rate,
            disbursement_date=datetime.now(timezone.utc),
            due_day=loan.due_day,
            term_months=new_term_months,
            disbursement_method=loan.disbursement_method,
            status=LoanStatus.ACTIVE,
            renewal_of=loan.id,
        )
        self.loan_repo.update(loan, status=LoanStatus.RENEWED)
        return new_loan

    def close_loan(self, loan_id: UUID) -> Optional[Loan]:
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            return None
        if loan.status not in (LoanStatus.ACTIVE, LoanStatus.OVERDUE):
            raise ValueError(f"Cannot close loan with status {loan.status}")
        return self.loan_repo.update(loan, status=LoanStatus.CLOSED, outstanding_principal=Decimal("0"))
