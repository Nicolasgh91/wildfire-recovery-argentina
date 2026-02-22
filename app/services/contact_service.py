from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.core.email import send_email
from app.core.email_config import email_config
from app.schemas.contact import ContactAttachmentMeta, ContactRequest

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5MB


@dataclass
class ContactAttachment:
    """Attachment payload for contact requests."""
    meta: ContactAttachmentMeta
    content: bytes


class ContactService:
    """Service to validate and deliver contact emails."""
    def _validate_content_type(self, content_type: Optional[str]) -> None:
        if content_type is None:
            return
        if content_type == "application/octet-stream":
            return
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported attachment type.",
            )

    async def read_attachment(self, attachment: UploadFile) -> ContactAttachment:
        if not attachment.filename:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Attachment filename is required.",
            )

        ext = Path(attachment.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Unsupported attachment extension.",
            )

        self._validate_content_type(attachment.content_type)

        content = await attachment.read()
        size = len(content)
        if size > MAX_ATTACHMENT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Attachment exceeds 5MB limit.",
            )

        sha256 = hashlib.sha256(content).hexdigest()
        meta = ContactAttachmentMeta(
            filename=attachment.filename,
            content_type=attachment.content_type or "application/octet-stream",
            size_bytes=size,
            sha256=sha256,
        )

        logger.info(
            "Contact attachment received filename=%s size=%s sha256=%s",
            meta.filename,
            meta.size_bytes,
            meta.sha256,
        )

        return ContactAttachment(meta=meta, content=content)

    def build_email_message(
        self,
        request_id: str,
        request: ContactRequest,
        attachment: Optional[ContactAttachment],
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = settings.SMTP_USER or email_config.DEFAULT_FROM
        msg["To"] = email_config.ADMIN_EMAIL
        msg["Reply-To"] = request.email
        msg["Subject"] = f"[ForestGuard] Contacto #{request_id} - {request.subject}"

        body_lines = [
            "Nueva solicitud de contacto (UC-F01)",
            f"ID: {request_id}",
            f"Nombre: {request.name}",
            f"Email: {request.email}",
            f"Asunto: {request.subject}",
            "",
            "Mensaje:",
            request.message,
            "",
        ]

        if attachment:
            body_lines.append(
                f"Adjunto: {attachment.meta.filename} "
                f"({attachment.meta.size_bytes} bytes, sha256={attachment.meta.sha256})"
            )

        msg.set_content("\n".join(body_lines))

        if attachment:
            maintype, subtype = ("application", "octet-stream")
            if attachment.meta.content_type and "/" in attachment.meta.content_type:
                maintype, subtype = attachment.meta.content_type.split("/", 1)
            msg.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.meta.filename,
            )

        return msg

    async def send_contact_email(self, message: EmailMessage) -> None:
        if not settings.SMTP_HOST:
            raise RuntimeError("SMTP not configured")
        await send_email(message)
