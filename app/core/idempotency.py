"""
=============================================================================
FORESTGUARD API - IDEMPOTENCY KEY SUPPORT
=============================================================================

This module provides idempotency key support for critical API endpoints
to prevent duplicate resource creation when clients retry requests.

How It Works:
-------------
1. Client sends request with `X-Idempotency-Key` header (UUID recommended)
2. Server checks if key exists in `idempotency_keys` table
3. If exists: Return cached response immediately (no duplicate creation)
4. If new: Process request, store response, return result

Usage Example:
--------------
    from app.core.idempotency import IdempotencyManager, get_idempotency_key

    @router.post("/issue")
    async def issue_certificate(
        request: CertificateRequest,
        db: Session = Depends(get_db),
        idempotency_key: Optional[str] = Depends(get_idempotency_key)
    ):
        manager = IdempotencyManager(db)
        endpoint = "/api/v1/certificates/issue"
        
        # Check for cached response
        cached = await manager.get_cached_response(idempotency_key, endpoint)
        if cached:
            return JSONResponse(content=cached["body"], status_code=cached["status"])
        
        # Process request normally...
        result = {"certificate_number": "CERT-2026-000001", ...}
        
        # Cache the response for future retries
        await manager.cache_response(
            idempotency_key, endpoint, request.model_dump(), 200, result
        )
        
        return result

Header Format:
--------------
    X-Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

Notes:
------
- Keys are optional; if not provided, request proceeds without idempotency
- Keys expire after 24 hours
- Same key with different request body returns 409 Conflict
- Keys are scoped per endpoint (same key can be used on different endpoints)

Author: ForestGuard Team
Date: 2026-01-29
=============================================================================
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session


# =============================================================================
# DEPENDENCY: Extract Idempotency Key from Header
# =============================================================================

async def get_idempotency_key(
    x_idempotency_key: Optional[str] = Header(
        None,
        description="Optional unique key to ensure idempotent request processing. "
                    "If the same key is sent again, the cached response is returned.",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
) -> Optional[str]:
    """
    FastAPI dependency to extract the X-Idempotency-Key header.
    
    Returns:
        Optional[str]: The idempotency key if provided, None otherwise.
    """
    return x_idempotency_key


# =============================================================================
# IDEMPOTENCY MANAGER
# =============================================================================

class IdempotencyManager:
    """
    Manages idempotency key storage and retrieval.
    
    Provides methods to:
    - Check if a cached response exists for an idempotency key
    - Cache a response for future retries
    - Validate request body matches the original request
    
    Attributes:
        db: SQLAlchemy database session
        ttl_hours: Time-to-live for idempotency keys (default: 24 hours)
    """
    
    def __init__(self, db: Session, ttl_hours: int = 24):
        """
        Initialize the IdempotencyManager.
        
        Args:
            db: SQLAlchemy database session
            ttl_hours: Hours until idempotency keys expire (default: 24)
        """
        self.db = db
        self.ttl_hours = ttl_hours
    
    def _hash_request(self, request_data: Dict[str, Any]) -> str:
        """
        Generate SHA-256 hash of request data for validation.
        
        Args:
            request_data: Dictionary of request body
            
        Returns:
            str: Hex-encoded SHA-256 hash
        """
        # Sort keys for consistent hashing
        json_str = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    async def get_cached_response(
        self,
        idempotency_key: Optional[str],
        endpoint: str,
        request_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a cached response exists for the given idempotency key.
        
        Args:
            idempotency_key: The client-provided idempotency key
            endpoint: API endpoint path
            request_data: Current request body for validation (optional)
            
        Returns:
            Dict with 'status' and 'body' if cached response exists, None otherwise
            
        Raises:
            HTTPException: 409 if same key used with different request body
        """
        if not idempotency_key:
            return None
        
        query = text("""
            SELECT 
                id,
                request_hash,
                response_status_code,
                response_body,
                expires_at
            FROM idempotency_keys
            WHERE idempotency_key = :key
              AND endpoint = :endpoint
              AND expires_at > NOW()
        """)
        
        result = self.db.execute(query, {
            "key": idempotency_key,
            "endpoint": endpoint
        }).fetchone()
        
        if not result:
            return None
        
        # Validate request body matches if provided
        if request_data:
            current_hash = self._hash_request(request_data)
            if current_hash != result.request_hash:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "Idempotency key conflict",
                        "message": "This idempotency key was used with a different request body. "
                                   "Use a new key for different requests.",
                        "code": "IDEMPOTENCY_KEY_CONFLICT"
                    }
                )
        
        return {
            "status": result.response_status_code,
            "body": result.response_body
        }
    
    async def cache_response(
        self,
        idempotency_key: Optional[str],
        endpoint: str,
        request_data: Dict[str, Any],
        status_code: int,
        response_body: Dict[str, Any]
    ) -> None:
        """
        Cache a response for the given idempotency key.
        
        Args:
            idempotency_key: The client-provided idempotency key
            endpoint: API endpoint path
            request_data: Request body dictionary
            status_code: HTTP response status code
            response_body: Response body dictionary
        """
        if not idempotency_key:
            return
        
        request_hash = self._hash_request(request_data)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)
        
        query = text("""
            INSERT INTO idempotency_keys (
                idempotency_key,
                endpoint,
                request_hash,
                response_status_code,
                response_body,
                expires_at
            ) VALUES (
                :key,
                :endpoint,
                :request_hash,
                :status_code,
                :response_body,
                :expires_at
            )
            ON CONFLICT (idempotency_key, endpoint) DO NOTHING
        """)
        
        self.db.execute(query, {
            "key": idempotency_key,
            "endpoint": endpoint,
            "request_hash": request_hash,
            "status_code": status_code,
            "response_body": json.dumps(response_body),
            "expires_at": expires_at
        })
        self.db.commit()
    
    @staticmethod
    async def cleanup_expired(db: Session) -> int:
        """
        Delete expired idempotency keys.
        
        Args:
            db: SQLAlchemy database session
            
        Returns:
            int: Number of deleted rows
        """
        query = text("""
            DELETE FROM idempotency_keys
            WHERE expires_at < NOW()
            RETURNING id
        """)
        result = db.execute(query)
        db.commit()
        return result.rowcount
