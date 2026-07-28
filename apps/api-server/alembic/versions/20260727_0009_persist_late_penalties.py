"""Turn the late penalty into a recorded fact instead of a formula

The penalty was derived on every read as `pending interest x late_penalty_rate`, so the
same debt reported different figures on different days: paying part of the interest shrank
the base it was computed from, raising `GlobalSettings.default_grace_days` moved every past
due date forward and erased the penalty from the whole portfolio backwards, and lowering a
loan's rate rewrote penalties on periods that had fallen due months earlier. A statement
printed yesterday did not match one printed today, and nothing recorded why.

The three columns added here hold the amount, the rate that produced it and the day the
period fell due. From here on `freeze_due_penalties` writes them once, when the period
crosses its due date, and every reader takes them as given.

The backfill freezes what the application is reporting **today** — same derivation the
collection screens use, advances included — so nobody's debt moves on the day this is
deployed. It deliberately does not reconstruct the balance each period owed on its own due
date: that would be more faithful, but it would raise the penalty of every customer who
paid after falling due, on the day of a deployment they were never told about.

Periods that have not fallen due yet keep all three columns NULL, which is what tells the
cycle they are still open questions.

Revision ID: 20260727_0009
Revises: 20260727_0008
Create Date: 2026-07-27 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260727_0009"
down_revision = "20260727_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("ALTER TABLE interest_charges ADD COLUMN IF NOT EXISTS penalty_amount DOUBLE PRECISION"))
    conn.execute(text("ALTER TABLE interest_charges ADD COLUMN IF NOT EXISTS penalty_rate_applied DOUBLE PRECISION"))
    conn.execute(text("ALTER TABLE interest_charges ADD COLUMN IF NOT EXISTS penalty_applied_at DATE"))

    # Mirrors interest_balance.py: interest owed per charge after the loan's advance pool is
    # consumed oldest period first. `pending_before` is what the earlier periods of the same
    # loan already took from that pool, so each charge only sees what is left of it.
    conn.execute(
        text(
            """
            WITH grace AS (
                SELECT COALESCE((SELECT default_grace_days FROM global_settings LIMIT 1), 0) AS days
            ),
            paid AS (
                SELECT interest_charge_id AS charge_id,
                       SUM(allocated_to_interest) AS interest
                  FROM payment_events
                 WHERE is_reversed = false
                   AND interest_charge_id IS NOT NULL
                 GROUP BY interest_charge_id
            ),
            advances AS (
                SELECT loan_id, SUM(allocated_to_interest) AS pool
                  FROM payment_events
                 WHERE is_reversed = false
                   AND interest_charge_id IS NULL
                   AND payment_type = 'interest_advance_payment'
                 GROUP BY loan_id
            ),
            base AS (
                SELECT c.id,
                       c.loan_id,
                       c.period_end,
                       GREATEST(0, c.amount - COALESCE(p.interest, 0)) AS pending,
                       l.late_penalty_rate AS rate,
                       -- Grace only postpones the penalty, so a loan that charges none gets none.
                       CASE WHEN l.late_penalty_rate > 0 THEN (SELECT days FROM grace) ELSE 0 END AS grace_days
                  FROM interest_charges c
                  JOIN loans l ON l.id = c.loan_id
                  LEFT JOIN paid p ON p.charge_id = c.id
            ),
            netted AS (
                SELECT b.*,
                       COALESCE(a.pool, 0) AS pool,
                       COALESCE(
                           SUM(b.pending) OVER (
                               PARTITION BY b.loan_id
                               ORDER BY b.period_end, b.id
                               ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                           ), 0) AS pending_before
                  FROM base b
                  LEFT JOIN advances a ON a.loan_id = b.loan_id
            ),
            frozen AS (
                SELECT n.id,
                       n.rate,
                       (n.period_end + (n.grace_days || ' days')::interval)::date AS due_date,
                       GREATEST(0, n.pending - LEAST(n.pending, GREATEST(0, n.pool - n.pending_before))) AS net_pending
                  FROM netted n
            )
            UPDATE interest_charges c
               SET penalty_amount = ROUND((f.net_pending * f.rate / 100)::numeric, 2),
                   penalty_rate_applied = f.rate,
                   penalty_applied_at = f.due_date
              FROM frozen f
             WHERE c.id = f.id
               AND c.penalty_applied_at IS NULL
               AND f.due_date < CURRENT_DATE
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE interest_charges DROP COLUMN IF EXISTS penalty_applied_at"))
    conn.execute(text("ALTER TABLE interest_charges DROP COLUMN IF EXISTS penalty_rate_applied"))
    conn.execute(text("ALTER TABLE interest_charges DROP COLUMN IF EXISTS penalty_amount"))
