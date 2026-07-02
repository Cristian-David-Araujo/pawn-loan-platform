"""add_defaulted_status

Revision ID: 4204eb05a02c
Revises: 20260625_0005
Create Date: 2026-06-20 16:16:17.683487
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4204eb05a02c'
down_revision = '20260625_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside the migration transaction
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE loanstatus ADD VALUE IF NOT EXISTS 'defaulted'")


def downgrade() -> None:
    # Downgrading enum values in PG is non-trivial and often unnecessary
    pass
