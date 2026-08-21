"""Add protected customer identity documents and collateral photos.

Media belongs in the database in this deployment: it is client evidence, needs the same role
checks as the customer or pledge it belongs to, and the database is what the established
export/restore flow protects. A container-local upload directory would lose that evidence on
the next deploy and would leave backups incomplete.

Revision ID: 20260820_0020
Revises: 20260811_0019
Create Date: 2026-08-20 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260820_0020"
down_revision = "20260811_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    # The initial migration builds the *current* SQLAlchemy metadata on a fresh database, so
    # these statements must safely do nothing there while adding the tables on an older one.
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS customer_identity_documents (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL UNIQUE REFERENCES customers(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                content_type VARCHAR(100) NOT NULL,
                size_bytes INTEGER NOT NULL,
                content BYTEA NOT NULL,
                uploaded_by_id INTEGER NULL REFERENCES users(id),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_customer_identity_documents_customer_id "
            "ON customer_identity_documents (customer_id)"
        )
    )
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS collateral_photos (
                id SERIAL PRIMARY KEY,
                collateral_item_id INTEGER NOT NULL REFERENCES collateral_items(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                content_type VARCHAR(100) NOT NULL,
                size_bytes INTEGER NOT NULL,
                content BYTEA NOT NULL,
                uploaded_by_id INTEGER NULL REFERENCES users(id),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_collateral_photos_collateral_item_id "
            "ON collateral_photos (collateral_item_id)"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS collateral_photos"))
    conn.execute(text("DROP TABLE IF EXISTS customer_identity_documents"))
