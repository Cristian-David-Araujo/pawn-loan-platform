"""Remove loan applications

`POST/GET /loan-applications` and `/loan-applications/{id}/approve` existed and wrote audit
rows, but nothing ever called them. The web client creates loans directly, `Loan.application_id`
was nullable and stayed `NULL` on every row, and approval only stamped a varchar — it did not
create the loan. A state machine nobody drives is worse than no state machine: it advertises an
approval gate in front of lending that does not exist.

The column goes before the table, or the foreign key holds it. Both use `IF EXISTS`, because
the initial migration is `Base.metadata.create_all`: a database created after this never had
either, and the statements must be no-ops there while doing real work on one that did.

Older archives are unaffected in the way that matters — the restore already refuses anything
whose `schema_revision` does not match the database, so an archive taken before this was
already out of scope rather than newly broken by it.

Revision ID: 20260810_0018
Revises: 20260809_0017
Create Date: 2026-08-10 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260810_0018"
down_revision = "20260809_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE loans DROP COLUMN IF EXISTS application_id"))
    conn.execute(text("DROP TABLE IF EXISTS loan_applications"))


def downgrade() -> None:
    """Recreates the shape, not the data.

    The applications themselves are gone and cannot be recovered from here. Downgrading
    restores an empty table and a null column so an older revision of the code can start; it
    does not restore a feature that had no users.
    """
    conn = op.get_bind()
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS loan_applications (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                loan_type VARCHAR(20) NOT NULL,
                requested_amount DOUBLE PRECISION NOT NULL,
                monthly_interest_rate DOUBLE PRECISION NOT NULL,
                term_months INTEGER NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                status VARCHAR(20) NOT NULL DEFAULT 'submitted',
                reviewed_by INTEGER NULL REFERENCES users(id),
                approved_by INTEGER NULL REFERENCES users(id),
                created_at TIMESTAMP NULL
            )
            """
        )
    )
    conn.execute(
        text(
            "ALTER TABLE loans ADD COLUMN IF NOT EXISTS application_id INTEGER "
            "NULL REFERENCES loan_applications(id)"
        )
    )
