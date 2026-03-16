from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.finance import InterestCharge
from app.repositories.finance_repository import InterestRepository, PenaltyRepository
from app.schemas.finance import InterestGenerateRequest, LoanBalanceResponse


class FinanceService:
    def __init__(self, db: Session):
        self.interest_repo = InterestRepository(db)
        self.penalty_repo = PenaltyRepository(db)

    def generate_interest(self, request: InterestGenerateRequest) -> InterestCharge:
        if self.interest_repo.has_charge_for_period(request.loan_id, request.period_start):
            raise ValueError(f"Interest already generated for period starting {request.period_start}")
        amount = (request.principal_base * request.interest_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.interest_repo.create(
            loan_id=request.loan_id,
            period_start=request.period_start,
            period_end=request.period_end,
            charge_date=request.charge_date,
            principal_base=request.principal_base,
            interest_rate=request.interest_rate,
            amount=amount,
        )

    def get_loan_balance(self, loan_id: UUID, outstanding_principal: Decimal) -> LoanBalanceResponse:
        total_interest = self.interest_repo.total_pending(loan_id)
        total_penalties = self.penalty_repo.total_pending(loan_id)
        return LoanBalanceResponse(
            loan_id=loan_id,
            total_pending_interest=total_interest,
            total_pending_penalties=total_penalties,
            total_outstanding=outstanding_principal + total_interest + total_penalties,
        )
