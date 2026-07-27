from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import AuditLog, CollateralItem, InterestCharge, Loan, Payment, PaymentEvent


def test_application_approve_and_create_loan(client: TestClient, auth_headers: dict[str, str], create_customer) -> None:
    customer = create_customer(document_number="LOAN-CUST-1")

    app_payload = {
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "requested_amount": 1200,
        "monthly_interest_rate": 8.5,
        "term_months": 6,
        "notes": "Initial test app",
    }
    app_response = client.post("/api/v1/loan-applications", headers=auth_headers, json=app_payload)
    assert app_response.status_code == 201
    application_id = app_response.json()["id"]

    approve_response = client.post(f"/api/v1/loan-applications/{application_id}/approve", headers=auth_headers)
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    loan_payload = {
        "application_id": application_id,
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "principal_amount": 1000,
        "monthly_interest_rate": 8.5,
        "disbursement_date": str(date.today()),
        "due_day": 10,
    }
    loan_response = client.post("/api/v1/loans", headers=auth_headers, json=loan_payload)
    assert loan_response.status_code == 201
    assert loan_response.json()["outstanding_principal"] == 1000


def test_close_without_force_requires_zero_outstanding(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=900)

    close_response = client.post(f"/api/v1/loans/{loan['id']}/close", headers=auth_headers, json={"force": False})
    assert close_response.status_code == 400



def test_renew_closes_source_and_creates_new_loan(client: TestClient, auth_headers: dict[str, str], create_loan) -> None:
    source_loan = create_loan(principal=500)

    renew_response = client.post(
        f"/api/v1/loans/{source_loan['id']}/renew",
        headers=auth_headers,
        json={"monthly_interest_rate": 7.0, "due_day": 8},
    )
    assert renew_response.status_code == 201
    renewed = renew_response.json()
    assert renewed["renewal_of"] == source_loan["id"]

    source_response = client.get(f"/api/v1/loans/{source_loan['id']}", headers=auth_headers)
    assert source_response.status_code == 200
    assert source_response.json()["status"] == "closed"


def test_update_loan_allows_rate_due_day_and_status(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
) -> None:
    loan = create_loan(principal=1200)

    response = client.put(
        f"/api/v1/loans/{loan['id']}",
        headers=auth_headers,
        json={"monthly_interest_rate": 9.5, "due_day": 12, "status": "overdue"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["monthly_interest_rate"] == 9.5
    assert payload["due_day"] == 12
    assert payload["status"] == "overdue"


def test_create_loan_generates_interest_immediately_for_past_disbursement(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
) -> None:
    customer = create_customer(document_number="LOAN-CUST-PAST-1")
    disbursement_date = date.today() - timedelta(days=95)

    loan_payload = {
        "customer_id": customer["id"],
        "loan_type": "pawn",
        "principal_amount": 1000,
        "monthly_interest_rate": 8.5,
        "disbursement_date": str(disbursement_date),
        "due_day": disbursement_date.day,
    }
    loan_response = client.post("/api/v1/loans", headers=auth_headers, json=loan_payload)
    assert loan_response.status_code == 201

    loan_id = loan_response.json()["id"]
    ledger_response = client.get(f"/api/v1/loans/{loan_id}/ledger", headers=auth_headers)
    assert ledger_response.status_code == 200

    interest_charges = ledger_response.json()["interest_charges"]
    assert len(interest_charges) >= 2


def test_delete_loan_refused_once_money_has_moved(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """A loan with a payment against it must survive: the ledger is the record."""
    loan = create_loan(principal=700)

    paid = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 100,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert paid.status_code == 200

    response = client.delete(f"/api/v1/loans/{loan['id']}", headers=auth_headers)
    assert response.status_code == 409
    assert "live payment records" in response.json()["detail"]

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]) is not None


def test_a_loan_whose_payments_were_all_reversed_can_be_undone(
    client: TestClient,
    auth_headers: dict[str, str],
    create_loan,
    db_session: Session,
) -> None:
    """The mistake case: a loan paid off by accident, reversed, and then removed.

    Reversed money never really moved, so blocking the delete would leave the operator with
    a phantom loan they can neither collect nor remove. The audit row keeps the evidence.
    """
    loan = create_loan(principal=500)

    settled = client.post(
        "/api/v1/payments/principal",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "total_amount": 500,
            "payment_method": "cash",
            "allow_with_unpaid_interest": True,
        },
    )
    assert settled.status_code == 200
    payment_id = settled.json()["payment_id"]

    # Still blocked while the payment is live.
    assert client.delete(f"/api/v1/loans/{loan['id']}", headers=auth_headers).status_code == 409

    reversed_response = client.post(
        f"/api/v1/payments/{payment_id}/reverse",
        headers=auth_headers,
        json={"reason": "Crédito pagado por error"},
    )
    assert reversed_response.status_code == 200

    assert client.delete(f"/api/v1/loans/{loan['id']}", headers=auth_headers).status_code == 204

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]) is None
    assert db_session.get(Payment, payment_id) is None
    assert db_session.scalars(select(PaymentEvent).where(PaymentEvent.loan_id == loan["id"])).first() is None

    entry = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "delete_loan", AuditLog.entity_id == str(loan["id"]))
    ).one()
    # The reversed payment survives as evidence even though its row is gone.
    assert "Crédito pagado por error" in entry.old_data
    assert "deleted_reversed_payments=1" in entry.new_data


def test_deleting_a_loan_leaves_a_full_snapshot_in_the_audit_log(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """Deletion destroys the loan, its pledges and its accruals, so the audit row is the
    only surviving evidence and has to describe what was there."""
    customer = create_customer(document_number="LOAN-DELETE-SNAPSHOT")
    created = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"],
            "loan_type": "pawn",
            "principal_amount": 900,
            "monthly_interest_rate": 8.0,
            "disbursement_date": str(date.today() - timedelta(days=45)),
            "due_day": 5,
        },
    )
    assert created.status_code == 201
    loan_id = created.json()["id"]

    pledge = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan_id,
            "description": "Anillo de oro",
            "appraised_value": 950,
            "storage_location": "Vault D",
        },
    )
    assert pledge.status_code == 201
    custody_code = pledge.json()["custody_code"]

    # The past disbursement means interest was generated on creation.
    charges = db_session.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)).all()
    assert len(list(charges)) > 0

    assert client.delete(f"/api/v1/loans/{loan_id}", headers=auth_headers).status_code == 204

    db_session.expire_all()
    assert db_session.get(Loan, loan_id) is None
    assert db_session.scalars(select(CollateralItem).where(CollateralItem.loan_id == loan_id)).first() is None
    assert db_session.scalars(select(InterestCharge).where(InterestCharge.loan_id == loan_id)).first() is None

    entry = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "delete_loan", AuditLog.entity_id == str(loan_id))
    ).one()
    # Enough to reconstruct what was destroyed, not just that something was.
    assert f"customer={customer['id']}" in entry.old_data
    assert "principal=900.0" in entry.old_data
    assert "rate=8.0" in entry.old_data
    assert custody_code in entry.old_data
    assert "Anillo de oro" in entry.old_data
    assert "interest_charges=[" in entry.old_data
    assert "deleted_collaterals=1" in entry.new_data
