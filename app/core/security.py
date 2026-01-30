"""
=============================================================================
FORESTGUARD - SECURITY MODULE
=============================================================================
API Key authentication for protected endpoints.

Usage:
    from app.core.security import verify_api_key
    
    @router.get("/protected", dependencies=[Depends(verify_api_key)])
    def protected_endpoint():
        ...
=============================================================================
"""

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader
import secrets
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# API Key Header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key for authenticated access"
)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency to verify API key from X-API-Key header.
    
    Returns:
        str: The validated API key
        
    Raises:
        HTTPException: 403 if key is missing or invalid
    """
    if not api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key. Include 'X-API-Key' header."
        )
    
    # Normalize settings.API_KEY to plain str if it's a SecretStr
    stored_key = settings.API_KEY
    try:
        # SecretStr provides get_secret_value()
        stored_key_val = stored_key.get_secret_value() if stored_key is not None else None
    except Exception:
        stored_key_val = stored_key

    # Use secrets.compare_digest for timing-attack safe comparison
    if not secrets.compare_digest(api_key, stored_key_val):
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    
    return api_key
