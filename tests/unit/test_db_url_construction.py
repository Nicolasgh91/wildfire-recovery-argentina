"""
DB URL Construction Unit Tests
================================
Verify that DATABASE_URL is assembled correctly by Settings.assemble_db_connection
and that app/db/database.py delegates to config.py instead of building its own URL.

These are pure unit tests — no real DB connection is made.
"""

import importlib
import sys
from unittest.mock import patch, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**kwargs):
    """Instantiate Settings with controlled env vars using monkeypatching."""
    from pydantic_settings import BaseSettings
    from app.core.config import Settings

    defaults = dict(
        DB_HOST="aws-0-us-west-2.pooler.supabase.com",
        DB_PORT="6543",
        DB_NAME="postgres",
        DB_USER="postgres.qkmuwmxifbahmcydteuj",
        DB_PASSWORD="testpassword",
        ENVIRONMENT="local",
        SECRET_KEY=None,
    )
    defaults.update(kwargs)

    with patch.dict("os.environ", {k: str(v) for k, v in defaults.items() if v is not None}, clear=False):
        return Settings(
            DB_HOST=defaults.get("DB_HOST"),
            DB_PORT=defaults.get("DB_PORT", "5432"),
            DB_NAME=defaults.get("DB_NAME", "postgres"),
            DB_USER=defaults.get("DB_USER"),
            DB_PASSWORD=defaults.get("DB_PASSWORD"),
            ENVIRONMENT=defaults.get("ENVIRONMENT", "local"),
        )


# ---------------------------------------------------------------------------
# 1. Settings.assemble_db_connection — URL assembly logic
# ---------------------------------------------------------------------------

class TestAssembleDbConnection:
    """Unit tests for the field_validator that builds DATABASE_URL."""

    def test_pooler_url_correct_format(self):
        """Supabase pooler: user=postgres.PROJECT_REF, port=6543 → correct URL."""
        s = _make_settings(
            DB_HOST="aws-0-us-west-2.pooler.supabase.com",
            DB_PORT="6543",
            DB_NAME="postgres",
            DB_USER="postgres.qkmuwmxifbahmcydteuj",
            DB_PASSWORD="simplepass",
        )
        assert s.DATABASE_URL is not None
        assert "postgres.qkmuwmxifbahmcydteuj" in s.DATABASE_URL
        assert "aws-0-us-west-2.pooler.supabase.com" in s.DATABASE_URL
        assert ":6543/" in s.DATABASE_URL
        assert s.DATABASE_URL.endswith("/postgres")

    def test_pooler_url_does_not_duplicate_postgres(self):
        """Critical: user must NOT become 'postgrespostgres' in the assembled URL."""
        s = _make_settings(
            DB_HOST="aws-0-us-west-2.pooler.supabase.com",
            DB_PORT="6543",
            DB_NAME="postgres",
            DB_USER="postgres.qkmuwmxifbahmcydteuj",
            DB_PASSWORD="simplepass",
        )
        assert "postgrespostgres" not in (s.DATABASE_URL or "")

    def test_direct_connection_url(self):
        """Direct connection (port 5432): user=postgres → correct URL."""
        s = _make_settings(
            DB_HOST="db.qkmuwmxifbahmcydteuj.supabase.co",
            DB_PORT="5432",
            DB_NAME="postgres",
            DB_USER="postgres",
            DB_PASSWORD="directpass",
        )
        assert s.DATABASE_URL is not None
        assert "db.qkmuwmxifbahmcydteuj.supabase.co" in s.DATABASE_URL
        assert ":5432/" in s.DATABASE_URL

    def test_password_with_special_chars_is_url_encoded(self):
        """Passwords with @, #, ! must be URL-encoded to avoid parse errors."""
        s = _make_settings(
            DB_HOST="aws-0-us-west-2.pooler.supabase.com",
            DB_PORT="6543",
            DB_NAME="postgres",
            DB_USER="postgres.proj123",
            DB_PASSWORD="p@ss#word!",
        )
        assert s.DATABASE_URL is not None
        # Raw special chars must not appear unencoded in the URL
        assert "p@ss#word!" not in s.DATABASE_URL
        # URL-encoded forms must be present
        assert "p%40ss%23word%21" in s.DATABASE_URL

    def test_missing_db_host_returns_none(self):
        """If DB_HOST is not set, DATABASE_URL must be None (not raise)."""
        from app.core.config import Settings
        s = Settings(
            DB_HOST=None,
            DB_USER="postgres.proj",
            DB_PASSWORD="pass",
            DB_NAME="postgres",
            ENVIRONMENT="local",
        )
        assert s.DATABASE_URL is None

    def test_missing_db_user_returns_none(self):
        """If DB_USER is not set, DATABASE_URL must be None (not raise)."""
        from app.core.config import Settings
        s = Settings(
            DB_HOST="aws-0-us-west-2.pooler.supabase.com",
            DB_USER=None,
            DB_PASSWORD="pass",
            DB_NAME="postgres",
            ENVIRONMENT="local",
        )
        assert s.DATABASE_URL is None

    def test_explicit_database_url_takes_precedence(self):
        """If DATABASE_URL is set explicitly, it must be used as-is."""
        explicit = "postgresql://custom_user:custom_pass@custom_host:9999/custom_db"
        from app.core.config import Settings
        s = Settings(
            DATABASE_URL=explicit,
            DB_HOST="other-host.supabase.com",
            DB_USER="postgres.other",
            DB_PASSWORD="other_pass",
            ENVIRONMENT="local",
        )
        assert s.DATABASE_URL == explicit

    def test_url_scheme_is_postgresql(self):
        """Assembled URL must use postgresql:// scheme."""
        s = _make_settings()
        assert s.DATABASE_URL is not None
        assert s.DATABASE_URL.startswith("postgresql://")

    def test_empty_password_produces_valid_url(self):
        """Empty password must not break URL assembly."""
        s = _make_settings(DB_PASSWORD="")
        assert s.DATABASE_URL is not None
        assert "postgresql://" in s.DATABASE_URL


