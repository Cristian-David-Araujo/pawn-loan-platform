"""add user password reset token columns

Revision ID: 20260625_0005
Revises: d053de0e094c
Create Date: 2026-06-25 13:42:00.000000
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '20260625_0005'
down_revision = 'd053de0e094c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expires_at TIMESTAMP")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_reset_token ON users (reset_token)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_reset_token")
    op.drop_column('users', 'reset_token_expires_at')
    op.drop_column('users', 'reset_token')
