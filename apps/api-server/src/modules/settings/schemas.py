from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GlobalSettingsUpdate(BaseModel):
    app_name: str
    company_name: str | None = None
    company_document_type: str | None = None
    company_document_number: str | None = None
    company_address: str | None = None
    company_phone: str | None = None
    company_email: str | None = None
    currency_code: str
    timezone: str
    date_format: str
    default_late_penalty_rate: float
    interest_generation_lead_days: int | None = None
    default_grace_days: int | None = None


class GlobalSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_name: str
    company_name: str | None
    company_document_type: str | None
    company_document_number: str | None
    company_address: str | None
    company_phone: str | None
    company_email: str | None
    currency_code: str
    timezone: str
    date_format: str
    default_late_penalty_rate: float
    interest_generation_lead_days: int
    default_grace_days: int
    updated_at: datetime
