"""Record who wrote a loan's balance off, when, and why

`POST /loans/{id}/close` with `force: true` closed a loan over whatever it still owed —
principal and accrued interest both — without asking for grounds and without leaving a trace
on the row. The debt simply stopped being collectable, with nobody's name on the decision.

Same treatment a payment reversal already gets, and for the same reason: the audit table has
no read path anywhere in the application, so a written-off loan has to be able to explain
itself from its own row.

Existing forced closures cannot be reconstructed — nothing distinguished them from an
ordinary settlement — so they keep an empty reason. The columns only describe closures made
from here on.

Revision ID: 20260728_0012
Revises: 20260728_0011
Create Date: 2026-07-28 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260728_0012"
down_revision = "20260728_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS force_closed_reason TEXT NOT NULL DEFAULT ''"))
    conn.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS force_closed_at TIMESTAMP WITHOUT TIME ZONE"))
    conn.execute(text("ALTER TABLE loans ADD COLUMN IF NOT EXISTS force_closed_by INTEGER REFERENCES users(id)"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE loans DROP COLUMN IF EXISTS force_closed_by"))
    conn.execute(text("ALTER TABLE loans DROP COLUMN IF EXISTS force_closed_at"))
    conn.execute(text("ALTER TABLE loans DROP COLUMN IF EXISTS force_closed_reason"))
