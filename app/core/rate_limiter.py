"""
=============================================================================
FORESTGUARD - RATE LIMITER MODULE (BL-002 / SEC-008 / SEC-009 / PERF-004)
=============================================================================
Distributed rate limiting with Redis backend and in-memory fallback.

Features:
- Redis-backed counters (INCR + EXPIRE) for multi-instance consistency
- Automatic fallback to in-memory when Redis is unavailable
- Trusted-proxy validation for X-Forwarded-For (SEC-009)
- Tracks requests per IP/key per day
- Blocks IPs exceeding daily limits
- Sends email alert when blocking occurs

Usage:
    from app.core.rate_limiter import check_ip_rate_limit

    @router.post("/endpoint", dependencies=[Depends(check_ip_rate_limit)])
    def endpoint():
        ...
=============================================================================
"""

import ipaddress
import logging
import smtplib
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Lock
from typing import Deque, Dict, List, Optional, Set

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.security import UserPrincipal, UserRole, get_current_user_optional

logger = logging.getLogger(__name__)

# Limits
LIMIT_IP_DAILY = 10
LIMIT_USER_DAILY = 1000
CONTACT_LIMIT_PER_MINUTE = 10
CONTACT_WINDOW_SECONDS = 60

# Parsed trusted proxy networks (built once at import)
_trusted_networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []


def _build_trusted_networks() -> None:
    """Parse TRUSTED_PROXIES setting into network objects."""
    global _trusted_networks
    nets = []
    for entry in settings.TRUSTED_PROXIES:
        try:
            nets.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            logger.warning("Invalid TRUSTED_PROXIES entry ignored: %s", entry)
    _trusted_networks = nets


_build_trusted_networks()


# =============================================================================
# BACKEND ABSTRACTION
# =============================================================================


class _RateLimitBackend(ABC):
    """Abstract rate-limit storage backend."""

    @abstractmethod
    def increment(self, key: str, ttl_seconds: int) -> int:
        """Increment counter and return new value. TTL applied on first create."""

    @abstractmethod
    def is_blocked(self, key: str) -> bool:
        """Return True if key is in blocked set."""

    @abstractmethod
    def block(self, key: str, ttl_seconds: int) -> None:
        """Mark key as blocked with TTL."""

    @abstractmethod
    def reset(self) -> None:
        """Clear all state (for tests)."""

    @abstractmethod
    def stats(self) -> dict:
        """Return debugging stats."""


class _InMemoryBackend(_RateLimitBackend):
    """Thread-safe in-memory backend (single-instance only)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: Dict[str, int] = defaultdict(int)
        self._blocked: Set[str] = set()
        self._current_date: date = date.today()

    def _reset_if_new_day(self) -> None:
        today = date.today()
        if today > self._current_date:
            with self._lock:
                if today > self._current_date:
                    self._counts.clear()
                    self._blocked.clear()
                    self._current_date = today
                    logger.info("Rate limiter reset for new day: %s", today)

    def increment(self, key: str, ttl_seconds: int) -> int:
        self._reset_if_new_day()
        with self._lock:
            self._counts[key] += 1
            return self._counts[key]

    def is_blocked(self, key: str) -> bool:
        self._reset_if_new_day()
        return key in self._blocked

    def block(self, key: str, ttl_seconds: int) -> None:
        with self._lock:
            self._blocked.add(key)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
            self._blocked.clear()
            self._current_date = date.today()

    def stats(self) -> dict:
        return {
            "backend": "in_memory",
            "date": str(self._current_date),
            "tracked_keys": len(self._counts),
            "blocked_keys": list(self._blocked),
            "counts": dict(self._counts),
        }


class _RedisBackend(_RateLimitBackend):
    """Redis-backed rate-limit storage for multi-instance deployments."""

    def __init__(self, redis_client) -> None:  # type: ignore[type-arg]
        self._redis = redis_client

    def increment(self, key: str, ttl_seconds: int) -> int:
        pipe = self._redis.pipeline(transaction=True)
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)  # set TTL only on first creation
        results = pipe.execute()
        return int(results[0])

    def is_blocked(self, key: str) -> bool:
        return bool(self._redis.exists(key))

    def block(self, key: str, ttl_seconds: int) -> None:
        self._redis.setex(key, ttl_seconds, "1")

    def reset(self) -> None:
        for pattern in ("rl:*", "rl_block:*"):
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=pattern, count=500)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break

    def stats(self) -> dict:
        counts = {}
        for pattern in ("rl:*",):
            cursor = 0
            while True:
                cursor, keys = self._redis.scan(cursor, match=pattern, count=500)
                for k in keys:
                    key_str = k if isinstance(k, str) else k.decode()
                    val = self._redis.get(k)
                    counts[key_str] = int(val) if val else 0
                if cursor == 0:
                    break
        return {"backend": "redis", "counts": counts}


# =============================================================================
# BACKEND INITIALIZATION
# =============================================================================

_backend: _RateLimitBackend


def _init_backend() -> _RateLimitBackend:
    """Try Redis first, fall back to in-memory."""
    try:
        import redis as _redis_lib

        client = _redis_lib.Redis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
        )
        client.ping()
        logger.info("Rate limiter using Redis backend (%s)", settings.REDIS_URL)
        return _RedisBackend(client)
    except Exception as exc:
        logger.warning(
            "Redis unavailable for rate limiter, using in-memory fallback: %s", exc
        )
        return _InMemoryBackend()


_backend = _init_backend()


# Contact sliding-window state (always in-memory; lightweight)
_contact_lock = Lock()
_contact_windows: Dict[str, Deque[float]] = defaultdict(deque)


# =============================================================================
# IP EXTRACTION (SEC-009)
# =============================================================================


def _is_trusted_proxy(ip_str: str) -> bool:
    """Check if an IP belongs to the configured trusted proxy ranges."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_networks)


