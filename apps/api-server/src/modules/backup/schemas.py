from pydantic import BaseModel


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
