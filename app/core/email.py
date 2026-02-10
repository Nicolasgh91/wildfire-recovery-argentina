from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_email_sync(message: EmailMessage) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured")

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


async def send_email(
    message: EmailMessage, retries: int = 2, retry_delay: float = 1.0
) -> None:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            await asyncio.to_thread(_send_email_sync, message)
            return
        except Exception as exc:
            last_error = exc
            logger.warning("Email send attempt %s failed: %s", attempt + 1, exc)
            if attempt < retries:
                await asyncio.sleep(retry_delay)

    if last_error:
        raise last_error
