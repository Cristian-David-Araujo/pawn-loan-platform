from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.schemas.reports import (
    ActiveLoansReport,
    CashSummaryReport,
    CollateralReport,
    OverdueLoansReport,
)


class ReportingService:
    def __init__(self, token: str):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def _get(self, url: str, params: Optional[Dict] = None) -> Any:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

    def get_active_loans_report(self) -> ActiveLoansReport:
        data = self._get(f"{settings.LOAN_SERVICE_URL}/api/v1/loans", params={"status": "active", "limit": 1000})
        loans = data.get("items", [])
        total = data.get("total", 0)
        outstanding = sum(Decimal(str(loan.get("outstanding_principal", 0))) for loan in loans)
        by_type: Dict[str, int] = {}
        for loan in loans:
            lt = loan.get("loan_type", "unknown")
            by_type[lt] = by_type.get(lt, 0) + 1
        return ActiveLoansReport(
            total_active_loans=total,
            total_outstanding_principal=outstanding,
            by_loan_type=by_type,
        )

    def get_overdue_loans_report(self) -> OverdueLoansReport:
        data = self._get(f"{settings.LOAN_SERVICE_URL}/api/v1/loans", params={"status": "overdue", "limit": 1000})
        loans = data.get("items", [])
        total = data.get("total", 0)
        return OverdueLoansReport(
            total_overdue_loans=total,
            aging_1_30=len([l for l in loans if l.get("aging_days", 0) <= 30]),
            aging_31_60=len([l for l in loans if 31 <= l.get("aging_days", 0) <= 60]),
            aging_61_90=len([l for l in loans if 61 <= l.get("aging_days", 0) <= 90]),
            aging_91_plus=len([l for l in loans if l.get("aging_days", 0) > 90]),
        )

    def get_collateral_report(self) -> CollateralReport:
        custody_data = self._get(f"{settings.COLLATERAL_SERVICE_URL}/api/v1/collateral-items", params={"status": "in_custody", "limit": 1000})
        released_data = self._get(f"{settings.COLLATERAL_SERVICE_URL}/api/v1/collateral-items", params={"status": "released", "limit": 1000})
        liquidation_data = self._get(f"{settings.COLLATERAL_SERVICE_URL}/api/v1/collateral-items", params={"status": "under_liquidation", "limit": 1000})
        sold_data = self._get(f"{settings.COLLATERAL_SERVICE_URL}/api/v1/collateral-items", params={"status": "sold", "limit": 1000})
        return CollateralReport(
            total_in_custody=custody_data.get("total", 0),
            total_released=released_data.get("total", 0),
            total_under_liquidation=liquidation_data.get("total", 0),
            total_sold=sold_data.get("total", 0),
        )

    def get_cash_summary(self, date_from: Optional[date] = None, date_to: Optional[date] = None) -> CashSummaryReport:
        params = {"limit": 1000}
        data = self._get(f"{settings.PAYMENT_SERVICE_URL}/api/v1/payments", params=params)
        payments = data.get("items", [])
        total = sum(Decimal(str(p.get("total_amount", 0))) for p in payments if p.get("status") == "completed")
        interest = sum(Decimal(str(p.get("allocated_to_interest", 0))) for p in payments if p.get("status") == "completed")
        principal = sum(Decimal(str(p.get("allocated_to_principal", 0))) for p in payments if p.get("status") == "completed")
        penalty = sum(Decimal(str(p.get("allocated_to_penalty", 0))) for p in payments if p.get("status") == "completed")
        return CashSummaryReport(
            date_from=date_from,
            date_to=date_to,
            total_collected=total,
            total_interest_collected=interest,
            total_principal_collected=principal,
            total_penalty_collected=penalty,
        )
