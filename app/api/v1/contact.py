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

    # Prepare payload for async task
    request_data = request.dict()
    attachment_data = None
    
    if contact_attachment:
        attachment_data = {
            "meta": contact_attachment.meta.dict(),
            "content_b64": base64.b64encode(contact_attachment.content).decode("utf-8"),
        }

    try:
        # Enqueue task
        send_contact_email_task.delay(
            request_id=request_id,
            request_data=request_data,
            attachment_data=attachment_data,
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue contact task: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again later.",
        ) from exc

    logger.info(
        "AUDIT: Contact request accepted id=%s email=%s has_attachment=%s",
        request_id,
        request.email,
        bool(contact_attachment),
        extra={
            "event": "contact_request_accepted",
            "request_id": request_id,
            "email": request.email,
            "has_attachment": bool(contact_attachment),
        },
    )

    return ContactResponse(
        status="accepted",
        request_id=request_id,
        message="Solicitud recibida. Nos pondremos en contacto a la brevedad.",
        attachment=contact_attachment.meta if contact_attachment else None,
    )
