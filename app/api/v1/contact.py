"""
UC-F01: Contacto y soporte.

Endpoint publico para recibir solicitudes de contacto con adjuntos opcionales.
"""
from __future__ import annotations

import base64
import logging
from typing import Optional
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import EmailStr

from app.core.rate_limiter import check_contact_rate_limit
from app.schemas.contact import ContactRequest, ContactResponse
from app.services.contact_service import ContactAttachment, ContactService
from workers.tasks.notification import send_contact_email_task

logger = logging.getLogger(__name__)

router = APIRouter()


def get_contact_service() -> ContactService:
    """Return contact service instance used by the UC-F01 endpoint."""
    return ContactService()


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enviar solicitud de contacto",
    description="UC-F01: Envia un mensaje de contacto con adjunto opcional.",
    dependencies=[Depends(check_contact_rate_limit)],
)
async def submit_contact(
    name: str = Form(...),
    email: EmailStr = Form(...),
    subject: str = Form(...),
    message: str = Form(...),
    attachment: Optional[UploadFile] = File(None),
    service: ContactService = Depends(get_contact_service),
) -> ContactResponse:
    """Accept and enqueue a public contact request with optional attachment."""
    request_id = uuid4().hex
    request = ContactRequest(
        name=name,
        email=email,
        subject=subject,
        message=message,
    )

    contact_attachment: Optional[ContactAttachment] = None
    if attachment is not None:
        contact_attachment = await service.read_attachment(attachment)

    email_domain = request.email.split("@")[-1] if "@" in request.email else None
    delivery_path = "celery_queue"

    # Prepare payload for async task
    request_data = request.model_dump()
    attachment_data = None

    if contact_attachment:
        attachment_data = {
            "meta": contact_attachment.meta.model_dump(),
            "content_b64": base64.b64encode(contact_attachment.content).decode("utf-8"),
        }

    try:
        # Enqueue task
        send_contact_email_task.delay(
            request_id=request_id,
            request_data=request_data,
            attachment_data=attachment_data,
        )
    except Exception as enqueue_exc:
        logger.warning(
            "Contact enqueue failed id=%s error=%s",
            request_id,
            enqueue_exc,
            extra={
                "event": "contact_enqueue_failed",
                "request_id": request_id,
                "email_domain": email_domain,
                "has_attachment": bool(contact_attachment),
            },
        )
        try:
            message_to_send = service.build_email_message(
                request_id=request_id,
                request=request,
                attachment=contact_attachment,
            )
            await service.send_contact_email(message_to_send)
            delivery_path = "smtp_fallback"
        except Exception as fallback_exc:
            logger.error(
                "Contact delivery failed id=%s enqueue_error=%s fallback_error=%s",
                request_id,
                enqueue_exc,
                fallback_exc,
                extra={
                    "event": "contact_delivery_failed",
                    "request_id": request_id,
                    "email_domain": email_domain,
                    "has_attachment": bool(contact_attachment),
                    "delivery_path": "smtp_fallback",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable. Please try again later.",
            ) from fallback_exc

    logger.info(
        "AUDIT: Contact request accepted id=%s has_attachment=%s delivery_path=%s",
        request_id,
        bool(contact_attachment),
        delivery_path,
        extra={
            "event": "contact_request_accepted",
            "request_id": request_id,
            "email_domain": email_domain,
            "has_attachment": bool(contact_attachment),
            "delivery_path": delivery_path,
        },
    )

    return ContactResponse(
        status="accepted",
        request_id=request_id,
        message="Solicitud recibida. Nos pondremos en contacto a la brevedad.",
        attachment=contact_attachment.meta if contact_attachment else None,
    )
