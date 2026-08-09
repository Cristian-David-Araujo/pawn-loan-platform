"""The product name is not an installation setting

`GlobalSettings.app_name` was editable from the settings screen, described as "the name
displayed in the top bar". That was wrong: it is the name of the product, not something an
installation chooses, and the field being editable is what let two names exist at once.

With the field gone from the form and from `GlobalSettingsUpdate`, any value other than
`Mutuum` is now unreachable — no screen can display it as editable and no endpoint can
change it back. So every row is normalised, not just the ones still holding the old
placeholder. `20260807_0015` deliberately spared custom values because the field was a
decision the operator was allowed to make; that reasoning ends the moment the decision is
taken away, and leaving one behind would strand an installation showing a name nobody can
correct without database access.

`BackupSettings.drive_folder_name` carried the same placeholder, and `0015` left it alone
for a reason worth restating: the name is paired with `drive_folder_id`, which is where the
archives actually land. `PUT /backup/schedule` nulls the id whenever the name changes, so
the two can never disagree. A migration that renamed the name and kept the id would put the
settings screen's label on a folder the copies do not go to; nulling the id instead would
quietly start a second folder in the operator's Drive and orphan the archives already in the
first.

So the rename here is restricted to rows where **no folder has been created yet**
(`drive_folder_id IS NULL`) — there the pair cannot disagree, because there is no folder to
disagree with. An installation already uploading keeps both values as they are, and its
operator renames the folder from the settings screen, which handles the pair correctly. The
column default moves regardless, because `20260805_0014` pinned the old literal server-side
and a row inserted by anything other than the ORM would still receive it.

Revision ID: 20260808_0016
Revises: 20260807_0015
Create Date: 2026-08-08 00:00:00
"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "20260808_0016"
down_revision = "20260807_0015"
branch_labels = None
depends_on = None

PRODUCT_NAME = "Mutuum"
OLD_FOLDER_NAME = "PawnPlatform Backups"
NEW_FOLDER_NAME = "Mutuum Backups"


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        text("UPDATE global_settings SET app_name = :name WHERE app_name <> :name"),
        {"name": PRODUCT_NAME},
    )

    conn.execute(
        text(
            "UPDATE backup_settings SET drive_folder_name = :new "
            "WHERE drive_folder_name = :old AND drive_folder_id IS NULL"
        ),
        {"new": NEW_FOLDER_NAME, "old": OLD_FOLDER_NAME},
    )
    conn.execute(
        text(f"ALTER TABLE backup_settings ALTER COLUMN drive_folder_name SET DEFAULT '{NEW_FOLDER_NAME}'")
    )


def downgrade() -> None:
    """Restores the folder name and the column default.

    `app_name` is not restored, and cannot be: the values this replaced were whatever each
    installation had typed, and they are gone. Downgrading leaves every row reading `Mutuum`,
    which is the product's name either way — the loss is a customisation that the version
    being downgraded to allowed and this one does not.
    """
    conn = op.get_bind()

    conn.execute(
        text(
            "UPDATE backup_settings SET drive_folder_name = :old "
            "WHERE drive_folder_name = :new AND drive_folder_id IS NULL"
        ),
        {"old": OLD_FOLDER_NAME, "new": NEW_FOLDER_NAME},
    )
    conn.execute(
        text(f"ALTER TABLE backup_settings ALTER COLUMN drive_folder_name SET DEFAULT '{OLD_FOLDER_NAME}'")
    )