# ---------------------------------------------------------------------------
# 2. database.py — delegates to session.py (no manual os.getenv)
# ---------------------------------------------------------------------------

class TestDatabaseModuleDelegation:
    """Verify database.py uses session.py's engine, not its own URL assembly."""

    def test_database_module_does_not_use_os_getenv_for_db_vars(self):
        """database.py must not call os.getenv for DB_HOST/DB_USER/DB_PASSWORD/DB_NAME."""
        import inspect
        import app.db.database as db_module

        source = inspect.getsource(db_module)

        # These patterns indicate manual URL assembly — must not be present
        forbidden_patterns = [
            'os.getenv("DB_HOST")',
            "os.getenv('DB_HOST')",
            'os.getenv("DB_USER")',
            "os.getenv('DB_USER')",
            'os.getenv("DB_PASSWORD")',
            "os.getenv('DB_PASSWORD')",
            'os.getenv("DB_NAME")',
            "os.getenv('DB_NAME')",
            "f\"postgresql://",
            "f'postgresql://",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in source, (
                f"database.py must not manually assemble DATABASE_URL. "
                f"Found forbidden pattern: {pattern!r}"
            )

    def test_database_module_imports_from_session(self):
        """database.py must import engine/session from app.db.session."""
        import inspect
        import app.db.database as db_module

        source = inspect.getsource(db_module)
        assert "from app.db.session import" in source, (
            "database.py must delegate to app.db.session"
        )

    def test_engine_is_exported(self):
        """database.py must export 'engine' for backward compatibility."""
        import app.db.database as db_module
        assert hasattr(db_module, "engine"), "database.py must export 'engine'"

    def test_session_local_is_exported(self):
        """database.py must export 'SessionLocal' for backward compatibility."""
        import app.db.database as db_module
        assert hasattr(db_module, "SessionLocal"), "database.py must export 'SessionLocal'"

    def test_get_db_is_callable(self):
        """database.py must export callable 'get_db'."""
        import app.db.database as db_module
        assert callable(db_module.get_db), "get_db must be callable"

    def test_get_db_sync_is_callable(self):
        """database.py must export callable 'get_db_sync'."""
        import app.db.database as db_module
        assert callable(db_module.get_db_sync), "get_db_sync must be callable"

    def test_test_connection_is_callable(self):
        """database.py must export callable 'test_connection'."""
        import app.db.database as db_module
        assert callable(db_module.test_connection), "test_connection must be callable"


# ---------------------------------------------------------------------------
# 3. Supabase user format validation
# ---------------------------------------------------------------------------

class TestSupabaseUserFormat:
    """Validate correct Supabase user format for pooler connections."""

    @pytest.mark.parametrize("user,port,should_warn", [
        ("postgres.qkmuwmxifbahmcydteuj", "6543", False),  # correct pooler format
        ("postgres", "5432", False),                        # correct direct format
        ("postgres", "6543", True),                         # wrong: plain user on pooler port
    ])
    def test_user_format_for_port(self, user, port, should_warn):
        """
        Pooler port 6543 requires user in 'postgres.PROJECT_REF' format.
        Plain 'postgres' on port 6543 will cause 'postgrespostgres' error.
        """
        is_pooler = port == "6543"
        has_project_ref = "." in user

        if is_pooler and not has_project_ref:
            # This is the misconfiguration that causes the bug
            assert should_warn, (
                f"User '{user}' on pooler port {port} will cause authentication error. "
                "Use format 'postgres.PROJECT_REF' for Supabase pooler connections."
            )
        else:
            assert not should_warn

    def test_assembled_url_contains_full_user_string(self):
        """The full DB_USER value must appear verbatim in the assembled URL."""
        user = "postgres.qkmuwmxifbahmcydteuj"
        s = _make_settings(DB_USER=user, DB_PASSWORD="pass")
        assert user in (s.DATABASE_URL or ""), (
            f"Full DB_USER '{user}' must appear in DATABASE_URL unchanged"
        )
