from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, Loan, Payment, User
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_balance import pending_interest_for_loans
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
    """Everything still owed and past due, including loans already marked closed.

    A loan settled with `allow_with_unpaid_interest` sits at zero principal with live
    interest charges, and the collection screens have carried that debt for a while. This
    report filtered on status alone, so the arrears figure the shop actually reads left out
    money the same system was busy trying to collect.
    """
    today = get_local_date(db)
    candidates = list(
        db.scalars(
            select(Loan).where(Loan.status.in_((LoanStatus.overdue, LoanStatus.closed)))
        ).all()
    )
    balances = pending_interest_for_loans(db, candidates, today)

    items = []
    for loan in candidates:
        balance = balances[loan.id]
        if loan.status == LoanStatus.closed and not balance.has_overdue_interest:
            continue
        items.append(
            {
                "id": loan.id,
                "customer_id": loan.customer_id,
                "status": loan.status.value,
                "outstanding_principal": round(loan.outstanding_principal, 2),
                "pending_interest": balance.pending_interest,
                "pending_penalty": balance.pending_penalty,
                "total_owed": round(loan.outstanding_principal + balance.outstanding, 2),
            }
        )

    return {
        "count": len(items),
        "total_owed": round(sum(item["total_owed"] for item in items), 2),
        "items": items,
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
    # Reversed payments are money that went back to the customer. Counting them made the
    # only cash report in the system report a till that was never that full.
    live = Payment.is_reversed.is_(False)
    total = db.scalar(select(func.coalesce(func.sum(Payment.total_amount), 0.0)).where(live))
    count = db.scalar(select(func.count(Payment.id)).where(live))
    reversed_total = db.scalar(
        select(func.coalesce(func.sum(Payment.total_amount), 0.0)).where(Payment.is_reversed.is_(True))
    )
    return {
        "payments_count": count,
        "total_collected": round(float(total or 0), 2),
        "reversed_count": db.scalar(select(func.count(Payment.id)).where(Payment.is_reversed.is_(True))),
        "total_reversed": round(float(reversed_total or 0), 2),
    }
