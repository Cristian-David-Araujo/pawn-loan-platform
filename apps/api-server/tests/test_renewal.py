"""What a renewal must carry across, and what it must stop carrying twice.

Renewal moves a live debt from one row to another. Every field it forgets to bring along is
a term of the loan that silently changes, and every field it forgets to clear on the source
is an amount the customer appears to owe twice.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, GlobalSettings, Loan


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _open_pawn_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    *,
    disbursed_days_ago: int = 35,
    principal: float = 1000000,
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
            "late_penalty_rate": 10,
            "disbursement_date": disbursement.isoformat(),
            "due_day": disbursement.day,
            "description": "gold chain",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_pledge(client: TestClient, auth_headers: dict[str, str], loan_id: int, description: str) -> dict:
    response = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan_id,
            "item_type": "general",
            "description": description,
            "serial_number": "",
            "appraised_value": 500000,
            "storage_location": "box 1",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_the_source_loan_stops_carrying_the_principal_it_handed_over(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """One loan renewed once must not read as two debts.

    The source kept its full outstanding while being closed, and `principal-context` reports
    anything that still owes — so the collection screen and the printed statement both
    doubled the customer's principal, and the closed half could never be collected.
    """
    _configure(db_session)
    customer = create_customer()
    source = _open_pawn_loan(client, auth_headers, customer["id"])

    renewal = client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={})
    assert renewal.status_code == 201, renewal.text
    renewed = renewal.json()

    db_session.expire_all()
    stored_source = db_session.get(Loan, source["id"])
    assert stored_source.status == LoanStatus.closed
    assert stored_source.outstanding_principal == 0
    assert renewed["outstanding_principal"] == 1000000

    context = client.get(
        f"/api/v1/payments/customers/{customer['id']}/principal-context", headers=auth_headers
    )
    assert context.status_code == 200, context.text
    total = sum(item["outstanding_principal"] for item in context.json()["items"])
    assert total == 1000000, "the customer appears to owe the principal twice"


def test_renewal_carries_the_pledges_to_the_live_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """A pawn loan without its pledge has no security behind it."""
    _configure(db_session)
    customer = create_customer()
    source = _open_pawn_loan(client, auth_headers, customer["id"])
    _add_pledge(client, auth_headers, source["id"], "gold chain")
    _add_pledge(client, auth_headers, source["id"], "watch")

    renewal = client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={})
    assert renewal.status_code == 201, renewal.text
    renewed_id = renewal.json()["id"]

    db_session.expire_all()
    pledges = list(db_session.scalars(select(CollateralItem)).all())
    assert len(pledges) == 2
    assert {item.loan_id for item in pledges} == {renewed_id}, "the pledges stayed on the closed loan"
    assert all(item.status == "in_custody" for item in pledges)


def test_renewal_inherits_the_penalty_rate_and_the_description(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    """Terms of the debt, not properties of the row that carried it.

    Dropping `late_penalty_rate` also zeroed the new loan's grace days, because a loan that
    charges no penalty is given none.
    """
    customer = create_customer()
    source = _open_pawn_loan(customer_id=customer["id"], client=client, auth_headers=auth_headers)

    renewed = client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={}).json()

    assert renewed["late_penalty_rate"] == source["late_penalty_rate"] == 10
    assert renewed["description"] == "gold chain"
    assert renewed["monthly_interest_rate"] == source["monthly_interest_rate"]


def test_an_override_still_wins_over_the_inherited_rate(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer()
    source = _open_pawn_loan(client, auth_headers, customer["id"])

    renewed = client.post(
        f"/api/v1/loans/{source['id']}/renew",
        headers=auth_headers,
        json={"monthly_interest_rate": 3},
    ).json()

    assert renewed["monthly_interest_rate"] == 3
    assert renewed["late_penalty_rate"] == 10, "an override of the rate must not reset the penalty"


def test_the_interest_already_accrued_stays_on_the_source(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Interest is owed for the months it ran, and renewal does not move or forgive it."""
    _configure(db_session)
    customer = create_customer()
    source = _open_pawn_loan(client, auth_headers, customer["id"])

    before = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert before["total_pending_interest"] == 50000

    client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={})

    after = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    owing = [item for group in after["groups"] for item in group["items"]]
    assert after["total_pending_interest"] == 50000, "renewal moved or forgave accrued interest"
    assert {item["loan_id"] for item in owing} == {source["id"]}


def test_a_closed_loan_cannot_be_renewed(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    """Renewing twice from the same source would mint a second debt out of one."""
    customer = create_customer()
    source = _open_pawn_loan(client, auth_headers, customer["id"])

    first = client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={})
    assert first.status_code == 201

    second = client.post(f"/api/v1/loans/{source['id']}/renew", headers=auth_headers, json={})
    assert second.status_code == 400
    assert "closed" in second.json()["detail"].lower()
