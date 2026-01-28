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
from collections import defaultdict
from datetime import date, datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Set
from threading import Lock

from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Thread-safe storage for IP tracking
_lock = Lock()
_ip_counts: Dict[str, int] = defaultdict(int)
_blocked_ips: Set[str] = set()
_current_date: date = date.today()


def _reset_if_new_day() -> None:
    """Reset counters if a new day has started."""
    global _current_date, _ip_counts, _blocked_ips
    today = date.today()
    if today > _current_date:
        with _lock:
            if today > _current_date:  # Double-check after acquiring lock
                _ip_counts.clear()
                _blocked_ips.clear()
                _current_date = today
                logger.info(f"Rate limiter reset for new day: {today}")


def _send_block_alert(ip: str, request_count: int) -> None:
    """Send email alert when an IP is blocked."""
    if not settings.ALERT_EMAIL or not settings.SMTP_HOST:
        logger.warning(f"Cannot send alert: SMTP not configured. Blocked IP: {ip}")
        return
    
    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER or "noreply@forestguard.org"
        msg['To'] = settings.ALERT_EMAIL
        msg['Subject'] = f"⚠️ ForestGuard: IP Blocked - {ip}"
        
        body = f"""
ForestGuard Security Alert
==========================

An IP address has been blocked due to excessive API requests.

Details:
- IP Address: {ip}
- Request Count: {request_count}
- Threshold: 10 requests/day
- Blocked At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Environment: {settings.ENVIRONMENT}

This could indicate:
- A misconfigured client
- Automated scraping attempt
- Denial of service attempt

The IP will be unblocked automatically at midnight (server time).

--
ForestGuard API Security
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Block alert sent to {settings.ALERT_EMAIL} for IP {ip}")
        
    except Exception as e:
        logger.error(f"Failed to send block alert email: {e}")


def get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering proxies."""
    # Check for forwarded header (behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the original client
        return forwarded.split(",")[0].strip()
    
    # Direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


async def check_ip_rate_limit(request: Request) -> str:
    """
    Dependency to check and enforce IP-based rate limiting.
    
    Returns:
        str: The client IP address
        
    Raises:
        HTTPException: 429 if IP is blocked or exceeds limit
    """
    _reset_if_new_day()
    
    client_ip = get_client_ip(request)
    
    # Check if already blocked
    if client_ip in _blocked_ips:
        logger.warning(f"Blocked IP attempted access: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="IP blocked due to excessive requests. Try again tomorrow."
        )
    
    # Increment counter
    with _lock:
        _ip_counts[client_ip] += 1
        current_count = _ip_counts[client_ip]
    
    # Log the access
    logger.info(f"API access from {client_ip}: request #{current_count} today")
    
    # Check if threshold exceeded
    if current_count > 10:
        with _lock:
            _blocked_ips.add(client_ip)
        
        logger.warning(f"IP {client_ip} blocked after {current_count} requests")
        
        # Send alert (async would be better, but sync is simpler for MVP)
        _send_block_alert(client_ip, current_count)
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. IP has been temporarily blocked."
        )
    
    return client_ip


def get_rate_limit_stats() -> dict:
    """Get current rate limiting statistics (for admin/debugging)."""
    return {
        "date": str(_current_date),
        "tracked_ips": len(_ip_counts),
        "blocked_ips": list(_blocked_ips),
        "ip_counts": dict(_ip_counts)
    }
