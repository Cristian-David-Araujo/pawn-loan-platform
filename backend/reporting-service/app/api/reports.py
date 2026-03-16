from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import decode_token
from app.schemas.reports import (
    ActiveLoansReport,
    CashSummaryReport,
    CollateralReport,
    OverdueLoansReport,
)
from app.services.reporting_service import ReportingService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def get_token(token: str = Depends(oauth2_scheme)) -> str:
    return token


@router.get("/active-loans", response_model=ActiveLoansReport)
def active_loans_report(
    token: str = Depends(get_token),
    _=Depends(get_current_user),
):
    try:
        service = ReportingService(token)
        return service.get_active_loans_report()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch report: {str(e)}")


@router.get("/overdue-loans", response_model=OverdueLoansReport)
def overdue_loans_report(
    token: str = Depends(get_token),
    _=Depends(get_current_user),
):
    try:
        service = ReportingService(token)
        return service.get_overdue_loans_report()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch report: {str(e)}")


@router.get("/collateral-custody", response_model=CollateralReport)
def collateral_report(
    token: str = Depends(get_token),
    _=Depends(get_current_user),
):
    try:
        service = ReportingService(token)
        return service.get_collateral_report()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch report: {str(e)}")


@router.get("/cash-summary", response_model=CashSummaryReport)
def cash_summary_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    token: str = Depends(get_token),
    _=Depends(get_current_user),
):
    try:
        service = ReportingService(token)
        return service.get_cash_summary(date_from=date_from, date_to=date_to)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not fetch report: {str(e)}")
