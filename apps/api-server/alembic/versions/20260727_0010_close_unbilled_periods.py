"""Close the months that were never billed, before interest starts accruing on arrears

Generation ran over `active` loans only, so a loan stopped billing the moment it turned
`overdue`. The months in between were never charged: they are not unpaid, they do not
exist. The companion code change makes `overdue` accrue again, and because
`_iter_due_periods` walks from the disbursement date, the first cycle after that change
would create every one of those months at once — a customer five months behind would see
their debt jump from two months to seven, overnight and with no warning.

The decision was not to bill them. This migration records that decision instead of leaving
an invisible hole: each missing period is inserted with an amount of zero and the status
`not_billed`. The generator skips periods that already exist, so those months are closed
for good, while a month that goes missing *after* this still gets picked up on the next
cycle — the self-healing behaviour is kept, which is the whole reason for marking rather
than for a cut-off date.

A zero charge never reaches a customer: balances drop anything with nothing outstanding, so
it shows in no collection screen and on no printed statement. It exists to answer, months
from now, why a given month was not charged.

The period arithmetic is copied from `interest_generation.py` on purpose rather than
imported. A migration must keep producing the same rows if that logic is ever changed, and
`period_end + 1 month` in SQL is not the same thing: the anchor is the disbursement day, so
a loan signed on the 31st bills 31 -> 28 -> 31, not 31 -> 28 -> 28.

Revision ID: 20260727_0010
Revises: 20260727_0009
Create Date: 2026-07-27 00:00:00
"""

from calendar import monthrange
from datetime import date

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260727_0010"
down_revision = "20260727_0009"
branch_labels = None
depends_on = None

NOT_BILLED_STATUS = "not_billed"


def _month_anchor(year: int, month: int, anchor_day: int) -> date:
    last_day = monthrange(year, month)[1]
    return date(year, month, min(max(1, anchor_day), last_day))


def _add_months(base_date: date, months: int, anchor_day: int) -> date:
    month_index = (base_date.month - 1) + months
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1
    return _month_anchor(year, month, anchor_day)


def _iter_due_periods(as_of_date: date, disbursement_date: date) -> list[tuple[date, date]]:
    anchor_day = disbursement_date.day
    period_start = disbursement_date
    period_end = _add_months(disbursement_date, 1, anchor_day)

    periods: list[tuple[date, date]] = []
    while period_end <= as_of_date:
        periods.append((period_start, period_end))
        period_start = period_end
        period_end = _add_months(period_end, 1, anchor_day)

    return periods


def upgrade() -> None:
    conn = op.get_bind()

    today = conn.scalar(text("SELECT CURRENT_DATE"))
    loans = conn.execute(text("SELECT id, disbursement_date FROM loans")).fetchall()
    existing = conn.execute(text("SELECT loan_id, period_start, period_end FROM interest_charges")).fetchall()

    billed: dict[int, set[tuple[date, date]]] = {}
    for loan_id, period_start, period_end in existing:
        billed.setdefault(loan_id, set()).add((period_start, period_end))

    # Every loan, not only the ones sitting in `overdue` today: a closed loan can be
    # reopened by a payment reversal, and the hole would come back to life with it.
    missing = [
        {"loan_id": loan_id, "period_start": period_start, "period_end": period_end}
        for loan_id, disbursement_date in loans
        for period_start, period_end in _iter_due_periods(today, disbursement_date)
        if (period_start, period_end) not in billed.get(loan_id, set())
    ]
    if not missing:
        return

    conn.execute(
        text(
            """
            INSERT INTO interest_charges
                (loan_id, period_start, period_end, charge_date, amount, status,
                 penalty_amount, penalty_rate_applied, penalty_applied_at, created_at)
            VALUES
                (:loan_id, :period_start, :period_end, :period_end, 0, '""" + NOT_BILLED_STATUS + """',
                 0, 0, :period_end, (NOW() AT TIME ZONE 'utc'))
            ON CONFLICT (loan_id, period_start, period_end) DO NOTHING
            """
        ),
        missing,
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM interest_charges WHERE status = :status AND amount = 0"),
        {"status": NOT_BILLED_STATUS},
    )
