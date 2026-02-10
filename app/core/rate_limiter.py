"""
=============================================================================
FORESTGUARD - RATE LIMITER MODULE
=============================================================================
IP-based rate limiting with automatic blocking and email alerts.

Features:
- Tracks requests per IP per day
- Blocks IPs exceeding 10 requests/day
- Sends email alert when blocking occurs
- Resets counts daily

Usage:
    from app.core.rate_limiter import check_ip_rate_limit
    
    @router.post("/endpoint", dependencies=[Depends(check_ip_rate_limit)])
    def endpoint():
        ...
=============================================================================
"""

import logging
import smtplib
import time
from collections import defaultdict, deque
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from threading import Lock
from typing import Deque, Dict, Optional, Set

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings
from app.core.security import UserPrincipal, UserRole, get_current_user_optional

logger = logging.getLogger(__name__)

# Thread-safe storage for IP and Key tracking
_lock = Lock()
_ip_counts: Dict[str, int] = defaultdict(int)
_key_counts: Dict[str, int] = defaultdict(int)  # Track by API Key
_blocked_ips: Set[str] = set()
_contact_windows: Dict[str, Deque[float]] = defaultdict(deque)
_current_date: date = date.today()

# Limits
LIMIT_IP_DAILY = 10
LIMIT_USER_DAILY = 1000
CONTACT_LIMIT_PER_MINUTE = 10
CONTACT_WINDOW_SECONDS = 60


def _reset_if_new_day() -> None:
    """Reset counters if a new day has started."""
    global _current_date, _ip_counts, _key_counts, _blocked_ips
    today = date.today()
    if today > _current_date:
        with _lock:
            if today > _current_date:  # Double-check after acquiring lock
                _ip_counts.clear()
                _key_counts.clear()
                _blocked_ips.clear()
                _current_date = today
                logger.info(f"Rate limiter reset for new day: {today}")


def _send_block_alert(target: str, request_count: int, is_ip: bool = True) -> None:
    """Send email alert when an IP or Key is blocked."""
    if not settings.ALERT_EMAIL or not settings.SMTP_HOST:
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER or "noreply@forestguard.org"
        msg["To"] = settings.ALERT_EMAIL
        subject = f"⚠️ ForestGuard: {'IP' if is_ip else 'API Key'} Blocked - {target}"
        msg["Subject"] = subject

        limit = LIMIT_IP_DAILY if is_ip else LIMIT_USER_DAILY

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
        logger.error(f"Failed to send block alert email: {e}")


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def check_rate_limit(
    request: Request, user: Optional[UserPrincipal] = Depends(get_current_user_optional)
) -> None:
    """
    Unified rate limiter:
    - Admin: Unlimited
    - Authenticated User: High limit (1000/day) based on API Key
    - Anonymous (IP): Low limit (10/day) based on IP
    """
    _reset_if_new_day()

    # 1. Admin - Unlimited
    if user and user.role == UserRole.ADMIN:
        return

    # 2. Authenticated User - Key Based Limit
    if user and user.role == UserRole.USER:
        key_masked = f"{user.key[:8]}..."
        with _lock:
            _key_counts[user.key] += 1
            count = _key_counts[user.key]

        if count > LIMIT_USER_DAILY:
            logger.warning(f"API Key {key_masked} exceeded limit ({count})")
            _send_block_alert(key_masked, count, is_ip=False)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily API limit exceeded for this key.",
            )
        return

    # 3. Anonymous - IP Based Limit
    client_ip = get_client_ip(request)
    if client_ip in _blocked_ips:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP blocked due to excessive requests.",
        )

    with _lock:
        _ip_counts[client_ip] += 1
        count = _ip_counts[client_ip]

    if count > LIMIT_IP_DAILY:
        with _lock:
            _blocked_ips.add(client_ip)
        logger.warning(f"IP {client_ip} blocked after {count} requests")
        _send_block_alert(client_ip, count, is_ip=True)
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

    with _lock:
        ip_window = _contact_windows[client_ip]

        while ip_window and ip_window[0] < window_start:
            ip_window.popleft()

        if len(ip_window) >= CONTACT_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Max 10 requests per minute.",
            )

        ip_window.append(now)


def reset_rate_limiter_state() -> None:
    """Clear in-memory rate limiter state. Intended for tests."""
    global _current_date
    with _lock:
        _ip_counts.clear()
        _key_counts.clear()
        _blocked_ips.clear()
        _contact_windows.clear()
        _current_date = date.today()


def get_rate_limit_stats() -> dict:
    """Get current rate limiting statistics (for admin/debugging)."""
    return {
        "date": str(_current_date),
        "tracked_ips": len(_ip_counts),
        "blocked_ips": list(_blocked_ips),
        "ip_counts": dict(_ip_counts),
        "contact_windows": {ip: len(window) for ip, window in _contact_windows.items()},
    }
