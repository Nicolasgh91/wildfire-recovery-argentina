from app.core.celery_runtime import (
    resolve_celery_broker_url,
    resolve_celery_result_backend,
)
from app.core.config import settings


def test_broker_url_prefers_celery_broker_env(monkeypatch):
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", None, raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://settings-redis:6379/0", raising=False)
    environ = {
        "CELERY_BROKER_URL": "redis://env-broker:6379/5",
        "REDIS_URL": "redis://env-redis:6379/1",
    }

    assert resolve_celery_broker_url(environ) == "redis://env-broker:6379/5"


def test_broker_url_falls_back_to_redis_url(monkeypatch):
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", None, raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://settings-redis:6379/0", raising=False)
    environ = {"REDIS_URL": "redis://localhost:6380/0"}

    assert resolve_celery_broker_url(environ) == "redis://localhost:6380/0"
    assert resolve_celery_broker_url(environ) != "redis://redis:6379/0"


def test_broker_url_uses_settings_when_env_is_missing(monkeypatch):
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", None, raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://settings-redis:6379/0", raising=False)

    assert resolve_celery_broker_url({}) == "redis://settings-redis:6379/0"


def test_result_backend_prefers_explicit_env(monkeypatch):
    monkeypatch.setattr(settings, "CELERY_RESULT_BACKEND", None, raising=False)
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", None, raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://settings-redis:6379/0", raising=False)
    environ = {
        "CELERY_RESULT_BACKEND": "redis://env-result:6379/9",
        "CELERY_BROKER_URL": "redis://env-broker:6379/5",
    }

    assert resolve_celery_result_backend(environ) == "redis://env-result:6379/9"


def test_result_backend_falls_back_to_resolved_broker(monkeypatch):
    monkeypatch.setattr(settings, "CELERY_RESULT_BACKEND", None, raising=False)
    monkeypatch.setattr(settings, "CELERY_BROKER_URL", None, raising=False)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://settings-redis:6379/0", raising=False)
    environ = {"CELERY_BROKER_URL": "redis://env-broker:6379/5"}

    assert resolve_celery_result_backend(environ) == "redis://env-broker:6379/5"
