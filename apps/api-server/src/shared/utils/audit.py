from sqlalchemy.orm import Session

from src.infrastructure.persistence.models import AuditLog, User


def write_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    user: User | None = None,
    old_data: str = "",
    new_data: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
        )
    )
    db.commit()
