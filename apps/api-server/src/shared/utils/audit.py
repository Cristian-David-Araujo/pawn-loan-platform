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
    commit: bool = True,
) -> None:
    """Record an operator action.

    Pass ``commit=False`` to enrol the row in the caller's transaction instead of committing
    it on its own. That is what any path that moves money should do: written afterwards, the
    audit row is a second transaction that can fail while the money stays moved, leaving a
    payment nobody appears to have taken. `delete_loan` has always done it this way.
    """
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
    if commit:
        db.commit()
