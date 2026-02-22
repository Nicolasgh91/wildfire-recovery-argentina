"""Supabase JWT authentication dependencies."""
import logging
import traceback
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.services.supabase_auth import AuthError, decode_supabase_token, get_or_create_supabase_user

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(deps.get_db),
) -> User:
    request_id = getattr(request.state, "request_id", None) if request else None
    path = request.url.path if request else None
    method = request.method if request else None
    auth_header = request.headers.get("authorization") if request else None
    authorization_present = bool(auth_header)
    bearer_parsed = bool(credentials and credentials.scheme.lower() == "bearer")

    logger.info(
        "Auth check | id=%s | method=%s | path=%s | authorization_present=%s | bearer_parsed=%s",
        request_id,
        method,
        path,
        authorization_present,
        bearer_parsed,
    )

    if not credentials:
        logger.warning(
            "Auth missing | id=%s | method=%s | path=%s",
            request_id,
            method,
            path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporciono token de autenticacion",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_supabase_token(token)
        return get_or_create_supabase_user(db, payload)
    except AuthError as exc:
        logger.warning(
            "Auth failed | id=%s | method=%s | path=%s | error_type=%s | error=%s | traceback=%s",
            request_id,
            method,
            path,
            type(exc).__name__,
            exc.message,
            traceback.format_exc(limit=3),
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        logger.warning(
            "Auth failed | id=%s | method=%s | path=%s | error_type=%s | error=%s | traceback=%s",
            request_id,
            method,
            path,
            type(exc).__name__,
            str(exc),
            traceback.format_exc(limit=3),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(deps.get_db),
) -> Optional[User]:
    if not credentials:
        return None
    return await get_current_user(credentials=credentials, request=request, db=db)
