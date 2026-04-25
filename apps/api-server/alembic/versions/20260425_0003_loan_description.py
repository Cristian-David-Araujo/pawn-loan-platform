"""Add description column to loans

Revision ID: 20260425_0003
Revises: 20260413_0002
Create Date: 2026-04-25 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260425_0003"
down_revision = "20260413_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE loans ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''"
    ))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE loans DROP COLUMN IF EXISTS description"
    ))
