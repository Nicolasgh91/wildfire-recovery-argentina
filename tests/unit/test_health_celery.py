from app.api.routes import health as health_module


def test_celery_health_returns_503_when_broker_is_unreachable(client, monkeypatch):
    def _raise_connection_error(*args, **kwargs):
        raise OSError("getaddrinfo failed")

    monkeypatch.setattr(
        health_module,
        "resolve_celery_broker_url",
        lambda: "redis://invalid-host:6379/0",
    )
    monkeypatch.setattr(health_module.redis, "from_url", _raise_connection_error)

    response = client.get("/api/v1/health/celery")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "degraded"
    assert "Redis unavailable" in payload["message"]


def test_celery_health_returns_200_when_broker_is_healthy(client, monkeypatch):
    class _HealthyRedisClient:
        def ping(self):
            return True

    monkeypatch.setattr(
        health_module,
        "resolve_celery_broker_url",
        lambda: "redis://localhost:6379/0",
    )
    monkeypatch.setattr(
        health_module.redis,
        "from_url",
        lambda *args, **kwargs: _HealthyRedisClient(),
    )

    response = client.get("/api/v1/health/celery")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
