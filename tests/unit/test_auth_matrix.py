"""Parametrized auth-contract tests for all critical endpoints (BL-001 / BL-012).

Each row defines:
  - method, path, expected status without auth, optional body/params
  - auth_type: 'jwt' | 'api_key' | 'public'

Unauthenticated requests to jwt/api_key endpoints MUST return 401 or 403.
Public endpoints MUST NOT return 401.
"""
import pytest

from app.main import app

import fastapi.testclient as _tc


# ── Auth matrix ──────────────────────────────────────────────────────────────
# (method, path, auth_type, body_or_params)
# auth_type: expected protection level
#   'jwt'     → must 401 without Bearer token
#   'api_key' → must 401/403 without X-API-Key
#   'public'  → must NOT 401
AUTH_MATRIX = [
    # --- Reports (JWT) ---
    ("POST", "/api/v1/reports/judicial", "jwt",
     {"json": {"fire_event_id": "00000000-0000-0000-0000-000000000000"}}),
    ("POST", "/api/v1/reports/historical", "jwt",
     {"json": {"protected_area_id": "00000000-0000-0000-0000-000000000000",
               "start_date": "2024-01-01", "end_date": "2024-12-31"}}),
    ("GET", "/api/v1/reports/fake-id/verify", "jwt",
     {"params": {"hash_to_verify": "abc123"}}),
    # --- Explorations (JWT) ---
    ("POST", "/api/v1/explorations/", "jwt",
     {"json": {"fire_event_id": "00000000-0000-0000-0000-000000000000"}}),
    ("GET", "/api/v1/explorations/", "jwt", {}),
    # --- Audit (JWT) ---
    ("POST", "/api/v1/audit/land-use", "jwt",
     {"json": {"lat": -34.6, "lon": -58.4}}),
    # --- Payments (JWT) ---
    ("GET", "/api/v1/payments/credits/balance", "jwt", {}),
    ("GET", "/api/v1/payments/credits/transactions", "jwt", {}),
    # --- Public endpoints ---
    ("GET", "/api/v1/fires", "public", {}),
    ("POST", "/api/v1/contact", "public",
     {"json": {"name": "Test", "email": "t@t.com", "message": "hi"}}),
    ("GET", "/health", "public", {}),
]


@pytest.fixture()
def anon_client():
    """Client with NO auth headers."""
    with _tc.TestClient(app) as c:
        yield c


_IDS = [f"{m} {p} [{a}]" for m, p, a, _ in AUTH_MATRIX]


@pytest.mark.parametrize("method,path,auth_type,kwargs", AUTH_MATRIX, ids=_IDS)
def test_auth_contract(anon_client, method, path, auth_type, kwargs):
    resp = anon_client.request(method, path, **kwargs)

    if auth_type in ("jwt", "api_key"):
        assert resp.status_code in (401, 403, 422), (
            f"{method} {path} should require auth ({auth_type}), "
            f"got {resp.status_code}"
        )
    elif auth_type == "public":
        assert resp.status_code != 401, (
            f"{method} {path} is public but returned 401"
        )
