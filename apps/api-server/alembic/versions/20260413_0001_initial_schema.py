"""Initial schema

Revision ID: 20260413_0001
Revises:
Create Date: 2026-04-13 00:00:00
"""

from alembic import op

from src.infrastructure.persistence.database import Base
from src.infrastructure.persistence import models as _models  # noqa: F401

# revision identifiers, used by Alembic.
revision = "20260413_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
