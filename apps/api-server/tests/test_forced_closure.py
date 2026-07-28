"""Closing a loan over a live balance writes that balance off, so it has to be answerable.

Same shape as `test_payment_reversal.py`: the grounds are mandatory and they end up on the
row, because the audit table has no read path anywhere in the application. Without that, a
debt just stops being collectable and nobody's name is on the decision.

`POST /loans/{id}/close` is an API-only surface — no view calls it — which is exactly why the
guard belongs in the endpoint rather than in a form.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, Loan


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _loan_owing(client: TestClient, auth_headers: dict[str, str], customer_id: int, *, principal: float) -> dict:
    disbursement = date.today() - timedelta(days=35)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id, "loan_type": "pawn", "principal_amount": principal,
            "outstanding_principal": principal, "monthly_interest_rate": 5, "late_penalty_rate": 10,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_forcing_a_close_over_a_balance_requires_a_reason(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    loan = _loan_owing(client, auth_headers, customer["id"], principal=1000000)

    refused = client.post(
        f"/api/v1/loans/{loan['id']}/close", headers=auth_headers, json={"force": True}
    )
    assert refused.status_code == 400
    assert "reason" in refused.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status != LoanStatus.closed, "the loan was closed anyway"


def test_the_reason_the_operator_and_the_moment_end_up_on_the_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    loan = _loan_owing(client, auth_headers, customer["id"], principal=1000000)

    closed = client.post(
        f"/api/v1/loans/{loan['id']}/close",
        headers=auth_headers,
        json={"force": True, "reason": "written off by agreement with the customer"},
    )
    assert closed.status_code == 200, closed.text
    body = closed.json()
    assert body["status"] == "closed"
    assert body["force_closed_reason"] == "written off by agreement with the customer"
    assert body["force_closed_at"] is not None

    db_session.expire_all()
    stored = db_session.get(Loan, loan["id"])
    assert stored.force_closed_by is not None, "nobody's name is on the write-off"


def test_a_reason_shorter_than_a_reason_is_rejected(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Same minimum a payment reversal enforces, so 'x' cannot stand in for grounds."""
    _configure(db_session)
    customer = create_customer()
    loan = _loan_owing(client, auth_headers, customer["id"], principal=1000000)

    response = client.post(
        f"/api/v1/loans/{loan['id']}/close", headers=auth_headers, json={"force": True, "reason": "x"}
    )
    assert response.status_code == 422


def test_a_settled_loan_closes_without_ceremony(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Nothing is written off, so nothing needs justifying."""
    _configure(db_session)
    customer = create_customer()
    loan = _loan_owing(client, auth_headers, customer["id"], principal=1000000)

    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 55000, "payment_method": "cash"},
    )
    client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 1000000, "payment_method": "cash"},
    )

    db_session.expire_all()
    stored = db_session.get(Loan, loan["id"])
    assert stored.outstanding_principal == 0
    assert stored.force_closed_reason == ""
    assert stored.force_closed_at is None


def test_closing_over_interest_alone_still_needs_a_reason(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Zero principal is not the same as owing nothing — the interest is real money."""
    _configure(db_session)
    customer = create_customer()
    loan = _loan_owing(client, auth_headers, customer["id"], principal=1000000)

    settled = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"], "total_amount": 1000000, "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert settled.status_code == 200, settled.text

    pending = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert pending["total_pending_interest"] == 50000

    refused = client.post(
        f"/api/v1/loans/{loan['id']}/close", headers=auth_headers, json={"force": True}
    )
    assert refused.status_code == 400
    assert "reason" in refused.json()["detail"].lower()
