import base64
import time
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt

from app.core.config import settings
from app.services import supabase_auth


def _b64url_uint(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _generate_es256_token():
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()
    numbers = public_key.public_numbers()

    jwk_dict = {
        "kty": "EC",
        "crv": "P-256",
        "x": _b64url_uint(numbers.x),
        "y": _b64url_uint(numbers.y),
        "use": "sig",
        "kid": "test-kid",
        "alg": "ES256",
    }

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    payload = {
        "sub": str(uuid4()),
        "email": "test@example.com",
        "aud": "authenticated",
        "iss": "https://test.supabase.co/auth/v1",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }

    token = jwt.encode(
        payload,
        private_pem,
        algorithm="ES256",
        headers={"kid": "test-kid"},
    )

    return token, jwk_dict


def test_audit_requires_authorization(client):
    payload = {"lat": -31.4201, "lon": -64.1888, "radius_meters": 500}
    response = client.post("/api/v1/audit/land-use", json=payload)
    assert response.status_code == 401


def test_audit_accepts_valid_supabase_jwt(client, monkeypatch):
    token, jwk_dict = _generate_es256_token()

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_JWT_AUDIENCE", "authenticated")
    supabase_auth._JWKS_CACHE["keys"] = None
    supabase_auth._JWKS_CACHE["fetched_at"] = 0.0

    class MockResponse:
        def __init__(self, payload):
            self._payload = payload
            self.status_code = 200

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    def mock_get(_url, timeout=5):
        return MockResponse({"keys": [jwk_dict]})

    monkeypatch.setattr(supabase_auth.requests, "get", mock_get)

    payload = {"lat": -31.4201, "lon": -64.1888, "radius_meters": 500}
    response = client.post(
        "/api/v1/audit/land-use",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code != 401
