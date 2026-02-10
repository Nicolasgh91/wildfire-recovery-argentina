"""
=============================================================================
FORESTGUARD - SECURITY MODULE
=============================================================================
API Key authentication with Role-Based Access Control (RBAC).

Roles:
- ADMIN: Full access to all endpoints
- USER : Access to standard protected endpoints

Usage:
    from app.core.security import get_current_user, require_admin
    
    @router.get("/protected", dependencies=[Depends(get_current_user)])
    def protected_endpoint(): ...

    @router.get("/admin-only", dependencies=[Depends(require_admin)])
    def admin_endpoint(): ...
=============================================================================
"""

import logging
import secrets
from enum import Enum
from typing import Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

# API Key Header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key for authenticated access (Admin or User)",
)


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserPrincipal(BaseModel):
    key: str  # The key used (masked in logs usually, but kept here for ref if needed)
    role: UserRole


def _get_secret_value(secret: Optional[settings.API_KEY.__class__]) -> Optional[str]:
    """Helper to extract string from SecretStr safely."""
    if secret is None:
        return None
    value = secret.get_secret_value()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


async def get_current_user(api_key: str = Security(api_key_header)) -> UserPrincipal:
    """
    Dependency to verify API key and return the authenticated user with role.

    Checks against:
    1. ADMIN_API_KEY -> Role.ADMIN
    2. API_KEY       -> Role.USER

    Raises:
        HTTPException: 403 if key is missing or invalid
    """
    if not api_key:
        logger.warning("API request without API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key. Include 'X-API-Key' header.",
        )

    # 1. Check Admin Key
    admin_key = _get_secret_value(settings.ADMIN_API_KEY)
    if admin_key and secrets.compare_digest(api_key, admin_key):
        return UserPrincipal(key=api_key, role=UserRole.ADMIN)

    # 2. Check Standard User Key
    user_key = _get_secret_value(settings.API_KEY)
    if user_key and secrets.compare_digest(api_key, user_key):
        return UserPrincipal(key=api_key, role=UserRole.USER)

    logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")


async def get_current_user_optional(
    api_key: str = Security(api_key_header),
) -> Optional[UserPrincipal]:
    """
    Dependency to get authenticated user if present, otherwise None.
    Does NOT raise 403 if key is missing (but does if key is invalid).
    """
    if not api_key:
        return None

    # Reuse the logic but catch the exception if strictly needed, or just duplicate generic check
    # 1. Check Admin Key
    admin_key = _get_secret_value(settings.ADMIN_API_KEY)
    if admin_key and secrets.compare_digest(api_key, admin_key):
        return UserPrincipal(key=api_key, role=UserRole.ADMIN)

    # 2. Check Standard User Key
    user_key = _get_secret_value(settings.API_KEY)
    if user_key and secrets.compare_digest(api_key, user_key):
        return UserPrincipal(key=api_key, role=UserRole.USER)

    # If key is provided but invalid, we technically SHOULD deny access or treat as anonymous?
    # Security-wise: Invalid credential should probably fail.
    # But for "Optional", maybe we just return None?
    # Let's fail on invalid key to prevent brute forcing from anonymous
    logger.warning(f"Invalid API key attempt in optional auth: {api_key[:8]}...")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API Key")


async def require_admin(
    user: UserPrincipal = Depends(get_current_user),
) -> UserPrincipal:
    """
    Dependency that ensures the user has ADMIN role.
    """
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


# Backwards compatibility alias (returns string key)
async def verify_api_key(user: UserPrincipal = Depends(get_current_user)) -> str:
    """Legacy dependency that returns just the API key string."""
    return user.key
