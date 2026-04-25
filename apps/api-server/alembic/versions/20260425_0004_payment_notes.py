"""Add notes column to payments

Revision ID: 20260425_0004
Revises: 20260425_0003
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260425_0004"
down_revision = "20260425_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE payments ADD COLUMN IF NOT EXISTS notes TEXT NOT NULL DEFAULT ''"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE payments DROP COLUMN IF EXISTS notes"
    ))
