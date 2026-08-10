"""The three operator escape hatches: voiding a charge, pausing a loan, settling for less.

All three forgive money, so what they must record — and what they must refuse — is the point
of this file. They also all reach into the canonical interest calculation, so several of these
exist to pin that a forgiven charge disappears from *every* balance rather than just the
screen the operator was looking at.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.domain.enums.loan import LoanStatus
from src.infrastructure.persistence.models import CollateralItem, InterestCharge, Loan, User
from src.infrastructure.security.password import get_password_hash
from src.infrastructure.utils.datetime_utils import get_local_date
from src.modules.finance.interest_balance import pending_interest_for_loan
from src.modules.finance.interest_generation import generate_missing_interest_charges


def _charge(db: Session, loan_id: int, amount: float, *, months_ago: int = 1) -> InterestCharge:
    """One billing period that has already ended, so it counts as accrued."""
    today = get_local_date(db)
    period_end = today - timedelta(days=30 * (months_ago - 1))
    charge = InterestCharge(
        loan_id=loan_id,
        period_start=period_end - timedelta(days=30),
        period_end=period_end,
        charge_date=period_end,
        amount=amount,
        status="generated",
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def _officer_headers(client: TestClient, db_session: Session, username: str = "officer") -> dict[str, str]:
    db_session.add(
        User(
            username=username,
            hashed_password=get_password_hash("officer123"),
            role="loan_officer",
            is_active=True,
        )
    )
    db_session.commit()
    token = client.post("/api/v1/auth/login", json={"username": username, "password": "officer123"}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


# ── Voiding a charge ─────────────────────────────────────────────────────────────────────


def test_voiding_a_charge_removes_it_from_every_balance(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    charge = _charge(db_session, loan["id"], 100.0)

    loan_row = db_session.get(Loan, loan["id"])
    assert pending_interest_for_loan(db_session, loan_row, get_local_date(db_session)).pending_interest == 100.0

    response = client.post(
        f"/api/v1/interest/charges/{charge.id}/void",
        headers=auth_headers,
        json={"reason": "billed by mistake"},
    )
    assert response.status_code == 200
    assert response.json()["voided_at"] is not None

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    balance = pending_interest_for_loan(db_session, loan_row, get_local_date(db_session))
    assert balance.pending_interest == 0.0, "the canonical calculation must not see a voided charge"
    assert balance.items == []


def test_a_voided_period_is_not_billed_again_by_the_next_cycle(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The row stays precisely so its period slot stays taken.

    Deleting it would have been the obvious implementation, and the generator would have
    re-billed the very month an administrator had just cancelled.
    """
    loan = create_loan(principal=1000.0)
    charge = _charge(db_session, loan["id"], 100.0)
    period = (charge.period_start, charge.period_end)

    client.post(
        f"/api/v1/interest/charges/{charge.id}/void",
        headers=auth_headers,
        json={"reason": "billed by mistake"},
    )

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    generated = generate_missing_interest_charges(
        db_session, [loan_row], get_local_date(db_session), get_local_date(db_session)
    )
    db_session.commit()

    assert period not in {(c.period_start, c.period_end) for c in generated}


