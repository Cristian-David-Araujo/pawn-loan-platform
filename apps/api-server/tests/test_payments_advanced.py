from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import InterestCharge, Loan


def _create_interest_charge(db_session: Session, loan_id: int, amount: float = 100.0) -> InterestCharge:
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=date.today(),
        period_end=date.today(),
        charge_date=date.today(),
        amount=amount,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()
    db_session.refresh(charge)
    return charge


def test_interest_pending_groups_for_customer(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_interest_charge(db_session, loan["id"], amount=120)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == loan_db.customer_id
    assert payload["total_pending_interest"] > 0
    assert len(payload["groups"]) >= 1


def test_partial_interest_payment_and_traceability(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1100)
    charge = _create_interest_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 40,
            "payment_method": "cash",
            "notes": "partial interest",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_allocated_amount"] == 40
    assert payload["allocations"][0]["payment_type"] == "partial_interest_payment"

    history = client.get(f"/api/v1/payments/customers/{loan_db.customer_id}/history", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) >= 1


def test_selected_interest_with_excess_creates_advance(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=900)
    charge = _create_interest_charge(db_session, loan["id"], amount=70)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 100,
            "payment_method": "cash",
            "notes": "selected plus advance",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    payment_types = {item["payment_type"] for item in payload["allocations"]}
    assert "interest_payment" in payment_types or "partial_interest_payment" in payment_types
    assert "interest_advance_payment" in payment_types


def test_interest_advance_without_pending_charges(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1300)
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [],
            "pay_all_pending": True,
            "total_amount": 25,
            "payment_method": "cash",
            "notes": "advance only",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_allocated_amount"] == 25
    assert payload["allocations"][0]["payment_type"] == "interest_advance_payment"


def test_principal_payment_requires_flag_when_unpaid_interest_exists(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=800)
    _create_interest_charge(db_session, loan["id"], amount=50)

    blocked = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 20,
            "payment_method": "cash",
            "allow_with_unpaid_interest": False,
            "notes": "should fail",
        },
    )
    assert blocked.status_code == 400

    allowed = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 20,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
            "notes": "allowed",
        },
    )
    assert allowed.status_code == 200
    assert allowed.json()["allocated_to_principal"] == 20
