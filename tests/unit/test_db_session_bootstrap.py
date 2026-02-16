import threading
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.db.session import ensure_database_url_configured
import app.db.session as session_module


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


class TestSessionLocalDoesNotDeadlock:
    """Verify that SessionLocal() doesn't deadlock due to nested lock acquisition."""

    def setup_method(self):
        session_module._engine = None
        session_module._session_factory = None

    def teardown_method(self):
        session_module._engine = None
        session_module._session_factory = None

    def test_session_local_completes_without_deadlock(self, monkeypatch):
        """SessionLocal() should complete within 5s (deadlock would hang forever)."""
        monkeypatch.setattr(
            session_module.settings,
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/testdb",
            raising=False,
        )

        mock_engine = MagicMock()
        result = [None]
        error = [None]

        with patch.object(session_module, "create_engine", return_value=mock_engine):
            def target():
                try:
                    result[0] = session_module.SessionLocal()
                except Exception as exc:
                    error[0] = exc

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(timeout=5.0)

            assert not thread.is_alive(), (
                "SessionLocal() deadlocked -- thread did not complete within 5s"
            )
            assert error[0] is None, f"SessionLocal() raised: {error[0]}"
            assert result[0] is not None

    def test_concurrent_session_local_no_deadlock(self, monkeypatch):
        """Multiple threads calling SessionLocal() concurrently should not deadlock."""
        monkeypatch.setattr(
            session_module.settings,
            "DATABASE_URL",
            "postgresql://user:pass@localhost:5432/testdb",
            raising=False,
        )

        mock_engine = MagicMock()
        errors = []
        barrier = threading.Barrier(4, timeout=10)

        with patch.object(session_module, "create_engine", return_value=mock_engine):
            def target():
                try:
                    barrier.wait()
                    session_module.SessionLocal()
                except Exception as exc:
                    errors.append(exc)

            threads = [threading.Thread(target=target) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            alive = [t for t in threads if t.is_alive()]
            assert len(alive) == 0, f"{len(alive)} threads deadlocked"
            assert len(errors) == 0, f"Errors during concurrent SessionLocal(): {errors}"

    def test_separate_locks_exist(self):
        """Verify the module has two distinct lock objects."""
        assert hasattr(session_module, "_engine_lock")
        assert hasattr(session_module, "_session_factory_lock")
        assert session_module._engine_lock is not session_module._session_factory_lock
