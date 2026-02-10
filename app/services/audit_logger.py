from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.system_audit import AuditEvent


class AuditLogger:
    """
    Service to handle persistent audit logging.
    Can be used synchronously or injected via BackgroundTasks in Controllers.
    """

    @staticmethod
    def log(
        db: Session,
        action: str,
        principal_id: str = "anonymous",
        principal_role: str = "public",
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Record a critical system action.
        """
        try:
            event = AuditEvent(
                principal_id=principal_id,
                principal_role=principal_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            db.add(event)
            db.commit()
        except Exception as e:
            # Audit logging failure should generally not block the main transaction,
            # but needs to be logged heavily.
            # In high security, we might want to raising/rollback.
            print(f"FAILED TO AUDIT LOG: {e}")
            db.rollback()
