"""Voiding a charge, pausing a loan, settling a loan for less

Three operator escape hatches, all of which forgive money, and all of which therefore record
who did it, when, and why on the row itself — the audit table has no read path in the
application, so a column is the only place a reason can actually be read back.

- `interest_charges.voided_*` — a charge that should never have been billed. The row stays,
  which keeps its `(period_start, period_end)` slot occupied and stops the generator from
  billing that month again on the next cycle.
- `loans.interest_paused*` — stop the clock without ending the debt. A flag rather than a
  `LoanStatus` value: a paused loan is still `active` or `overdue`, resuming has to return it
  to whichever it was, and `LoanStatus` is a native PG enum whose type would need altering.
- `loans.settle*` / `written_off_*` — a negotiated settlement. The loan closes as `closed`;
  these columns are what let a report separate a settlement from a normal payoff.

`IF NOT EXISTS` throughout, because the initial migration is `Base.metadata.create_all`: a
fresh database already has every current column at revision 0001 and this must be a no-op
there, while doing real work on a database that exists at an older revision.

Revision ID: 20260809_0017
Revises: 20260808_0016
Create Date: 2026-08-09 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260809_0017"
down_revision = "20260808_0016"
branch_labels = None
depends_on = None

INTEREST_CHARGE_COLUMNS = (
    "voided_at TIMESTAMP NULL",
    "voided_by INTEGER NULL REFERENCES users(id)",
    "void_reason TEXT NOT NULL DEFAULT ''",
)

LOAN_COLUMNS = (
    "interest_paused BOOLEAN NOT NULL DEFAULT FALSE",
    "interest_paused_at TIMESTAMP NULL",
    "interest_paused_by INTEGER NULL REFERENCES users(id)",
    "interest_pause_reason TEXT NOT NULL DEFAULT ''",
    "settled_at TIMESTAMP NULL",
    "settled_by INTEGER NULL REFERENCES users(id)",
    "settlement_reason TEXT NOT NULL DEFAULT ''",
    "settlement_amount DOUBLE PRECISION NULL",
    "written_off_principal DOUBLE PRECISION NULL",
    "written_off_interest DOUBLE PRECISION NULL",
)


def _column_name(definition: str) -> str:
    return definition.split(" ", 1)[0]


def upgrade() -> None:
    conn = op.get_bind()

    for definition in INTEREST_CHARGE_COLUMNS:
        conn.execute(text(f"ALTER TABLE interest_charges ADD COLUMN IF NOT EXISTS {definition}"))

    for definition in LOAN_COLUMNS:
        conn.execute(text(f"ALTER TABLE loans ADD COLUMN IF NOT EXISTS {definition}"))

    # Every read of pending interest filters on `voided_at IS NULL`, and the collection
    # screens are the hottest path in the product.
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_interest_charges_loan_voided "
            "ON interest_charges (loan_id, voided_at)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("DROP INDEX IF EXISTS ix_interest_charges_loan_voided"))

    for definition in LOAN_COLUMNS:
        conn.execute(text(f"ALTER TABLE loans DROP COLUMN IF EXISTS {_column_name(definition)}"))

    for definition in INTEREST_CHARGE_COLUMNS:
        conn.execute(
            text(f"ALTER TABLE interest_charges DROP COLUMN IF EXISTS {_column_name(definition)}")
        )
