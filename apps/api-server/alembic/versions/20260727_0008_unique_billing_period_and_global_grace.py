"""Make duplicate billing periods impossible and move grace days to a global setting

Two separate defects, fixed together because they share the same root: policy that lived
where it should not.

1. `POST /interest/generate` did not take the advisory lock the scheduler uses, so both
   could generate the same billing period at once. Nothing at the database level rejected
   the duplicate, and customers were charged — and in some cases paid — twice. The unique
   constraint added here is what actually guarantees it cannot happen again; the lock only
   makes the collision rare.

2. Grace days came from `Loan.due_day`, which the create form filled with the day-of-month
   of the disbursement date. A loan signed on the 25th silently got 25 days of grace and one
   signed on the 3rd got three. Grace is a portfolio policy, so it becomes a global setting
   and every existing loan is normalised onto it.

Deduplication keeps the lowest id of each group and re-points its ledger rows, so money
already received stays recorded against the surviving charge. Nothing is deleted that a
payment ever touched.

Revision ID: 20260727_0008
Revises: 20260727_0007
Create Date: 2026-07-27 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260727_0008"
down_revision = "20260727_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("ALTER TABLE global_settings ADD COLUMN IF NOT EXISTS default_grace_days INTEGER NOT NULL DEFAULT 0"))

    # Move every ledger row off the duplicates and onto the surviving charge, so the money
    # keeps pointing at a real period instead of being orphaned by the delete below.
    conn.execute(
        text(
            """
            WITH ranked AS (
                SELECT id, loan_id, period_start, period_end,
                       MIN(id) OVER (PARTITION BY loan_id, period_start, period_end) AS keep_id
                FROM interest_charges
            )
            UPDATE payment_events e
               SET interest_charge_id = r.keep_id
              FROM ranked r
             WHERE e.interest_charge_id = r.id
               AND r.id <> r.keep_id
            """
        )
    )

    conn.execute(
        text(
            """
            DELETE FROM interest_charges c
             USING (
                SELECT id, MIN(id) OVER (PARTITION BY loan_id, period_start, period_end) AS keep_id
                  FROM interest_charges
             ) r
             WHERE c.id = r.id AND r.id <> r.keep_id
            """
        )
    )

    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'uq_interest_charge_period'
                ) THEN
                    ALTER TABLE interest_charges
                        ADD CONSTRAINT uq_interest_charge_period
                        UNIQUE (loan_id, period_start, period_end);
                END IF;
            END $$;
            """
        )
    )

    # Existing loans carry the accidental grace taken from their disbursement day; line them
    # up with the policy so no loan keeps a value nobody chose.
    conn.execute(
        text("UPDATE loans SET due_day = COALESCE((SELECT default_grace_days FROM global_settings LIMIT 1), 0)")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE interest_charges DROP CONSTRAINT IF EXISTS uq_interest_charge_period"))
    conn.execute(text("ALTER TABLE global_settings DROP COLUMN IF EXISTS default_grace_days"))
