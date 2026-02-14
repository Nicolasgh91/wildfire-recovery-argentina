"""
Test JWT token compatibility after dependency updates.

Ensures that python-jose updates don't break existing JWT tokens.
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.core.config import settings


def test_jwt_encode_decode_hs256():
    """Test JWT encoding and decoding with HS256 algorithm."""
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    
    # Encode token
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Decode token
    decoded = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=["HS256"]
    )
    
    assert decoded["sub"] == payload["sub"]
    assert decoded["email"] == payload["email"]


def test_jwt_expired_token():
    """Test that expired tokens are properly rejected."""
    payload = {
        "sub": "test-user-id",
        "exp": datetime.utcnow() - timedelta(hours=1),  # Already expired
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    with pytest.raises(JWTError):
        jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )


def test_jwt_invalid_signature():
    """Test that tokens with invalid signatures are rejected."""
    payload = {
        "sub": "test-user-id",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    # Try to decode with wrong secret
    with pytest.raises(JWTError):
        jwt.decode(
            token,
            "wrong-secret-key",
            algorithms=["HS256"]
        )


def test_jwt_algorithm_mismatch():
    """Test that algorithm mismatch is detected."""
    payload = {
        "sub": "test-user-id",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    # Try to decode with different algorithm
    with pytest.raises(JWTError):
        jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS512"]  # Different algorithm
        )


def test_jwt_with_supabase_claims():
    """Test JWT with Supabase-like claims structure."""
    payload = {
        "sub": "550e8400-e29b-41d4-a716-446655440000",
        "email": "user@example.com",
        "role": "authenticated",
        "app_metadata": {
            "provider": "google",
        },
        "user_metadata": {
            "full_name": "Test User",
        },
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm="HS256"
    )
    
    decoded = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=["HS256"]
    )
    
    assert decoded["sub"] == payload["sub"]
    assert decoded["email"] == payload["email"]
    assert decoded["role"] == "authenticated"
    assert "app_metadata" in decoded
    assert "user_metadata" in decoded
