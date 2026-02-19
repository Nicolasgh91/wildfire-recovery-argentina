"""
Auth + Supabase JWT Integration Tests
=======================================
Full-stack integration tests running against the PostgreSQL service container
provided by auth-jwt-ci.yml. These tests verify:

  1. Database connectivity smoke (SELECT 1, users table present).
  2. HTTP auth behavior with a real SQLAlchemy session:
       - GET /health                               → 200  (no auth)
       - GET /api/v1/audit/geocode?q=chubut        → 401  (no token)
       - GET /api/v1/audit/geocode?q=chubut        → 401  (invalid JWT)
       - GET /api/v1/audit/geocode?q=chubut        → 401  (API key, wrong type)

CI smoke local values are set by auth-jwt-ci.yml; do not replace with
production values.

Prereqs (handled by CI workflow):
  - DATABASE_URL env var set to the test PostgreSQL instance.
  - database/migrations/create_users.sql applied before this test runs.
"""

import os

import pytest
from sqlalchemy import create_engine, text
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# DB Smoke Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_engine():
    """Create a raw SQLAlchemy engine pointing at the CI test database."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL / TEST_DATABASE_URL not set — skipping integration tests")
    engine = create_engine(url)
    yield engine
    engine.dispose()


# ---------------------------------------------------------------------------
# 1. Database smoke tests
# ---------------------------------------------------------------------------

class TestDatabaseSmoke:
    def test_select_1(self, db_engine):
        """Basic connectivity: SELECT 1 must return 1."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1

    def test_users_table_exists(self, db_engine):
        """Users table must be present (migration applied by CI before tests)."""
        with db_engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'users'"
                )
            ).scalar()
        assert result == 1, "users table not found — check database/migrations/create_users.sql"

    def test_users_table_has_expected_columns(self, db_engine):
        """Users table must have the required columns."""
        required_columns = {"id", "email", "password_hash", "role", "is_verified"}
        with db_engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'users'"
                )
            ).fetchall()
        present = {row[0] for row in rows}
        missing = required_columns - present
        assert not missing, f"Missing columns in users table: {missing}"


# ---------------------------------------------------------------------------
# 2. HTTP auth smoke tests (with real DB session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def http_client():
    """
    TestClient backed by a real DB session.

    The FastAPI app reads DATABASE_URL from the environment at engine-init
    time. Since the CI job sets DATABASE_URL before Python starts, the app
    uses the CI PostgreSQL instance automatically.
    """
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestHttpAuthSmoke:
    """Verify the full auth pipeline with a live DB session underneath."""

    def test_health_returns_200(self, http_client):
        """GET /health must return 200 — no auth required."""
        resp = http_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_audit_geocode_no_token_returns_401(self, http_client):
        """GET /api/v1/audit/geocode without JWT → 401 (missing credentials)."""
        resp = http_client.get("/api/v1/audit/geocode", params={"q": "chubut"})
        assert resp.status_code == 401

    def test_audit_geocode_invalid_jwt_returns_401(self, http_client):
        """GET /api/v1/audit/geocode with invalid JWT → 401 (bad signature / format)."""
        resp = http_client.get(
            "/api/v1/audit/geocode",
            params={"q": "chubut"},
            headers={"Authorization": "Bearer not.a.real.supabase.token"},
        )
        assert resp.status_code == 401

    def test_audit_geocode_api_key_only_returns_401(self, http_client):
        """GET /api/v1/audit/geocode with X-API-Key only → 401 (wrong auth scheme)."""
        resp = http_client.get(
            "/api/v1/audit/geocode",
            params={"q": "chubut"},
            headers={"X-API-Key": "ci-test-api-key-not-for-production"},
        )
        assert resp.status_code == 401

    def test_audit_geocode_expired_jwt_structure_returns_401(self, http_client):
        """JWT with valid structure but wrong alg/kid/issuer → 401."""
        # A structurally valid but unsigned JWT (alg=none, no kid)
        # jose will reject this before touching the DB
        import base64, json
        header  = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({"sub": "test", "exp": 9999999999}).encode()).rstrip(b"=")
        fake_jwt = f"{header.decode()}.{payload.decode()}.fakesig"
        resp = http_client.get(
            "/api/v1/audit/geocode",
            params={"q": "chubut"},
            headers={"Authorization": f"Bearer {fake_jwt}"},
        )
        assert resp.status_code == 401
