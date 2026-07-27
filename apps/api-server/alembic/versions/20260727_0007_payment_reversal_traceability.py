"""Record who reversed a payment, when, and why

Reversal is the only way a payment is ever "deleted", so the row has to carry the
accountability itself. Before this the ledger only had a bare ``is_reversed`` boolean:
you could see that money had been taken back but not by whom, when, or on what grounds.

Revision ID: 20260727_0007
Revises: 20260725_0006
Create Date: 2026-07-27 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260727_0007"
down_revision = "20260725_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE payments ADD COLUMN IF NOT EXISTS reversed_at TIMESTAMP WITHOUT TIME ZONE"))
    conn.execute(text("ALTER TABLE payments ADD COLUMN IF NOT EXISTS reversed_by INTEGER"))
    conn.execute(text("ALTER TABLE payments ADD COLUMN IF NOT EXISTS reversal_reason TEXT NOT NULL DEFAULT ''"))
    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'payments_reversed_by_fkey'
                ) THEN
                    ALTER TABLE payments
                        ADD CONSTRAINT payments_reversed_by_fkey
                        FOREIGN KEY (reversed_by) REFERENCES users (id);
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_reversed_by_fkey"))
    conn.execute(text("ALTER TABLE payments DROP COLUMN IF EXISTS reversal_reason"))
    conn.execute(text("ALTER TABLE payments DROP COLUMN IF EXISTS reversed_by"))
    conn.execute(text("ALTER TABLE payments DROP COLUMN IF EXISTS reversed_at"))
