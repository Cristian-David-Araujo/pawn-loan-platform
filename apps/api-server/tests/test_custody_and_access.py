"""Who may touch the vault, and how a pledge is labelled.

Custody is the leverage behind a pawn loan and the label is how a physical item is found, so
both the permissions and the code have to hold up against the ordinary accidents of the job:
a loan deleted, a customer paying at the counter, a cash report read at the end of the day.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.user import UserRole
from src.infrastructure.persistence.models import CollateralItem, GlobalSettings, User
from src.infrastructure.security.password import get_password_hash


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _headers_for(client: TestClient, db_session: Session, username: str, role: UserRole) -> dict[str, str]:
    db_session.add(
        User(
            username=username,
            hashed_password=get_password_hash("secretpassword"),
            role=role,
            is_active=True,
            full_name="",
            email="",
            phone="",
            document_number="",
            address="",
        )
    )
    db_session.commit()
    response = client.post("/api/v1/auth/login", json={"username": username, "password": "secretpassword"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _pawn_loan(client: TestClient, auth_headers: dict[str, str], customer_id: int, *, days_ago: int = 0) -> dict:
    disbursement = date.today() - timedelta(days=days_ago)
    response = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer_id, "loan_type": "pawn", "principal_amount": 1000000,
            "outstanding_principal": 1000000, "monthly_interest_rate": 5, "late_penalty_rate": 10,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
            "description": "gold chain",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _pledge(client: TestClient, headers: dict[str, str], loan_id: int, description: str):
    return client.post(
        "/api/v1/collateral-items",
        headers=headers,
        json={
            "loan_id": loan_id, "item_type": "general", "description": description,
            "serial_number": "", "appraised_value": 500000, "storage_location": "box 1",
        },
    )


def test_a_custody_code_is_never_reused_after_a_pledge_is_deleted(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Deleting a loan cascades to its pledges, and the label must not come back.

    The code was `count() + 1`. With the counter behind, the next registration either hit a
    code that still existed — the unique index turning every further attempt into a 500 — or
    landed on the gap and reissued a label already printed on someone's document.
    """
    _configure(db_session)
    customer = create_customer()
    doomed = _pawn_loan(client, auth_headers, customer["id"])
    keeper = _pawn_loan(client, auth_headers, customer["id"])

    first = _pledge(client, auth_headers, doomed["id"], "ring").json()["custody_code"]
    second = _pledge(client, auth_headers, keeper["id"], "watch").json()["custody_code"]
    third = _pledge(client, auth_headers, keeper["id"], "chain").json()["custody_code"]
    assert len({first, second, third}) == 3

    deleted = client.delete(f"/api/v1/loans/{doomed['id']}", headers=auth_headers)
    assert deleted.status_code == 204, deleted.text

    # Two pledges left, so the old counter would have produced `third` again.
    fresh = _pledge(client, auth_headers, keeper["id"], "bracelet")
    assert fresh.status_code == 201, fresh.text
    assert fresh.json()["custody_code"] not in {first, second, third}

    codes = [item.custody_code for item in db_session.scalars(select(CollateralItem)).all()]
    assert len(codes) == len(set(codes))


def test_a_collector_hands_pledges_back_but_cannot_register_or_write_them_off(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The counter role delivers goods; it does not decide what enters or leaves the books.

    Every route here except the sale used to take plain `get_current_user`, so a collector
    could register a pledge, move it to another loan or write it off — including one held for
    a loan being paid on time.
    """
    _configure(db_session)
    collector = _headers_for(client, db_session, "counter", UserRole.collector)
    customer = create_customer()
    loan = _pawn_loan(client, auth_headers, customer["id"])

    denied = _pledge(client, collector, loan["id"], "ring")
    assert denied.status_code == 403, "a collector registered a pledge"

    pledge_id = _pledge(client, auth_headers, loan["id"], "ring").json()["id"]

    assert client.post(f"/api/v1/collateral-items/{pledge_id}/liquidate", headers=collector).status_code == 403
    assert client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell", headers=collector, json={"sale_price": 1}
    ).status_code == 403

    # Settle the loan, and the collector may hand the goods over.
    paid = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={"loan_id": loan["id"], "total_amount": 1000000, "payment_method": "cash"},
    )
    assert paid.status_code == 200, paid.text

    released = client.post(f"/api/v1/collateral-items/{pledge_id}/release", headers=collector)
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "released"


def test_a_loan_officer_cannot_write_off_or_sell_a_pledge(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Disposing of someone else's goods is an administrator's call."""
    _configure(db_session)
    officer = _headers_for(client, db_session, "officer", UserRole.loan_officer)
    customer = create_customer()
    loan = _pawn_loan(client, auth_headers, customer["id"])
    pledge_id = _pledge(client, officer, loan["id"], "ring").json()["id"]

    client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers)

    assert client.post(f"/api/v1/collateral-items/{pledge_id}/liquidate", headers=officer).status_code == 403
    assert client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell", headers=officer, json={"sale_price": 100}
    ).status_code == 403


