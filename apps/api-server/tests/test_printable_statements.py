"""Field contract for the printable documents.

The print views (payment receipt, loan statement, customer statement, payment history)
read these exact field names. Renaming one without updating the frontend would silently
print zeros, so the names are pinned here.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import InterestCharge, Loan


def _create_past_due_charge(
    db_session: Session,
    loan_id: int,
    amount: float = 100.0,
    months_ago: int = 1,
) -> InterestCharge:
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=date.today() - timedelta(days=30 * (months_ago + 1)),
        period_end=date.today() - timedelta(days=30 * months_ago),
        charge_date=date.today() - timedelta(days=30 * months_ago),
        amount=amount,
        status="generated",
    )
    db_session.add(charge)
    db_session.commit()
    db_session.refresh(charge)
    return charge


def test_principal_context_exposes_the_loan_statement_fields(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_past_due_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/principal-context",
        headers=auth_headers,
    )
    assert response.status_code == 200

    item = next(entry for entry in response.json()["items"] if entry["loan_id"] == loan["id"])
    assert set(item) >= {
        "loan_id",
        "next_due_date",
        "original_principal",
        "outstanding_principal",
        "accrued_unpaid_interest",
        "penalties",
        "total_payoff_amount",
    }

    # The printed "total para liquidar" must add up.
    assert item["total_payoff_amount"] == round(
        item["outstanding_principal"] + item["accrued_unpaid_interest"] + item["penalties"], 2
    )
    assert item["accrued_unpaid_interest"] > 0


def test_interest_pending_exposes_the_period_detail_fields(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_past_due_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    response = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/interest-pending",
        headers=auth_headers,
    )
    assert response.status_code == 200

    items = [item for group in response.json()["groups"] for item in group["items"]]
    assert items

    assert set(items[0]) >= {
        "interest_charge_id",
        "loan_id",
        "billing_period",
        "due_date",
        "original_interest_amount",
        "remaining_pending_amount",
        "overdue",
        "penalty_amount",
        "current_outstanding_balance",
    }


def test_payment_history_exposes_operator_and_reversal_state(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    charge = _create_past_due_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "selected_charge_ids": [charge.id],
            "pay_all_pending": False,
            "total_amount": 50,
            "payment_method": "cash",
            "notes": "abono",
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]

    history = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/history",
        headers=auth_headers,
    )
    assert history.status_code == 200
    event = history.json()[0]

    assert set(event) >= {
        "payment_type",
        "loan_id",
        "billing_period",
        "total_entered_amount",
        "allocated_to_interest",
        "allocated_to_penalty",
        "allocated_to_principal",
        "payment_date",
        "is_reversed",
        "operator",
    }
    # The printed history credits whoever received the money.
    assert event["operator"]["username"] == "admin"
    assert event["is_reversed"] is False

    # After a reversal the printed row must be flagged so totals can exclude it.
    assert client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"}).status_code == 200

    history_after = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/history",
        headers=auth_headers,
    )
    assert all(item["is_reversed"] for item in history_after.json())


def test_receipt_breaks_one_payment_down_across_the_charges_it_settled(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """A single payment covering two charges must print one line per charge.

    This is the traceability case: the customer hands over 100 against two invoices of
    50, and the receipt has to show where each half went instead of one opaque total.
    """
    loan = create_loan(principal=1000)
    older = _create_past_due_charge(db_session, loan["id"], amount=50, months_ago=2)
    newer = _create_past_due_charge(db_session, loan["id"], amount=50, months_ago=1)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": loan_db.customer_id,
            "pay_all_pending": True,
            "total_amount": 100,
            "payment_method": "cash",
        },
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]

    response = client.get(f"/api/v1/payments/{payment_id}/allocations", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()

    assert set(body) >= {
        "payment_id",
        "payment_date",
        "loan_ids",
        "total_amount",
        "total_allocated",
        "unallocated_amount",
        "is_reversed",
        "allocations",
    }
    assert set(body["allocations"][0]) >= {
        "payment_event_id",
        "payment_type",
        "loan_id",
        "interest_charge_id",
        "billing_period",
        "charge_amount",
        "charge_due_date",
        "allocated_to_interest",
        "allocated_to_penalty",
        "allocated_to_principal",
        "allocated_total",
        "fully_covered",
        "is_reversed",
    }

    # One line per settled charge, oldest first — the order the money was applied in.
    settled = [item for item in body["allocations"] if item["interest_charge_id"] is not None]
    assert [item["interest_charge_id"] for item in settled] == [older.id, newer.id]
    assert all(item["charge_amount"] == 50 for item in settled)
    assert all(item["fully_covered"] for item in settled)

    # The printed breakdown must reconcile with the money received.
    assert body["total_amount"] == 100
    assert body["total_allocated"] == 100
    assert body["unallocated_amount"] == 0
    assert round(sum(item["allocated_total"] for item in body["allocations"]), 2) == body["total_amount"]


def test_receipt_breakdown_flags_a_partially_covered_charge(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    loan = create_loan(principal=1000)
    _create_past_due_charge(db_session, loan["id"], amount=100)

    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    payment = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={"customer_id": loan_db.customer_id, "pay_all_pending": True, "total_amount": 40},
    )
    assert payment.status_code == 200
    payment_id = payment.json()["allocations"][0]["payment_id"]

    body = client.get(f"/api/v1/payments/{payment_id}/allocations", headers=auth_headers).json()
    line = body["allocations"][0]

    assert line["fully_covered"] is False
    assert line["charge_amount"] == 100
    assert line["allocated_total"] == 40

    # Reversing keeps the line on the receipt but drops it out of the total.
    assert client.post(f"/api/v1/payments/{payment_id}/reverse", headers=auth_headers, json={"reason": "operator correction"}).status_code == 200

    after = client.get(f"/api/v1/payments/{payment_id}/allocations", headers=auth_headers).json()
    assert after["is_reversed"] is True
    assert after["allocations"][0]["is_reversed"] is True
    assert after["total_allocated"] == 0


def test_closed_loan_is_absent_from_the_statement(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """The print view falls back to the stored principal when a loan owes nothing."""
    loan = create_loan(principal=500)
    loan_db = db_session.get(Loan, loan["id"])
    assert loan_db is not None

    closed = client.post(
        f"/api/v1/loans/{loan['id']}/close",
        headers=auth_headers,
        json={"force": True},
    )
    assert closed.status_code == 200

    response = client.get(
        f"/api/v1/payments/customers/{loan_db.customer_id}/principal-context",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert all(item["loan_id"] != loan["id"] for item in response.json()["items"])
