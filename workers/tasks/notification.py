import base64
from typing import Optional, Dict, Any

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.email import _send_email_sync
from app.schemas.contact import ContactRequest, ContactAttachmentMeta
from app.services.contact_service import ContactService, ContactAttachment

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    name="workers.tasks.notification.send_contact_email",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    ignore_result=True,
)
def send_contact_email_task(
    self, 
    request_id: str, 
    request_data: Dict[str, Any], 
    attachment_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Async task to send contact form email via SMTP.
    Payloads are passed as dicts/json to be pickle-free.
    """
    logger.info(f"Processing contact email task for request_id={request_id}")

    try:
        service = ContactService()

        # Reconstruct Pydantic models from dicts
        request = ContactRequest(**request_data)
        
        contact_attachment: Optional[ContactAttachment] = None
        if attachment_data:
            try:
                meta_data = attachment_data.get("meta")
                content_b64 = attachment_data.get("content_b64")
                
                if meta_data and content_b64:
                    meta = ContactAttachmentMeta(**meta_data)
                    content = base64.b64decode(content_b64)
                    contact_attachment = ContactAttachment(meta=meta, content=content)
            except Exception as e:
                logger.error(f"Failed to reconstruction attachment: {e}")
                # We continue without attachment if it fails, or raise? 
                # Better to raise to fix the issue, or log and send without it?
                # Given this is "Contact", better to fail and retry or notify admin.
                raise e

        # Build email message
        email_message = service.build_email_message(
            request_id=request_id,
            request=request,
            attachment=contact_attachment,
        )

        # Send email synchronously
        _send_email_sync(email_message)
        
        logger.info(f"Email sent successfully for request_id={request_id}")
        return "sent"

    except Exception as exc:
        logger.error(f"Failed to send contact email: {exc}")
        # celery autoretry_for will handle the retry
        raise exc
