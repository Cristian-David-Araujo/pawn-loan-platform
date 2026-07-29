"""Record the principal a billing period was charged on

`amount` was `outstanding_principal * monthly_interest_rate / 100` evaluated against the
loan's balance *at the moment the cycle ran*, which equals the balance the period actually
carried only while the cycle is on time. With the scheduler stopped for three months, a
customer who paid 700.000 off a 1.000.000 loan in between had all three backlogged periods
billed on the remaining 300.000 — the two months they owed the full principal for were
billed at a third of their value, and nothing on the row said so.

The generator now bills each period on the balance it carried at its `period_end`, rebuilt
from the standing principal allocations, and stores that base here so the figure can be
audited instead of re-derived from a balance that keeps moving.

Existing rows keep NULL: what they were billed on cannot be reconstructed after the fact,
and inventing a base would make a guess look like a record.

Revision ID: 20260729_0013
Revises: 20260728_0012
Create Date: 2026-07-29 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260729_0013"
down_revision = "20260728_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE interest_charges ADD COLUMN IF NOT EXISTS principal_base DOUBLE PRECISION"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE interest_charges DROP COLUMN IF EXISTS principal_base"))