def test_the_cash_report_excludes_money_that_went_back(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    _configure(db_session)
    customer = create_customer()
    disbursement = date.today() - timedelta(days=35)
    client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"], "loan_type": "personal", "principal_amount": 1000000,
            "outstanding_principal": 1000000, "monthly_interest_rate": 5, "late_penalty_rate": 0,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
        },
    )
    client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": customer["id"], "total_amount": 50000, "payment_method": "cash"},
    )

    before = client.get("/api/v1/reports/cash-summary", headers=auth_headers).json()
    assert before["total_collected"] == 50000

    payment_id = client.get("/api/v1/payments", headers=auth_headers).json()[0]["id"]
    client.post(
        f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "till error"}
    )

    after = client.get("/api/v1/reports/cash-summary", headers=auth_headers).json()
    assert after["total_collected"] == 0, "the report counted money returned to the customer"
    assert after["payments_count"] == 0
    assert after["total_reversed"] == 50000, "the reversal is not hidden either"


def test_the_arrears_report_carries_a_closed_loan_that_still_owes(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """`pay_principal` closes at zero principal, interest and all."""
    _configure(db_session)
    customer = create_customer()
    disbursement = date.today() - timedelta(days=95)
    loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"], "loan_type": "pawn", "principal_amount": 1000000,
            "outstanding_principal": 1000000, "monthly_interest_rate": 5, "late_penalty_rate": 10,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
        },
    ).json()

    settled = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"], "total_amount": 1000000, "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert settled.status_code == 200, settled.text

    report = client.get("/api/v1/reports/overdue-loans", headers=auth_headers).json()
    assert report["count"] == 1, "a closed loan owing 165.000 vanished from the arrears report"
    row = report["items"][0]
    assert row["status"] == "closed"
    assert row["outstanding_principal"] == 0
    assert row["pending_interest"] == 150000
    assert row["pending_penalty"] == 15000
    assert report["total_owed"] == 165000


def test_the_last_administrator_cannot_lock_everyone_out(
    client: TestClient,
    auth_headers: dict[str, str],
    db_session: Session,
) -> None:
    """Creating users is admin-only, so an installation with no admin can never regain one."""
    admin = db_session.scalar(select(User).where(User.role == UserRole.administrator))

    demoted = client.put(
        f"/api/v1/users/{admin.id}", headers=auth_headers, json={"role": "collector"}
    )
    assert demoted.status_code == 400
    assert "administrator" in demoted.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.get(User, admin.id).role == UserRole.administrator
    assert client.get("/api/v1/users", headers=auth_headers).status_code == 200

    # With a second administrator around, the demotion is allowed.
    _headers_for(client, db_session, "second_admin", UserRole.administrator)
    allowed = client.put(
        f"/api/v1/users/{admin.id}", headers=auth_headers, json={"role": "collector"}
    )
    assert allowed.status_code == 200, allowed.text


def test_a_new_user_needs_a_password_worth_the_name(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """A reset already demanded eight characters; setting one had no floor at all."""
    weak = client.post(
        "/api/v1/users", headers=auth_headers, json={"username": "weak", "password": "1", "role": "collector"}
    )
    assert weak.status_code == 422

    ok = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={"username": "solid", "password": "longenough1", "role": "collector"},
    )
    assert ok.status_code == 201, ok.text
