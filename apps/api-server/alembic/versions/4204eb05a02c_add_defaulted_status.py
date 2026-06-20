"""add_defaulted_status

Revision ID: 4204eb05a02c
Revises: d053de0e094c
Create Date: 2026-06-20 16:16:17.683487
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4204eb05a02c'
down_revision = 'd053de0e094c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Commit any existing transaction since ALTER TYPE cannot run inside a transaction block
    op.execute("COMMIT")
    op.execute("ALTER TYPE loanstatus ADD VALUE IF NOT EXISTS 'defaulted'")


def downgrade() -> None:
    # Downgrading enum values in PG is non-trivial and often unnecessary
    pass
