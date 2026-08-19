"""The next due date is never the day the loan was signed.

A statement printed the same afternoon a loan was disbursed read "próximo vencimiento" as
that very day. The first billing period runs from the disbursement to the same day of the
next month, so on day zero nothing has fallen due yet.
"""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import Loan
from src.modules.payments.router import _next_interest_generation_date as next_due


def test_the_day_it_is_signed_points_at_next_month() -> None:
    signed = date(2026, 8, 19)
    assert next_due(signed, signed) == date(2026, 9, 19)


def test_the_day_after_still_points_at_the_first_period_end() -> None:
    signed = date(2026, 8, 19)
    assert next_due(date(2026, 8, 20), signed) == date(2026, 9, 19)


def test_the_period_end_itself_is_the_answer_that_day() -> None:
    """On the day a period closes, that day *is* the due date — this is the case the old
    `<=` was written for, and it has to keep working."""
    signed = date(2026, 8, 19)
    assert next_due(date(2026, 9, 19), signed) == date(2026, 9, 19)
    assert next_due(date(2026, 9, 20), signed) == date(2026, 10, 19)


def test_a_month_end_anchor_lands_on_the_shortest_month() -> None:
    """A loan signed on the 31st has no 31st to fall on in February."""
    assert next_due(date(2026, 1, 31), date(2026, 1, 31)) == date(2026, 2, 28)
    assert next_due(date(2026, 8, 31), date(2026, 8, 31)) == date(2026, 9, 30)


def test_a_freshly_created_loan_prints_a_future_due_date(
    client: TestClient, db_session: Session, auth_headers: dict[str, str], create_loan
) -> None:
    """End to end, through the endpoint the printed statement actually reads."""
    loan = create_loan(principal=1000.0)
    row = db_session.get(Loan, loan["id"])

    response = client.get(
        f"/api/v1/payments/customers/{row.customer_id}/principal-context", headers=auth_headers
    )
    assert response.status_code == 200, response.text

    item = next(i for i in response.json()["items"] if i["loan_id"] == loan["id"])
    assert item["next_due_date"] > item["disbursement_date"], (
        "a loan cannot fall due on the day it was handed over"
    )
