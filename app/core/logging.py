import logging
import re
import sys
from pathlib import Path

from app.core.config import settings


def redact_pii(message: str) -> str:
    """Redact personally identifiable information from log messages.

    Sanitizes emails, IPs, JWT tokens, API keys, and passwords to comply
    with Argentina's Ley 25.326 (Personal Data Protection) and GDPR.

    Args:
        message: The log message to sanitize.

    Returns:
        Sanitized message with PII redacted.
    """
    if not isinstance(message, str):
        return str(message)

    # Emails: user@example.com -> u***@example.com
    message = re.sub(
        r"[\w.-]+@[\w.-]+\.\w+",
        lambda m: m.group()[0] + "***@" + m.group().split("@")[1],
        message,
    )

    # IPs (IPv4): 192.168.1.100 -> 192.168.1.***
    message = re.sub(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b", r"\1***", message)

    # JWT tokens: eyJ... -> [JWT_REDACTED]
    message = re.sub(
        r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "[JWT_REDACTED]",
        message,
    )

    # API Keys: long hex strings (32+ chars)
    message = re.sub(r"\b[a-fA-F0-9]{32,}\b", "[API_KEY_REDACTED]", message)

    # Password values in common patterns
    message = re.sub(
        r'(password|passwd|pwd|secret)["\']?\s*[:=]\s*["\']?[^"\'&\s]+',
        r"\1=[REDACTED]",
        message,
        flags=re.IGNORECASE,
    )

    return message


class PIIRedactingFormatter(logging.Formatter):
    """Custom formatter that redacts PII from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Redact the message
        record.msg = redact_pii(str(record.msg))
        # Redact any args that might contain PII
        if record.args:
            record.args = tuple(
                redact_pii(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return super().format(record)


def setup_logging():
    """Configure logging for the application with PII redaction."""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create PII-redacting formatter
    formatter = PIIRedactingFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler with PII redaction
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler with PII redaction
    file_handler = logging.FileHandler(log_dir / "wildfire_api.log")
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured - Level: {settings.LOG_LEVEL} (PII redaction enabled)"
    )

    return logger
