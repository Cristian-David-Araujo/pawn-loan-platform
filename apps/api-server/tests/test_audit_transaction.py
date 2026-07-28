"""Every path that moves money records who moved it, in the same transaction.

`write_audit` commits by default, which is fine for a settings change. On a money path it
means two transactions: the payment can stand while the audit row is lost, leaving a
collection that nobody appears to have taken — and the audit table has no read path in the
application, so there is nothing to reconcile it against afterwards.

This file pins the *presence* of the row for each money path. The atomicity itself is
structural — `commit=False` plus a single `db.commit()` — and can only really be checked by
reading the code, so the comment above the call is the other half of the guard.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import AuditLog, GlobalSettings


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _loan(client: TestClient, auth_headers: dict[str, str], customer_id: int, *, days_ago: int = 35) -> dict:
    disbursement = date.today() - timedelta(days=days_ago)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id, "loan_type": "pawn", "principal_amount": 1000000,
            "outstanding_principal": 1000000, "monthly_interest_rate": 5, "late_penalty_rate": 0,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _actions(db_session: Session) -> list[str]:
    db_session.expire_all()
    return [row.action for row in db_session.scalars(select(AuditLog).order_by(AuditLog.id)).all()]


def test_every_money_movement_leaves_an_audit_row(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    loan = _loan(client, auth_headers, customer["id"])

    interest = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 50000, "payment_method": "cash"},
    )
    assert interest.status_code == 200, interest.text
    assert "interest_payment" in _actions(db_session)

    principal = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 400000, "payment_method": "cash"},
    )
    assert principal.status_code == 200, principal.text
    assert "principal_payment" in _actions(db_session)

    payment_id = client.get("/api/v1/payments", headers=auth_headers).json()[0]["id"]
    reversal = client.post(
        f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "till error"}
    )
    assert reversal.status_code == 200, reversal.text
    assert "reverse_payment" in _actions(db_session)


def test_an_advance_is_audited_too(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The branch with nothing pending writes a different row, so it needs its own check."""
    _configure(db_session)
    customer = create_customer()
    _loan(client, auth_headers, customer["id"], days_ago=0)

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 200000, "payment_method": "cash"},
    )
    assert response.status_code == 200, response.text
    assert "interest_advance_payment" in _actions(db_session)


def test_a_rejected_payment_leaves_no_audit_row_behind(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The other half of sharing the transaction: nothing sticks when the payment does not."""
    _configure(db_session)
    customer = create_customer()
    loan = _loan(client, auth_headers, customer["id"])
    before = _actions(db_session)

    refused = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 99999999, "payment_method": "cash"},
    )
    assert refused.status_code == 400

    assert _actions(db_session) == before, "a rejected payment recorded an action anyway"
