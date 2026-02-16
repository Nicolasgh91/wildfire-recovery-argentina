import pytest

from app.core.config import settings
from app.db.session import ensure_database_url_configured


def test_ensure_database_url_configured_returns_url_when_present(monkeypatch):
    monkeypatch.setattr(
        settings,
        "DATABASE_URL",
        "postgresql://user:pass@localhost:5432/testdb",
        raising=False,
    )

    resolved = ensure_database_url_configured(context="Celery worker startup")

    assert resolved == "postgresql://user:pass@localhost:5432/testdb"


def test_ensure_database_url_configured_raises_with_actionable_message(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", None, raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        ensure_database_url_configured(context="Celery worker startup")

    message = str(exc_info.value)
    assert "DATABASE_URL is required" in message
    assert "Celery worker startup" in message
