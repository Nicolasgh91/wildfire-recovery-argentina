"""Tests for rate limiter with Redis backend + trusted proxy IP extraction (BL-002 / SEC-009)."""
import ipaddress
from unittest.mock import MagicMock, patch

import fakeredis
import pytest

from app.core.rate_limiter import (
    _InMemoryBackend,
    _RedisBackend,
    _is_trusted_proxy,
    _trusted_networks,
    get_client_ip,
)


# =============================================================================
# Redis backend tests
# =============================================================================


@pytest.fixture()
def redis_backend():
    client = fakeredis.FakeRedis(decode_responses=True)
    return _RedisBackend(client)


class TestRedisBackend:
    def test_increment_returns_count(self, redis_backend):
        assert redis_backend.increment("rl:ip:1.2.3.4", 86400) == 1
        assert redis_backend.increment("rl:ip:1.2.3.4", 86400) == 2
        assert redis_backend.increment("rl:ip:1.2.3.4", 86400) == 3

    def test_increment_sets_ttl(self, redis_backend):
        redis_backend.increment("rl:ip:1.2.3.4", 100)
        ttl = redis_backend._redis.ttl("rl:ip:1.2.3.4")
        assert 0 < ttl <= 100

    def test_block_and_is_blocked(self, redis_backend):
        assert redis_backend.is_blocked("rl_block:ip:1.2.3.4") is False
        redis_backend.block("rl_block:ip:1.2.3.4", 86400)
        assert redis_backend.is_blocked("rl_block:ip:1.2.3.4") is True

    def test_reset_clears_keys(self, redis_backend):
        redis_backend.increment("rl:ip:1.2.3.4", 86400)
        redis_backend.block("rl_block:ip:1.2.3.4", 86400)
        redis_backend.reset()
        assert redis_backend.is_blocked("rl_block:ip:1.2.3.4") is False
        # Counter gone after reset
        assert redis_backend.increment("rl:ip:1.2.3.4", 86400) == 1


# =============================================================================
# InMemory backend tests
# =============================================================================


@pytest.fixture()
def mem_backend():
    return _InMemoryBackend()


class TestInMemoryBackend:
    def test_increment_returns_count(self, mem_backend):
        assert mem_backend.increment("rl:ip:1.2.3.4", 86400) == 1
        assert mem_backend.increment("rl:ip:1.2.3.4", 86400) == 2

    def test_block_and_is_blocked(self, mem_backend):
        assert mem_backend.is_blocked("rl_block:ip:1.2.3.4") is False
        mem_backend.block("rl_block:ip:1.2.3.4", 86400)
        assert mem_backend.is_blocked("rl_block:ip:1.2.3.4") is True

    def test_reset(self, mem_backend):
        mem_backend.increment("rl:ip:1.2.3.4", 86400)
        mem_backend.block("rl_block:ip:1.2.3.4", 86400)
        mem_backend.reset()
        assert mem_backend.is_blocked("rl_block:ip:1.2.3.4") is False
        assert mem_backend.increment("rl:ip:1.2.3.4", 86400) == 1


# =============================================================================
# Trusted proxy / get_client_ip tests (SEC-009)
# =============================================================================


class TestGetClientIp:
    def _make_request(self, client_host="203.0.113.50", forwarded_for=None):
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = client_host
        headers = {}
        if forwarded_for:
            headers["X-Forwarded-For"] = forwarded_for
        req.headers = headers
        return req

    def test_no_proxy_returns_direct_ip(self):
        req = self._make_request(client_host="203.0.113.50")
        assert get_client_ip(req) == "203.0.113.50"

    def test_untrusted_proxy_ignores_forwarded_for(self):
        """X-Forwarded-For from untrusted source is ignored."""
        req = self._make_request(
            client_host="203.0.113.50",  # not in trusted proxies
            forwarded_for="1.2.3.4",
        )
        assert get_client_ip(req) == "203.0.113.50"

    def test_trusted_proxy_uses_forwarded_for(self):
        """X-Forwarded-For from trusted proxy returns real client IP."""
        req = self._make_request(
            client_host="127.0.0.1",  # trusted
            forwarded_for="203.0.113.99",
        )
        assert get_client_ip(req) == "203.0.113.99"

    def test_trusted_proxy_chain_picks_rightmost_untrusted(self):
        """Multi-hop chain: picks rightmost non-trusted IP."""
        req = self._make_request(
            client_host="10.0.0.1",  # trusted (10.0.0.0/8)
            forwarded_for="203.0.113.1, 10.0.0.5, 10.0.0.2",
        )
        assert get_client_ip(req) == "203.0.113.1"

    def test_no_client_returns_unknown(self):
        req = MagicMock()
        req.client = None
        req.headers = {}
        assert get_client_ip(req) == "unknown"


# =============================================================================
# Fallback test
# =============================================================================


class TestFallback:
    def test_init_backend_falls_back_to_inmemory(self):
        """If Redis is unreachable, _init_backend returns InMemoryBackend."""
        with patch("app.core.rate_limiter.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://nonexistent:9999/0"
            mock_settings.TRUSTED_PROXIES = ["127.0.0.1"]
            from app.core.rate_limiter import _init_backend

            backend = _init_backend()
            assert isinstance(backend, _InMemoryBackend)
