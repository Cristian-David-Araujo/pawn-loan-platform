"""Add parent payment link to payment events

Revision ID: 20260413_0002
Revises: 20260413_0001
Create Date: 2026-04-13 00:30:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260413_0002"
down_revision = "20260413_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_events", sa.Column("payment_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_payment_events_payment_id"), "payment_events", ["payment_id"], unique=False)
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
