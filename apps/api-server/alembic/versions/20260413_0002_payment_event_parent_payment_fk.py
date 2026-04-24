"""Add parent payment link to payment events

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13 00:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260413_0002"
down_revision = "20260413_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Migration 0001 uses Base.metadata.create_all() which captures the current
    # model state. If this migration was already included in the model when 0001
    # ran (fresh install), the column and index already exist — use IF NOT EXISTS
    # to stay idempotent.
    conn.execute(text(
        "ALTER TABLE payment_events ADD COLUMN IF NOT EXISTS payment_id INTEGER"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_payment_events_payment_id ON payment_events (payment_id)"
    ))

    has_fk = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = 'fk_payment_events_payment_id_payments'"
    )).fetchone()
    if not has_fk:
        op.create_foreign_key(
            "fk_payment_events_payment_id_payments",
            "payment_events",
            "payments",
            ["payment_id"],
            ["id"],
        )


def downgrade() -> None:
    op.drop_constraint("fk_payment_events_payment_id_payments", "payment_events", type_="foreignkey")
    op.drop_index(op.f("ix_payment_events_payment_id"), table_name="payment_events")
    op.drop_column("payment_events", "payment_id")
