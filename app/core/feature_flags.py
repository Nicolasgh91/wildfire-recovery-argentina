"""
Feature flag enforcement for ForestGuard API.

Provides FastAPI dependencies to block access to features disabled via environment variables.
"""
from fastapi import HTTPException
from app.core.config import settings


def require_feature(name: str):
    """
    FastAPI dependency factory for feature flag enforcement.
    
    Args:
        name: Feature name (e.g., "certificates", "refuges")
        
    Returns:
        Dependency function that raises 404 if feature is disabled
        
    Example:
        @router.get("/certificates", dependencies=[Depends(require_feature("certificates"))])
    """
    def _check():
        flag_attr = f"FEATURE_{name.upper()}"
        enabled = getattr(settings, flag_attr, False)
        if not enabled:
            raise HTTPException(
                status_code=404,
                detail="Not available in MVP"
            )
    return _check
