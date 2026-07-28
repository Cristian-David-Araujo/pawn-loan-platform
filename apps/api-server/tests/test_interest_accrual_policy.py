"""The three rules that decide how much a customer owes.

They are collected here rather than split across the loan, finance and payment files
because they only make sense together: interest keeps accruing while the debt is alive,
a penalty is fixed once and never recomputed, and a period that has been invoiced is
immutable. Each of them silently reported a debt other than the real one.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import GlobalSettings, InterestCharge


def _configure(db_session: Session, *, grace_days: int = 5, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _open_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    *,
    disbursed_days_ago: int,
    principal: float = 1000000,
    penalty_rate: float = 10,
) -> dict:
    disbursement = date.today() - timedelta(days=disbursed_days_ago)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "loan_type": "pawn",
            "principal_amount": principal,
            "outstanding_principal": principal,
            "monthly_interest_rate": 5,
            "late_penalty_rate": penalty_rate,
            "disbursement_date": disbursement.isoformat(),
            "due_day": disbursement.day,
            "description": "gold chain",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _charges(db_session: Session, loan_id: int) -> list[InterestCharge]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(InterestCharge)
            .where(InterestCharge.loan_id == loan_id)
            .order_by(InterestCharge.period_start.asc())
        ).all()
    )


def test_an_invoiced_period_survives_an_edit_of_the_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Correcting a pledge description must not rewrite what was already charged.

    The amount used to be recomputed from the *current* principal for every due period,
    so paying 400.000 of principal and then fixing a typo turned an invoice of 50.000 the
    customer had already settled into one of 30.000, with the ledger still holding 50.000.
    """
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=35, penalty_rate=0)

    interest = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 50000, "payment_method": "cash"},
    )
    assert interest.status_code == 200, interest.text

    principal = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 400000, "payment_method": "cash"},
    )
    assert principal.status_code == 200, principal.text

    billed = _charges(db_session, loan["id"])
    assert [item.amount for item in billed] == [50000]

    edit = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"description": "18k gold chain"},
    )
    assert edit.status_code == 200, edit.text
    assert edit.json()["description"] == "18k gold chain"

    after = _charges(db_session, loan["id"])
    assert [item.amount for item in after] == [50000], "an invoiced period was rewritten"


def test_an_edit_only_reaches_periods_that_have_not_ended(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Lowering the principal reprices what is still open, never what already closed."""
    # Lead days pull an unfinished period forward, which is the one an edit may reprice.
    _configure(db_session, lead_days=10)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=55, penalty_rate=0)

    before = _charges(db_session, loan["id"])
    assert len(before) == 2, "expected one closed period and one still open"
    assert [item.amount for item in before] == [50000, 50000]

    edit = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"outstanding_principal": 600000},
    )
    assert edit.status_code == 200, edit.text

    after = _charges(db_session, loan["id"])
    assert after[0].amount == 50000, "the closed period must keep the amount it was invoiced at"
    assert after[1].amount == 30000, "the open period must follow the new principal"


def test_editing_a_loan_no_longer_requires_resending_rate_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    loan = _open_loan(client, auth_headers, customer["id"], disbursed_days_ago=0)

    response = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"description": "only this changed"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["monthly_interest_rate"] == loan["monthly_interest_rate"]
    assert body["status"] == loan["status"]
