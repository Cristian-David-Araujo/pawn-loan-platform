"""Add is_reversed flag to payment_events

Revision ID: 20260725_0006
Revises: d94e8344fe17
Create Date: 2026-07-25 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260725_0006"
down_revision = "d94e8344fe17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS is_reversed BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    # Backfill ledger rows whose parent payment was already reversed, otherwise their
    # allocations would keep cancelling interest that was actually returned.
    conn.execute(text(
        "UPDATE payment_events SET is_reversed = TRUE "
        "WHERE payment_id IN (SELECT id FROM payments WHERE is_reversed = TRUE)"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE payment_events DROP COLUMN IF EXISTS is_reversed"
    ))
