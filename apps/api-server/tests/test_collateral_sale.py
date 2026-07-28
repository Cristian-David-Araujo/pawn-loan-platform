"""What the proceeds of a foreclosure sale have to pay before anything else.

Selling a pledge is the shop collecting through the goods instead of through the customer,
so the money has to land on the debt the same way a payment would. It used to go straight to
principal, which closed the loan while its interest stayed live and left the surplus recorded
in a total that its own buckets did not add up to.
"""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import GlobalSettings, Loan, Payment, PaymentEvent


def _configure(db_session: Session, *, grace_days: int = 0, lead_days: int = 0) -> None:
    settings = db_session.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db_session.add(settings)
    settings.default_grace_days = grace_days
    settings.interest_generation_lead_days = lead_days
    db_session.commit()


def _foreclosed_pawn_loan(
    client: TestClient,
    auth_headers: dict[str, str],
    customer_id: int,
    *,
    disbursed_days_ago: int = 95,
    principal: float = 1000000,
) -> tuple[dict, int]:
    """A loan three months behind, foreclosed, with one pledge up for sale."""
    disbursement = date.today() - timedelta(days=disbursed_days_ago)
    loan = client.post(
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
    assert loan.status_code == 201, loan.text
    loan = loan.json()

    pledge = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan["id"],
            "item_type": "general",
            "description": "gold chain",
            "serial_number": "",
            "appraised_value": 2000000,
            "storage_location": "box 1",
        },
    )
    assert pledge.status_code == 201, pledge.text

    foreclose = client.post(f"/api/v1/loans/{loan['id']}/foreclose", headers=auth_headers)
    assert foreclose.status_code == 200, foreclose.text

    return loan, pledge.json()["id"]


def test_the_sale_settles_penalty_and_interest_before_principal(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """1.000.000 of principal, 150.000 of interest, 15.000 of penalty, sold for 1.165.000."""
    _configure(db_session)
    customer = create_customer()
    loan, pledge_id = _foreclosed_pawn_loan(client, auth_headers, customer["id"])

    before = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert before["total_pending_interest"] == 150000
    assert before["total_pending_penalty"] == 15000

    sale = client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell",
        headers=auth_headers,
        json={"sale_price": 1165000, "notes": "auction"},
    )
    assert sale.status_code == 200, sale.text

    db_session.expire_all()
    stored_loan = db_session.get(Loan, loan["id"])
    assert stored_loan.outstanding_principal == 0
    assert stored_loan.status == LoanStatus.closed

    after = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert after["total_pending_interest"] == 0, "the sale left accrued interest unpaid"
    assert after["total_pending_penalty"] == 0

    payment = db_session.scalar(select(Payment).where(Payment.loan_id == loan["id"]))
    assert payment.total_amount == 1165000
    assert payment.allocated_to_penalty == 15000
    assert payment.allocated_to_interest == 150000
    assert payment.allocated_to_principal == 1000000
    assert payment.allocated_to_fees == 0


def test_a_payment_from_a_sale_always_adds_up_to_itself(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """The surplus is the house's, and it is recorded rather than left unaccounted for.

    The buckets used to fall short of `total_amount` by the whole surplus, so the payment
    could not explain the money it said it had received.
    """
    _configure(db_session)
    customer = create_customer()
    loan, pledge_id = _foreclosed_pawn_loan(client, auth_headers, customer["id"])

    sale = client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell",
        headers=auth_headers,
        json={"sale_price": 2000000, "notes": "auction"},
    )
    assert sale.status_code == 200, sale.text

    db_session.expire_all()
    payment = db_session.scalar(select(Payment).where(Payment.loan_id == loan["id"]))
    buckets = round(
        payment.allocated_to_penalty
        + payment.allocated_to_interest
        + payment.allocated_to_fees
        + payment.allocated_to_principal,
        2,
    )
    assert buckets == payment.total_amount == 2000000
    # 2.000.000 - (15.000 penalty + 150.000 interest + 1.000.000 principal)
    assert payment.allocated_to_fees == 835000


def test_a_sale_short_of_the_debt_leaves_the_rest_owed(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """A pledge that fetched less than the debt does not close the loan."""
    _configure(db_session)
    customer = create_customer()
    loan, pledge_id = _foreclosed_pawn_loan(client, auth_headers, customer["id"])

    sale = client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell",
        headers=auth_headers,
        json={"sale_price": 200000, "notes": "auction"},
    )
    assert sale.status_code == 200, sale.text

    db_session.expire_all()
    stored_loan = db_session.get(Loan, loan["id"])
    # 165.000 of interest and penalty first, then 35.000 off the principal.
    assert stored_loan.outstanding_principal == 965000
    assert stored_loan.status == LoanStatus.defaulted, "a partial sale must not close the loan"

    after = client.get(
        f"/api/v1/payments/customers/{customer['id']}/interest-pending", headers=auth_headers
    ).json()
    assert after["total_pending_interest"] == 0
    assert after["total_pending_penalty"] == 0


def test_the_sale_writes_ledger_rows_the_receipt_can_explain(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """One row per period touched, so `/payments/{id}/allocations` is not empty."""
    _configure(db_session)
    customer = create_customer()
    loan, pledge_id = _foreclosed_pawn_loan(client, auth_headers, customer["id"])

    client.post(
        f"/api/v1/collateral-items/{pledge_id}/sell",
        headers=auth_headers,
        json={"sale_price": 1165000, "notes": "auction"},
    )

    db_session.expire_all()
    payment = db_session.scalar(select(Payment).where(Payment.loan_id == loan["id"]))
    events = list(db_session.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == payment.id)).all())
    # Three billing periods plus the principal row.
    assert len(events) == 4
    assert all(event.payment_type == "collateral_sale" for event in events)

    allocations = client.get(f"/api/v1/payments/{payment.id}/allocations", headers=auth_headers)
    assert allocations.status_code == 200, allocations.text
    assert len(allocations.json()["allocations"]) == 4


def test_only_a_foreclosed_pledge_can_be_sold(
    client: TestClient,
    auth_headers: dict[str, str],
    create_customer,
    db_session: Session,
) -> None:
    """An item in custody belongs to the customer until foreclosure says otherwise."""
    _configure(db_session)
    customer = create_customer()
    disbursement = date.today() - timedelta(days=35)
    loan = client.post(
        "/api/v1/loans",
        headers=auth_headers,
        json={
            "customer_id": customer["id"], "loan_type": "pawn", "principal_amount": 1000000,
            "outstanding_principal": 1000000, "monthly_interest_rate": 5, "late_penalty_rate": 10,
            "disbursement_date": disbursement.isoformat(), "due_day": disbursement.day,
            "description": "gold chain",
        },
    ).json()
    pledge = client.post(
        "/api/v1/collateral-items",
        headers=auth_headers,
        json={
            "loan_id": loan["id"], "item_type": "general", "description": "gold chain",
            "serial_number": "", "appraised_value": 2000000, "storage_location": "box 1",
        },
    ).json()

    response = client.post(
        f"/api/v1/collateral-items/{pledge['id']}/sell",
        headers=auth_headers,
        json={"sale_price": 2000000},
    )
    assert response.status_code == 400
    assert "not for sale" in response.json()["detail"].lower()

    db_session.expire_all()
    assert db_session.scalar(select(Payment).where(Payment.loan_id == loan["id"])) is None
