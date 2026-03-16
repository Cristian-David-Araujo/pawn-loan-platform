from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ReportFilters(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    loan_type: Optional[str] = None


class ActiveLoansReport(BaseModel):
    total_active_loans: int
    total_outstanding_principal: Decimal
    by_loan_type: Dict[str, int]


class OverdueLoansReport(BaseModel):
    total_overdue_loans: int
    aging_1_30: int
    aging_31_60: int
    aging_61_90: int
    aging_91_plus: int


class CollateralReport(BaseModel):
    total_in_custody: int
    total_released: int
    total_under_liquidation: int
    total_sold: int


class CashSummaryReport(BaseModel):
    date_from: Optional[date]
    date_to: Optional[date]
    total_collected: Decimal
    total_interest_collected: Decimal
    total_principal_collected: Decimal
    total_penalty_collected: Decimal


class ServiceSummary(BaseModel):
    service: str
    data: Any
