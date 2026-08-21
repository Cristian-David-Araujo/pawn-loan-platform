"""Store identity document front and back as separate, replaceable scans.

Revision ID: 20260820_0021
Revises: 20260820_0020
Create Date: 2026-08-20 00:05:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260820_0021"
down_revision = "20260820_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # Existing one-file uploads become the front side. Fresh databases already receive this
    # column from the current metadata in migration 0001, so every operation is idempotent.
    conn.execute(
        text(
            "ALTER TABLE customer_identity_documents "
            "ADD COLUMN IF NOT EXISTS side VARCHAR(12) NOT NULL DEFAULT 'front'"
        )
    )
    conn.execute(
        text(
            "ALTER TABLE customer_identity_documents "
            "DROP CONSTRAINT IF EXISTS customer_identity_documents_customer_id_key"
        )
    )
    conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_identity_documents_customer_side "
            "ON customer_identity_documents (customer_id, side)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    # On a fresh install, revision 0001 creates the current metadata and this name belongs
    # to a UNIQUE constraint. On an upgrade from 0020 it is the explicit index made above.
    # PostgreSQL will not drop an index that backs a constraint, so handle both origins.
    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'uq_customer_identity_documents_customer_side'
                      AND conrelid = 'customer_identity_documents'::regclass
                ) THEN
                    ALTER TABLE customer_identity_documents
                    DROP CONSTRAINT uq_customer_identity_documents_customer_side;
                ELSE
                    DROP INDEX IF EXISTS uq_customer_identity_documents_customer_side;
                END IF;
            END $$;
            """
        )
    )
    # Downgrading can only keep one side because revision 0020 has a unique customer id.
    conn.execute(text("DELETE FROM customer_identity_documents WHERE side <> 'front'"))
    conn.execute(
        text(
            "ALTER TABLE customer_identity_documents "
            "ADD CONSTRAINT customer_identity_documents_customer_id_key UNIQUE (customer_id)"
        )
    )
    conn.execute(text("ALTER TABLE customer_identity_documents DROP COLUMN IF EXISTS side"))
