"""The product is called Mutuum

`GlobalSettings.app_name` is what the sidebar, the login card and the printed footer show,
and it defaulted to the placeholder `PawnPlatform`. Changing the model default alone only
reaches installations created after this, so every existing deployment would keep showing
the placeholder until somebody noticed and retyped it in the settings screen.

Only rows still holding that exact default are renamed. The field is deliberately editable —
its help text is "the name displayed in the top bar" — so an operator who typed their own
name has made a decision, and a migration is the wrong place to overrule it. The column
default is dropped to `Mutuum` too, because `a8b6082a41d5` pinned the old literal as a
server-side default and a row inserted by anything other than the ORM would still get it.

`BackupSettings.drive_folder_name` is left alone on purpose, despite carrying the same
placeholder. It is paired with `drive_folder_id`: the id is what uploads actually go to, and
the router nulls it whenever the name changes precisely so the two cannot disagree. Renaming
the name here without touching the id would leave the settings screen labelling a folder the
archives do not land in; nulling the id instead would silently start a second folder in the
operator's Drive and orphan the copies already there. New installations get the new default
from the model. An operator who wants an existing folder renamed does it from the settings
screen, which handles the pair correctly.

Revision ID: 20260807_0015
Revises: 20260805_0014
Create Date: 2026-08-07 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260807_0015"
down_revision = "20260805_0014"
branch_labels = None
depends_on = None

OLD_NAME = "PawnPlatform"
NEW_NAME = "Mutuum"


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("UPDATE global_settings SET app_name = :new WHERE app_name = :old"),
        {"new": NEW_NAME, "old": OLD_NAME},
    )
    conn.execute(text(f"ALTER TABLE global_settings ALTER COLUMN app_name SET DEFAULT '{NEW_NAME}'"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("UPDATE global_settings SET app_name = :old WHERE app_name = :new"),
        {"old": OLD_NAME, "new": NEW_NAME},
    )
    conn.execute(text(f"ALTER TABLE global_settings ALTER COLUMN app_name SET DEFAULT '{OLD_NAME}'"))
