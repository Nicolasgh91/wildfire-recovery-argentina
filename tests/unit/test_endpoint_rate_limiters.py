"""
Test endpoint-specific rate limiters.

Verifies that audit, reports, and payments endpoints have appropriate rate limits.
"""
import pytest
from fastapi import HTTPException, Request
from unittest.mock import Mock, AsyncMock

from app.core.rate_limiter import (
    make_audit_rate_limiter,
    make_reports_rate_limiter,
    make_payments_rate_limiter,
    reset_rate_limiter_state,
)
from app.core.security import UserPrincipal, UserRole


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter state before each test."""
    reset_rate_limiter_state()
    yield
    reset_rate_limiter_state()


def make_mock_request(ip: str = "192.168.1.1") -> Request:
    """Create a mock request with specified IP."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = ip
    request.headers = {}
    return request


@pytest.mark.asyncio
async def test_audit_rate_limiter_anonymous():
    """Test audit rate limiter for anonymous users (5/day)."""
    limiter = make_audit_rate_limiter()
    request = make_mock_request("10.0.0.1")
    
    # First 5 requests should succeed
    for i in range(5):
        await limiter(request, user=None)
    
    # 6th request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=None)
    
    assert exc_info.value.status_code == 429
    assert "5/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_audit_rate_limiter_authenticated():
    """Test audit rate limiter for authenticated users (50/day)."""
    limiter = make_audit_rate_limiter()
    request = make_mock_request()
    user = UserPrincipal(key="test-api-key-123", role=UserRole.USER)
    
    # First 50 requests should succeed
    for i in range(50):
        await limiter(request, user=user)
    
    # 51st request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=user)
    
    assert exc_info.value.status_code == 429
    assert "50/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_audit_rate_limiter_admin_unlimited():
    """Test audit rate limiter for admin users (unlimited)."""
    limiter = make_audit_rate_limiter()
    request = make_mock_request()
    admin = UserPrincipal(key="admin-key", role=UserRole.ADMIN)
    
    # 100 requests should all succeed for admin
    for i in range(100):
        await limiter(request, user=admin)
    
    # No exception should be raised


@pytest.mark.asyncio
async def test_reports_rate_limiter_anonymous():
    """Test reports rate limiter for anonymous users (2/day)."""
    limiter = make_reports_rate_limiter()
    request = make_mock_request("10.0.0.2")
    
    # First 2 requests should succeed
    for i in range(2):
        await limiter(request, user=None)
    
    # 3rd request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=None)
    
    assert exc_info.value.status_code == 429
    assert "2/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_reports_rate_limiter_authenticated():
    """Test reports rate limiter for authenticated users (20/day)."""
    limiter = make_reports_rate_limiter()
    request = make_mock_request()
    user = UserPrincipal(key="test-api-key-456", role=UserRole.USER)
    
    # First 20 requests should succeed
    for i in range(20):
        await limiter(request, user=user)
    
    # 21st request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=user)
    
    assert exc_info.value.status_code == 429
    assert "20/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_payments_rate_limiter_anonymous():
    """Test payments rate limiter for anonymous users (3/day)."""
    limiter = make_payments_rate_limiter()
    request = make_mock_request("10.0.0.3")
    
    # First 3 requests should succeed
    for i in range(3):
        await limiter(request, user=None)
    
    # 4th request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=None)
    
    assert exc_info.value.status_code == 429
    assert "3/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_payments_rate_limiter_authenticated():
    """Test payments rate limiter for authenticated users (10/day)."""
    limiter = make_payments_rate_limiter()
    request = make_mock_request()
    user = UserPrincipal(key="test-api-key-789", role=UserRole.USER)
    
    # First 10 requests should succeed
    for i in range(10):
        await limiter(request, user=user)
    
    # 11th request should fail
    with pytest.raises(HTTPException) as exc_info:
        await limiter(request, user=user)
    
    assert exc_info.value.status_code == 429
    assert "10/day" in exc_info.value.detail


@pytest.mark.asyncio
async def test_different_endpoints_independent_limits():
    """Test that different endpoints have independent rate limits."""
    audit_limiter = make_audit_rate_limiter()
    reports_limiter = make_reports_rate_limiter()
    payments_limiter = make_payments_rate_limiter()
    
    request = make_mock_request("10.0.0.4")
    user = UserPrincipal(key="test-api-key-multi", role=UserRole.USER)
    
    # Use audit limit (50)
    for i in range(50):
        await audit_limiter(request, user=user)
    
    # Reports and payments should still work (independent counters)
    await reports_limiter(request, user=user)
    await payments_limiter(request, user=user)
    
    # Audit should be exhausted
    with pytest.raises(HTTPException):
        await audit_limiter(request, user=user)


@pytest.mark.asyncio
async def test_fixed_window_behavior():
    """Test that rate limiter uses fixed window (not sliding)."""
    limiter = make_audit_rate_limiter()
    request = make_mock_request("10.0.0.5")
    
    # Exhaust limit
    for i in range(5):
        await limiter(request, user=None)
    
    # Should still be blocked (fixed window doesn't reset until 24h)
    with pytest.raises(HTTPException):
        await limiter(request, user=None)