def get_client_ip(request: Request) -> str:
    """Extract client IP, trusting X-Forwarded-For only from trusted proxies."""
    direct_ip = request.client.host if request.client else "unknown"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded and _is_trusted_proxy(direct_ip):
        # Rightmost untrusted IP is the real client
        parts = [p.strip() for p in forwarded.split(",")]
        # Walk from right to left, skip trusted proxies
        for ip in reversed(parts):
            if not _is_trusted_proxy(ip):
                return ip
        # All IPs in chain are trusted — use leftmost
        return parts[0]

    return direct_ip


# =============================================================================
# ALERT
# =============================================================================


def _send_block_alert(
    target: str, request_count: int, limit: int, is_ip: bool = True
) -> None:
    """Send email alert when an IP or Key is blocked."""
    if not settings.ALERT_EMAIL or not settings.SMTP_HOST:
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER or "noreply@forestguard.org"
        msg["To"] = settings.ALERT_EMAIL
        subject = f"⚠️ ForestGuard: {'IP' if is_ip else 'API Key'} Blocked - {target}"
        msg["Subject"] = subject

        body = f"""
ForestGuard Security Alert
==========================

Access blocked due to excessive API requests.

Details:
- Target: {target} ({'IP Address' if is_ip else 'API Key'})
- Request Count: {request_count}
- Threshold: {limit} requests/day
- Blocked At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Environment: {settings.ENVIRONMENT}

This will be unblocked automatically at midnight.

--
ForestGuard API Security
        """

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

    except Exception as e:
        logger.error("Failed to send block alert notification: %s", e)


# =============================================================================
# PUBLIC RATE-LIMIT DEPENDENCIES
# =============================================================================

_DAY_SECONDS = 86400


async def check_rate_limit(
    request: Request,
    user: Optional[UserPrincipal] = Depends(get_current_user_optional),
    limit_ip_daily: int = LIMIT_IP_DAILY,
) -> None:
    """
    Unified rate limiter:
    - Admin: Unlimited
    - Authenticated User: High limit (1000/day) based on API Key
    - Anonymous (IP): Low limit (10/day) based on IP
    """
    # 1. Admin - Unlimited
    if user and user.role == UserRole.ADMIN:
        return

    # 2. Authenticated User - Key Based Limit
    if user and user.role == UserRole.USER:
        key_masked = f"{user.key[:8]}..."
        rl_key = f"rl:key:{user.key}"
        count = _backend.increment(rl_key, _DAY_SECONDS)

        if count > LIMIT_USER_DAILY:
            logger.warning("API Key %s exceeded limit (%d)", key_masked, count)
            _send_block_alert(key_masked, count, LIMIT_USER_DAILY, is_ip=False)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily API limit exceeded for this key.",
            )
        return

    # 3. Anonymous - IP Based Limit
    client_ip = get_client_ip(request)
    block_key = f"rl_block:ip:{client_ip}"

    if _backend.is_blocked(block_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP blocked due to excessive requests.",
        )

    rl_key = f"rl:ip:{client_ip}"
    count = _backend.increment(rl_key, _DAY_SECONDS)

    if count > limit_ip_daily:
        _backend.block(block_key, _DAY_SECONDS)
        logger.warning("IP %s blocked after %d requests", client_ip, count)
        _send_block_alert(client_ip, count, limit_ip_daily, is_ip=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. IP blocked.",
        )


# Backward compatibility helper
async def check_ip_rate_limit(request: Request) -> str:
    """Legacy: enforces IP limit only (ignores auth). Used where strict IP limit is desired."""
    await check_rate_limit(request, user=None)
    return get_client_ip(request)


async def check_contact_rate_limit(request: Request) -> None:
    """
    Endpoint-specific limiter for UC-F01 contact form.

    Applies a sliding window of 60 seconds with max 10 requests per IP.
    """
    client_ip = get_client_ip(request)
    now = time.time()
    window_start = now - CONTACT_WINDOW_SECONDS

    with _contact_lock:
        ip_window = _contact_windows[client_ip]

        while ip_window and ip_window[0] < window_start:
            ip_window.popleft()

        if len(ip_window) >= CONTACT_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Max 10 requests per minute.",
            )

        ip_window.append(now)


# =============================================================================
# TEST / DEBUG HELPERS
# =============================================================================


def reset_rate_limiter_state() -> None:
    """Clear rate limiter state. Intended for tests."""
    _backend.reset()
    with _contact_lock:
        _contact_windows.clear()


def get_rate_limit_stats() -> dict:
    """Get current rate limiting statistics (for admin/debugging)."""
    stats = _backend.stats()
    stats["contact_windows"] = {
        ip: len(window) for ip, window in _contact_windows.items()
    }
    return stats


def make_rate_limiter(limit_ip_daily: int):
    """Return a dependency that enforces a custom anonymous IP daily limit."""

    async def _limit(
        request: Request,
        user: Optional[UserPrincipal] = Depends(get_current_user_optional),
    ) -> None:
        await check_rate_limit(request, user=user, limit_ip_daily=limit_ip_daily)

    return _limit
