from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GlobalSettingsUpdate(BaseModel):
    currency_code: str
    timezone: str
    date_format: str
    default_late_penalty_rate: float
    interest_generation_lead_days: int | None = None


class GlobalSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency_code: str
    timezone: str
    date_format: str
    default_late_penalty_rate: float
    interest_generation_lead_days: int
    updated_at: datetime
