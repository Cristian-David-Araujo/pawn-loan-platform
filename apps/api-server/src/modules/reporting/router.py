from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, Loan, Payment, User
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db

router = APIRouter(prefix="/reports", tags=["reporting"])


@router.get("/active-loans")
def active_loans_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> dict:
    loans = list(db.scalars(select(Loan).where(Loan.status == LoanStatus.active)).all())
    return {
        "count": len(loans),
        "items": [
            {
                "id": loan.id,
                "customer_id": loan.customer_id,
                "outstanding_principal": loan.outstanding_principal,
            }
            for loan in loans
        ],
    }


@router.get("/overdue-loans")
def overdue_loans_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> dict:
    loans = list(db.scalars(select(Loan).where(Loan.status == LoanStatus.overdue)).all())
    return {
        "count": len(loans),
        "items": [
            {
                "id": loan.id,
                "customer_id": loan.customer_id,
                "outstanding_principal": loan.outstanding_principal,
            }
            for loan in loans
        ],
    }


@router.get("/collateral-custody")
def collateral_custody_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> dict:
    items = list(db.scalars(select(CollateralItem).where(CollateralItem.status == "in_custody")).all())
    return {
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "loan_id": item.loan_id,
                "custody_code": item.custody_code,
                "description": item.description,
            }
            for item in items
        ],
    }


@router.get("/cash-summary")
def cash_summary_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.administrator, UserRole.loan_officer)),
) -> dict:
    total = db.scalar(select(func.coalesce(func.sum(Payment.total_amount), 0.0)))
    count = db.scalar(select(func.count(Payment.id)))
    return {
        "payments_count": count,
        "total_collected": round(float(total or 0), 2),
    }
