"""
Supabase authentication helpers for ForestGuard.
"""
import logging
import secrets
import time
import traceback
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import requests
from jose import JWTError, jwk, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fallback_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_BCRYPT_AVAILABLE: Optional[bool] = None
ALGORITHM = "ES256"
JWKS_CACHE_TTL_SECONDS = 600
_JWKS_CACHE: dict = {"fetched_at": 0.0, "keys": None}
logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Authentication error."""

    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def _normalize_secret(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    global _BCRYPT_AVAILABLE
    if _BCRYPT_AVAILABLE is False:
        return fallback_context.hash(password)

    try:
        hashed = pwd_context.hash(password)
        _BCRYPT_AVAILABLE = True
        return hashed
    except Exception as exc:
        _BCRYPT_AVAILABLE = False
        logger.warning(
            "bcrypt hash failed; falling back to pbkdf2_sha256 | error_type=%s | error=%s",
            type(exc).__name__,
            str(exc),
        )
        return fallback_context.hash(password)


def _supabase_jwks_url() -> str:
    if not settings.SUPABASE_URL:
        raise AuthError("Supabase URL no configurado", 401)
    return settings.SUPABASE_URL.rstrip("/") + "/auth/v1/.well-known/jwks.json"


def _get_expected_issuer() -> str:
    if not settings.SUPABASE_URL:
        raise AuthError("Supabase URL no configurado", 401)
    return settings.SUPABASE_URL.rstrip("/") + "/auth/v1"


def _fetch_jwks() -> list[dict]:
    jwks_url = _supabase_jwks_url()
    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    data = response.json()
    keys = data.get("keys")
    if not keys:
        raise AuthError("JWKS sin claves", 401)
    return keys


def _get_jwks() -> tuple[list[dict], bool]:
    now = time.time()
    cached_keys = _JWKS_CACHE.get("keys")
    if cached_keys and now - _JWKS_CACHE.get("fetched_at", 0) < JWKS_CACHE_TTL_SECONDS:
        return cached_keys, True

    try:
        keys = _fetch_jwks()
        _JWKS_CACHE["keys"] = keys
        _JWKS_CACHE["fetched_at"] = now
        return keys, False
    except Exception as exc:  # pragma: no cover - network failures
        if cached_keys:
            logger.warning(
                "JWKS fetch failed; using cached keys. error=%s",
                type(exc).__name__,
            )
            return cached_keys, True
        if isinstance(exc, AuthError):
            raise
        raise AuthError("No se pudo obtener JWKS", 401) from exc


def decode_supabase_token(token: str) -> dict:
    """Decode and validate a Supabase JWT access token."""
    expected_issuer = _get_expected_issuer()
    audience = settings.SUPABASE_JWT_AUDIENCE

    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning(
            "JWT header parse failed | error_type=%s | error=%s | traceback=%s",
            type(exc).__name__,
            str(exc),
            traceback.format_exc(limit=3),
        )
        raise AuthError("Token invalido", 401) from exc

    header_alg = header.get("alg")
    header_kid = header.get("kid")

    logger.info(
        "JWT validate | alg=%s | kid=%s | expected_alg=%s | expected_issuer=%s | expected_audience=%s",
        header_alg,
        header_kid,
        ALGORITHM,
        expected_issuer,
        audience,
    )

    if header_alg != ALGORITHM:
        raise AuthError("Algoritmo JWT invalido", 401)
    if not header_kid:
        raise AuthError("Token invalido", 401)

    jwks_keys, cache_hit = _get_jwks()
    key_dict = next((key for key in jwks_keys if key.get("kid") == header_kid), None)
    if not key_dict:
        raise AuthError("Token invalido", 401)

    logger.info("JWKS lookup | cache_hit=%s | kid=%s", cache_hit, header_kid)

    try:
        jwk_key = jwk.construct(key_dict, ALGORITHM)
        public_key = jwk_key.to_pem()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            issuer=expected_issuer,
            audience=audience,
            options={"verify_aud": bool(audience), "verify_iss": True},
        )
    except JWTError as exc:
        logger.warning(
            "JWT decode failed | error_type=%s | error=%s | traceback=%s",
            type(exc).__name__,
            str(exc),
            traceback.format_exc(limit=3),
        )
        if "expired" in str(exc).lower():
            raise AuthError("Token expirado", 401) from exc
        raise AuthError("Token invalido", 401) from exc

    return payload


def get_or_create_supabase_user(db: Session, payload: dict) -> User:
    """Map Supabase JWT payload to local user model."""
    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token invalido", 401)

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise AuthError("Token invalido", 401) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        return user

    email = payload.get("email")
    if not email:
        raise AuthError("Token invalido", 401)

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing

    user_metadata = payload.get("user_metadata") or {}
    app_metadata = payload.get("app_metadata") or {}

    full_name = (
        user_metadata.get("full_name")
        or user_metadata.get("name")
        or email.split("@")[0]
    )
    role = "admin" if app_metadata.get("role") == "admin" else "user"

    user = User(
        id=user_id,
        email=email,
        full_name=full_name,
        password_hash=hash_password(secrets.token_urlsafe(16)),
        role=role,
        is_verified=bool(
            payload.get("email_confirmed_at") or payload.get("email_verified")
        ),
    )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
