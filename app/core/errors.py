"""
=============================================================================
FORESTGUARD - ERROR HANDLING MODULE
=============================================================================
Global exception handlers for secure, user-friendly error responses.

Features:
- Catches unhandled exceptions
- Logs full stack trace server-side
- Returns sanitized error message to client
- Prevents information leakage in production

Usage:
    # In main.py
    from app.core.errors import register_exception_handlers
    register_exception_handlers(app)
=============================================================================
"""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Catch-all handler for unhandled exceptions.

        - Logs the full traceback for debugging
        - Returns a generic error message to prevent info leakage
        - In debug mode, includes more details
        """
        # Log full details server-side
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}:\n"
            f"{traceback.format_exc()}"
        )

        # Determine response based on environment
        if settings.DEBUG:
            # Development: show more details
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "path": request.url.path,
                },
            )
        else:
            # Production: minimal information
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error",
                    "message": "An unexpected error occurred. Please try again later.",
                },
            )
