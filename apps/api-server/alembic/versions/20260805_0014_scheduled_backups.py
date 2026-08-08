"""Recurring backups: the schedule, its destination, and the run history

Two new tables. `Base.metadata.create_all` at revision 0001 already gives a *fresh* database
both of them, so this only does work on a database that already exists at an older revision -
production. Hence the inspector guard: it is the `IF NOT EXISTS` of a `CREATE TABLE`, and it
lets `op.create_table` generate the right DDL for each dialect (SERIAL on PostgreSQL,
AUTOINCREMENT on SQLite) instead of this file hand writing SQL for both.

The schedule is its own table rather than more columns on `global_settings` because
`GET /settings` is readable by every authenticated role and these columns hold the OAuth
client secret and refresh token of the Google Drive account the archives are written to.

Revision ID: 20260805_0014
Revises: 20260729_0013
Create Date: 2026-08-05 00:00:00
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260805_0014"
down_revision = "20260729_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "backup_settings" not in existing_tables:
        op.create_table(
            "backup_settings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("frequency", sa.String(length=20), nullable=False, server_default="daily"),
            sa.Column("hour", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("day_of_week", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("day_of_month", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("destination", sa.String(length=30), nullable=False, server_default="local_directory"),
            sa.Column("local_directory", sa.String(length=500), nullable=True),
            sa.Column("retention_copies", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("drive_client_id", sa.String(length=255), nullable=True),
            sa.Column("drive_client_secret", sa.String(length=255), nullable=True),
            sa.Column("drive_refresh_token", sa.String(length=500), nullable=True),
            sa.Column("drive_account_email", sa.String(length=255), nullable=True),
            sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
            sa.Column(
                "drive_folder_name",
                sa.String(length=255),
                nullable=False,
                server_default="PawnPlatform Backups",
            ),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    if "backup_runs" not in existing_tables:
        op.create_table(
            "backup_runs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="success"),
            sa.Column("trigger", sa.String(length=20), nullable=False, server_default="scheduled"),
            sa.Column("destination", sa.String(length=30), nullable=False, server_default="local_directory"),
            sa.Column("filename", sa.String(length=255), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=True),
            sa.Column("total_rows", sa.Integer(), nullable=True),
            sa.Column("location", sa.String(length=500), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("triggered_by", sa.String(length=80), nullable=True),
        )
        # Named as the models declare them, so an upgraded database and a freshly created one
        # end up with the same schema.
        op.create_index("ix_backup_runs_id", "backup_runs", ["id"])
        op.create_index("ix_backup_runs_started_at", "backup_runs", ["started_at"])


def downgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())

    if "backup_runs" in existing_tables:
        op.drop_table("backup_runs")
    if "backup_settings" in existing_tables:
        op.drop_table("backup_settings")