def test_voiding_is_refused_while_a_payment_points_at_the_charge(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """Money already allocated would be left describing a period that no longer exists."""
    loan = create_loan(principal=1000.0)
    charge = _charge(db_session, loan["id"], 100.0)

    paid = client.post(
        "/api/v1/payments/interest",
        headers=auth_headers,
        json={
            "customer_id": db_session.get(Loan, loan["id"]).customer_id,
            "total_amount": 40.0,
            "payment_method": "cash",
        },
    )
    assert paid.status_code == 200, paid.text

    refused = client.post(
        f"/api/v1/interest/charges/{charge.id}/void",
        headers=auth_headers,
        json={"reason": "changed my mind"},
    )
    assert refused.status_code == 409
    assert "Reverse them" in refused.json()["detail"]


def test_voiding_needs_a_reason_and_an_administrator(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    charge = _charge(db_session, loan["id"], 100.0)

    blank = client.post(
        f"/api/v1/interest/charges/{charge.id}/void", headers=auth_headers, json={"reason": "x"}
    )
    assert blank.status_code == 422, "three characters is the floor, same as a payment reversal"

    officer = _officer_headers(client, db_session)
    forbidden = client.post(
        f"/api/v1/interest/charges/{charge.id}/void",
        headers=officer,
        json={"reason": "billed by mistake"},
    )
    assert forbidden.status_code == 403, "forgiving money is not a loan officer's decision"


# ── Pausing a loan ───────────────────────────────────────────────────────────────────────


def test_pausing_stops_new_charges_and_writes_a_marker_instead(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """The marker is what stops the self-healing generator back-billing the pause."""
    loan = create_loan(principal=1000.0)
    loan_row = db_session.get(Loan, loan["id"])
    loan_row.disbursement_date = get_local_date(db_session) - timedelta(days=70)
    db_session.commit()

    assert client.post(
        f"/api/v1/loans/{loan['id']}/pause",
        headers=auth_headers,
        json={"reason": "payment arrangement agreed"},
    ).status_code == 200

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    generated = generate_missing_interest_charges(
        db_session, [loan_row], get_local_date(db_session), get_local_date(db_session)
    )
    db_session.commit()

    assert generated, "the periods still have to be recorded, just not billed"
    assert all(charge.amount == 0 for charge in generated)
    assert all(charge.status == "not_billed" for charge in generated)

    balance = pending_interest_for_loan(db_session, loan_row, get_local_date(db_session))
    assert balance.pending_interest == 0.0, "a marker must reach no collection screen"


def test_resuming_does_not_bill_the_paused_months(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    loan_row = db_session.get(Loan, loan["id"])
    loan_row.disbursement_date = get_local_date(db_session) - timedelta(days=70)
    db_session.commit()

    client.post(
        f"/api/v1/loans/{loan['id']}/pause", headers=auth_headers, json={"reason": "arrangement"}
    )
    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    generate_missing_interest_charges(
        db_session, [loan_row], get_local_date(db_session), get_local_date(db_session)
    )
    db_session.commit()

    assert client.post(f"/api/v1/loans/{loan['id']}/resume", headers=auth_headers).status_code == 200

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    generate_missing_interest_charges(
        db_session, [loan_row], get_local_date(db_session), get_local_date(db_session)
    )
    db_session.commit()

    balance = pending_interest_for_loan(db_session, loan_row, get_local_date(db_session))
    assert balance.pending_interest == 0.0, "the paused months must never arrive as one lump"


def test_a_pause_keeps_the_debt_that_already_existed(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """Pausing is an agreement about what happens next, not a way to erase arrears."""
    loan = create_loan(principal=1000.0)
    _charge(db_session, loan["id"], 100.0)

    client.post(
        f"/api/v1/loans/{loan['id']}/pause", headers=auth_headers, json={"reason": "arrangement"}
    )

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    balance = pending_interest_for_loan(db_session, loan_row, get_local_date(db_session))
    assert balance.pending_interest == 100.0


def test_pause_records_who_and_why_and_refuses_twice(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)

    client.post(
        f"/api/v1/loans/{loan['id']}/pause", headers=auth_headers, json={"reason": "hospitalised"}
    )
    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])
    assert loan_row.interest_paused is True
    assert loan_row.interest_pause_reason == "hospitalised"
    assert loan_row.interest_paused_at is not None
    assert loan_row.interest_paused_by is not None

    again = client.post(
        f"/api/v1/loans/{loan['id']}/pause", headers=auth_headers, json={"reason": "hospitalised"}
    )
    assert again.status_code == 400


# ── Settling a loan ──────────────────────────────────────────────────────────────────────


def test_settlement_applies_the_money_and_writes_off_the_rest(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    _charge(db_session, loan["id"], 100.0)

    response = client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=auth_headers,
        json={
            "amount": 300.0,
            "reason": "customer cannot pay the balance",
            "collateral_action": "release",
        },
    )
    assert response.status_code == 200

    db_session.expire_all()
    loan_row = db_session.get(Loan, loan["id"])

    assert loan_row.status == LoanStatus.closed
    assert loan_row.outstanding_principal == 0.0
    assert loan_row.settlement_amount == 300.0
    assert loan_row.settled_at is not None
    assert loan_row.settled_by is not None
    assert loan_row.settlement_reason == "customer cannot pay the balance"

    # 300 covers the 100 of interest first, then 200 of principal; 800 of principal is forgiven.
    assert loan_row.written_off_interest == 0.0
    assert loan_row.written_off_principal == 800.0

    balance = pending_interest_for_loan(db_session, loan_row, get_local_date(db_session))
    assert balance.outstanding == 0.0, "a settled loan must not keep showing on collection screens"


def test_settlement_voids_the_interest_it_cannot_cover(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """Closing the loan is not enough on its own.

    `pending_interest_for_customer` deliberately keeps a closed loan that still owes, so a
    settlement that only closed the loan would leave the forgiven interest on the collection
    screen forever — uncollectable and unremovable.
    """
    loan = create_loan(principal=1000.0)
    charge = _charge(db_session, loan["id"], 100.0)

    client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=auth_headers,
        json={"amount": 30.0, "reason": "nothing else recoverable", "collateral_action": "release"},
    )

    db_session.expire_all()
    charge_row = db_session.get(InterestCharge, charge.id)
    assert charge_row.voided_at is not None
    assert charge_row.void_reason == "loan_settlement"

    loan_row = db_session.get(Loan, loan["id"])
    assert loan_row.written_off_interest == 70.0
    assert loan_row.written_off_principal == 1000.0


def test_settlement_cannot_exceed_what_the_loan_owes(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)

    response = client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=auth_headers,
        json={"amount": 5000.0, "reason": "typo", "collateral_action": "release"},
    )
    assert response.status_code == 400
    assert "more than" in response.json()["detail"]

    db_session.expire_all()
    assert db_session.get(Loan, loan["id"]).status == LoanStatus.active, "a refusal writes nothing"


def test_the_operator_chooses_what_happens_to_the_pledge(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    # Distinct principals: `create_loan` derives the customer's document number from the
    # principal, so two loans of the same size collide on it.
    for principal, action, expected in ((1100.0, "release", "released"), (1200.0, "for_sale", "for_sale")):
        loan = create_loan(principal=principal)
        db_session.add(
            CollateralItem(
                loan_id=loan["id"],
                description="ring",
                appraised_value=500.0,
                custody_code=f"CUST-{loan['id']:05d}",
                status="in_custody",
            )
        )
        db_session.commit()

        assert client.post(
            f"/api/v1/loans/{loan['id']}/settle",
            headers=auth_headers,
            json={"amount": 10.0, "reason": "negotiated", "collateral_action": action},
        ).status_code == 200

        db_session.expire_all()
        pledge = db_session.query(CollateralItem).filter_by(loan_id=loan["id"]).one()
        assert pledge.status == expected


def test_settling_is_administrator_only_and_needs_a_reason(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)

    officer = _officer_headers(client, db_session, username="officer2")
    forbidden = client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=officer,
        json={"amount": 10.0, "reason": "negotiated", "collateral_action": "release"},
    )
    assert forbidden.status_code == 403

    no_reason = client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=auth_headers,
        json={"amount": 10.0, "collateral_action": "release"},
    )
    assert no_reason.status_code == 422

    no_choice = client.post(
        f"/api/v1/loans/{loan['id']}/settle",
        headers=auth_headers,
        json={"amount": 10.0, "reason": "negotiated"},
    )
    assert no_choice.status_code == 422, "handing goods over and keeping them cannot have a default"


def test_a_loan_cannot_be_settled_twice(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    loan = create_loan(principal=1000.0)
    body = {"amount": 10.0, "reason": "negotiated", "collateral_action": "release"}

    assert client.post(f"/api/v1/loans/{loan['id']}/settle", headers=auth_headers, json=body).status_code == 200
    again = client.post(f"/api/v1/loans/{loan['id']}/settle", headers=auth_headers, json=body)
    assert again.status_code == 400
    assert "already been settled" in again.json()["detail"]
