"""One key, one payment

A double-clicked submit was two payments. The row lock added earlier stops two cashiers
racing on the same balance; it does nothing about the same cashier sending the same
collection twice because the connection was slow and the button still looked live.

The column is nullable and the index is unique. Every payment recorded before this carries
NULL, and in PostgreSQL a unique index treats NULLs as distinct — so history does not become
a pile of duplicates of each other.

Revision ID: 20260811_0019
Revises: 20260810_0018
Create Date: 2026-08-11 00:00:00
"""

from alembic import op
from sqlalchemy import text

revision = "20260811_0019"
down_revision = "20260810_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE payments ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(64) NULL"))
    conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_idempotency_key "
            "ON payments (idempotency_key)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP INDEX IF EXISTS uq_payments_idempotency_key"))
    conn.execute(text("ALTER TABLE payments DROP COLUMN IF EXISTS idempotency_key"))
