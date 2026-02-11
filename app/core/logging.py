import logging
import sys
from pathlib import Path

from app.core.config import settings
from app.core.sanitizer import redact_pii

try:
    import structlog
except Exception:  # pragma: no cover - fallback for test envs
    structlog = None


class PIIRedactingFormatter(logging.Formatter):
    """Custom formatter that redacts PII from log messages."""

    def format(self, record: logging.LogRecord) -> str:
        record.msg = redact_pii(str(record.msg))
        if record.args:
            record.args = tuple(
                redact_pii(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return super().format(record)


def _configure_standard_logging(log_dir: Path, log_level: int):
    formatter = PIIRedactingFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_dir / "wildfire_api.log")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured (structlog unavailable). Level: %s", settings.LOG_LEVEL
    )
    return logger


def _redact_structlog(_, __, event_dict):
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            event_dict[key] = redact_pii(value)
    return event_dict


def _configure_structlog(log_dir: Path, log_level: int):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_structlog,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _redact_structlog,
        ],
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_dir / "wildfire_api.log")
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    logger = structlog.get_logger(__name__)
    logger.info(
        "logging_configured",
        level=settings.LOG_LEVEL,
        pii_redaction=True,
    )

    return logger


def setup_logging():
    """Configure logging for the application with PII redaction."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    if structlog is None:
        return _configure_standard_logging(log_dir, log_level)

    return _configure_structlog(log_dir, log_level)
