"""
Account lifecycle operations (challenge + soft delete).
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_email
from app.models.system_audit import AuditEvent
from app.models.user import User
from app.services.supabase_admin import supabase_admin_service

logger = logging.getLogger(__name__)

DELETE_CONFIRM_TEXT = "ELIMINAR"
CHALLENGE_TTL_MINUTES = 30


@dataclass
class DeleteChallengeRecord:
    token_hash: str
    expires_at: datetime


_DELETE_CHALLENGES: dict[UUID, DeleteChallengeRecord] = {}


def _hash_token(user_id: UUID, token: str) -> str:
    return hashlib.sha256(f"{user_id}:{token}".encode("utf-8")).hexdigest()


def _build_challenge_email(recipient: str, token: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_USER or "no-reply@forestguard.ar"
    msg["To"] = recipient
    msg["Subject"] = "ForestGuard - token de eliminacion de cuenta"
    msg.set_content(
        (
            "Recibimos una solicitud de eliminacion de cuenta.\n\n"
            f"Tu token temporal es: {token}\n"
            f"Validez: {CHALLENGE_TTL_MINUTES} minutos.\n\n"
            "Si no fuiste vos, ignora este mensaje."
        )
    )
    return msg


async def issue_delete_challenge(user: User) -> None:
    if not user.email:
        return

    token = f"{secrets.randbelow(1_000_000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CHALLENGE_TTL_MINUTES)
    _DELETE_CHALLENGES[user.id] = DeleteChallengeRecord(
        token_hash=_hash_token(user.id, token),
        expires_at=expires_at,
    )

    try:
        await send_email(_build_challenge_email(user.email, token))
    except Exception:
        # Neutral response: challenge issuance endpoint must not leak internals.
        logger.exception("Failed to deliver delete challenge email")


def verify_delete_challenge(user_id: UUID, provided_token: str) -> bool:
    if not provided_token:
        return False
    record = _DELETE_CHALLENGES.get(user_id)
    if not record:
        return False
    if datetime.now(timezone.utc) > record.expires_at:
        _DELETE_CHALLENGES.pop(user_id, None)
        return False

    expected_hash = record.token_hash
    if expected_hash != _hash_token(user_id, provided_token.strip()):
        return False

    _DELETE_CHALLENGES.pop(user_id, None)
    return True


def verify_password_for_delete(user: User, password: str) -> bool:
    if not user.email or not password:
        return False
    return supabase_admin_service.verify_password(user.email, password)


def soft_delete_account(
    db: Session,
    user: User,
    deletion_reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> User:
    now = datetime.now(timezone.utc)

    db.execute(
        text(
            """
            UPDATE citizen_reports
            SET reporter_user_id = NULL
            WHERE reporter_user_id = :user_id
            """
        ),
        {"user_id": str(user.id)},
    )

    if not user.is_deleted:
        user.is_deleted = True
        user.deleted_at = now
        user.deletion_reason = (deletion_reason or "user_request")[:255]

        if user.email and not user.email.startswith("deleted+"):
            user.email = f"deleted+{user.id}@forestguard.local"
        user.full_name = "Deleted User"

        db.add(
            AuditEvent(
                principal_id=str(user.id),
                principal_role=user.role,
                action="account_delete",
                resource_type="user",
                resource_id=user.id,
                details={
                    "reason": user.deletion_reason,
                    "preserved_citizen_reports": True,
                },
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )

    db.commit()
    db.refresh(user)

    # Best effort: revoke active sessions on Supabase side.
    supabase_admin_service.revoke_user_sessions(user.id)

    return user
