from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import GlobalSettings, User
from src.modules.settings.schemas import GlobalSettingsRead, GlobalSettingsUpdate
from src.domain.enums.user import UserRole
from src.shared.dependencies.auth import require_roles
from src.shared.dependencies.db import get_db
from src.shared.utils.audit import write_audit

router = APIRouter(prefix="/settings", tags=["settings"])


def _ensure_global_settings(db: Session) -> GlobalSettings:
    settings = db.get(GlobalSettings, 1)
    if settings is None:
        settings = GlobalSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=GlobalSettingsRead)
def get_global_settings(
    db: Session = Depends(get_db),
) -> GlobalSettings:
    return _ensure_global_settings(db)


@router.put("", response_model=GlobalSettingsRead)
def update_global_settings(
    payload: GlobalSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.administrator)),
) -> GlobalSettings:
    settings = _ensure_global_settings(db)

    if payload.app_name is not None:
        settings.app_name = payload.app_name
    
    settings.company_name = payload.company_name
    settings.company_document_type = payload.company_document_type
    settings.company_document_number = payload.company_document_number
    settings.company_address = payload.company_address
    settings.company_phone = payload.company_phone
    settings.company_email = payload.company_email

    settings.currency_code = payload.currency_code.upper()
    settings.timezone = payload.timezone
    settings.date_format = payload.date_format
    settings.default_late_penalty_rate = payload.default_late_penalty_rate
    if payload.interest_generation_lead_days is not None:
        settings.interest_generation_lead_days = max(0, payload.interest_generation_lead_days)

    db.commit()
    db.refresh(settings)

    write_audit(
        db,
        action="update_global_settings",
        entity_type="GlobalSettings",
        entity_id=str(settings.id),
        user=current_user,
        new_data=(
            f"currency={settings.currency_code},timezone={settings.timezone},"
            f"date_format={settings.date_format},default_late_penalty_rate={settings.default_late_penalty_rate},"
            f"interest_generation_lead_days={settings.interest_generation_lead_days}"
        ),
    )

    return settings
