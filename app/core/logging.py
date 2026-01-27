import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(log_dir / "wildfire_api.log"),
        ]
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}")
    
    return logger