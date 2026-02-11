import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_alert(subject: str, body: str) -> None:
    """Send alert email to admin. Fire-and-forget."""
    if not settings.ALERT_EMAIL or not settings.SMTP_HOST:
        return

    msg = EmailMessage()
    msg["Subject"] = f"[ForestGuard Alert] {subject}"
    msg["From"] = settings.ALERT_EMAIL
    msg["To"] = settings.ALERT_EMAIL
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as exc:
        logger.warning("alert_send_failed error=%s", exc)
