from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.modules.backup.destinations import DESTINATIONS
from src.modules.backup.schedule import FREQUENCIES, MAX_DAY_OF_MONTH


class ImportTablePlan(BaseModel):
    name: str
    current_rows: int
    incoming_rows: int


class ImportResultRead(BaseModel):
    """Outcome of an analysis or of an applied restore."""

    imported: bool
    can_import: bool
    format_version: str | None
    archive_schema_revision: str | None
    database_schema_revision: str | None
    archive_generated_at: str | None
    total_current_rows: int
    total_incoming_rows: int
    tables: list[ImportTablePlan]
    errors: list[str]
    warnings: list[str]


class BackupScheduleUpdate(BaseModel):
    """The recurring backup schedule as the administrator sets it.

    The Google credentials are deliberately absent: ``client_id``/``client_secret`` arrive
    with the authorisation flow and the refresh token is never sent by a client at all.
    """

    enabled: bool
    frequency: str
    hour: int = Field(ge=0, le=23)
    day_of_week: int = Field(default=1, ge=1, le=7)
    day_of_month: int = Field(default=1, ge=1, le=MAX_DAY_OF_MONTH)
    destination: str
    local_directory: str | None = None
    retention_copies: int = Field(default=7, ge=0, le=365)
    drive_folder_name: str | None = None

    @field_validator("frequency")
    @classmethod
    def _known_frequency(cls, value: str) -> str:
        if value not in FREQUENCIES:
            raise ValueError(f"frequency must be one of {', '.join(FREQUENCIES)}")
        return value

    @field_validator("destination")
    @classmethod
    def _known_destination(cls, value: str) -> str:
        if value not in DESTINATIONS:
            raise ValueError(f"destination must be one of {', '.join(DESTINATIONS)}")
        return value


class BackupRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    trigger: str
    destination: str
    filename: str | None
    size_bytes: int | None
    total_rows: int | None
    location: str | None
    error: str | None
    triggered_by: str | None


class BackupScheduleRead(BaseModel):
    """The schedule, plus what the administrator needs to judge whether it is working.

    No credential is ever returned — only ``drive_connected`` and the account's email, so the
    UI can show which Google account the copies go to. The OAuth client secret and refresh
    token leave the database for exactly one purpose, which is talking to Google.
    """

    enabled: bool
    frequency: str
    hour: int
    day_of_week: int
    day_of_month: int
    destination: str
    # What the administrator chose, empty when nothing was chosen. Reported separately from the
    # path actually used so an installation that never set one keeps following
    # `BACKUP_LOCAL_DIRECTORY` — saving the resolved value back would freeze the old path the
    # day a deploy moves the volume.
    local_directory: str
    local_directory_effective: str
    retention_copies: int
    drive_connected: bool
    drive_account_email: str | None
    drive_folder_name: str
    drive_folder_id: str | None
    # Absolute local time of the next slot, so "every day at 2am" can be read back as a date.
    next_run_at: datetime | None
    last_run: BackupRunRead | None
    last_successful_run: BackupRunRead | None


class DriveAuthorizationRead(BaseModel):
    """What the browser needs to start the Google consent flow."""

    authorization_url: str
    redirect_uri: str
    state: str


class DriveAuthorizationStart(BaseModel):
    client_id: str = Field(min_length=10)
    client_secret: str = Field(min_length=10)
    # Must match a redirect URI registered on the OAuth client, character for character.
    redirect_uri: str = Field(min_length=8)


class DriveConnectRequest(BaseModel):
    code: str = Field(min_length=8)
    redirect_uri: str = Field(min_length=8)
    state: str | None = None


class DestinationTestRead(BaseModel):
    ok: bool
    destination: str
    detail: str
