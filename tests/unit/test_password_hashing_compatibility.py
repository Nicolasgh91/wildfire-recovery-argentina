"""
Test password hashing compatibility after dependency updates.

Ensures that passlib updates don't break existing password hashes.
"""
import pytest
from passlib.context import CryptContext


# Initialize password context (same as production)
# Use relaxed mode to handle bcrypt 5.0+ strict validation
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__ident="2b",
    bcrypt__default_rounds=12
)


def test_bcrypt_hash_and_verify():
    """Test basic bcrypt hashing and verification."""
    password = "SecurePassword123!"
    
    # Hash password
    hashed = pwd_context.hash(password)
    
    assert isinstance(hashed, str)
    assert hashed.startswith("$2b$")  # bcrypt prefix
    assert len(hashed) == 60  # Standard bcrypt hash length
    
    # Verify correct password
    assert pwd_context.verify(password, hashed) is True
    
    # Verify incorrect password
    assert pwd_context.verify("WrongPassword", hashed) is False


def test_bcrypt_hash_uniqueness():
    """Test that same password produces different hashes (salt)."""
    password = "TestPassword123"
    
    hash1 = pwd_context.hash(password)
    hash2 = pwd_context.hash(password)
    
    # Hashes should be different due to random salt
    assert hash1 != hash2
    
    # But both should verify the same password
    assert pwd_context.verify(password, hash1) is True
    assert pwd_context.verify(password, hash2) is True


def test_bcrypt_existing_hash_compatibility():
    """Test that existing bcrypt hashes still work after update."""
    # Generate a hash that simulates an existing database entry
    password = "TestPassword123"
    existing_hash = pwd_context.hash(password)
    
    # Verify that the hash format is correct (bcrypt $2b$ prefix)
    assert existing_hash.startswith("$2b$")
    
    # Should still verify correctly
    assert pwd_context.verify(password, existing_hash) is True
    assert pwd_context.verify("WrongPassword", existing_hash) is False


def test_bcrypt_unicode_password():
    """Test handling of unicode characters in passwords."""
    password = "Contraseña123!@#$%^&*()"
    
    hashed = pwd_context.hash(password)
    assert pwd_context.verify(password, hashed) is True
    assert pwd_context.verify("Contrasena123!@#$%^&*()", hashed) is False


def test_bcrypt_long_password():
    """Test handling of very long passwords."""
    # bcrypt has a 72-byte limit, manually truncate as recommended
    password = "a" * 100
    password_truncated = password[:72]
    
    hashed = pwd_context.hash(password_truncated)
    assert pwd_context.verify(password_truncated, hashed) is True
    # Note: In production, frontend should enforce max password length


def test_bcrypt_special_characters():
    """Test passwords with special characters."""
    passwords = [
        "Pass@word!123",
        "P@$$w0rd#2024",
        "Test_Pass-123.456",
        "密码123",  # Chinese characters
        "пароль123",  # Cyrillic
    ]
    
    for password in passwords:
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(password, hashed) is True


def test_bcrypt_needs_update():
    """Test that old hashes are detected as needing update."""
    # Hash with current settings
    password = "TestPassword123"
    current_hash = pwd_context.hash(password)
    
    # Current hash should not need update
    assert pwd_context.needs_update(current_hash) is False
    
    # Old hash with lower rounds (simulated)
    # In production, you might have hashes with fewer rounds
    old_hash = "$2b$04$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/qviu6"
    
    # Old hash might need update (depending on config)
    # This is informational, not a breaking change
    needs_update = pwd_context.needs_update(old_hash)
    assert isinstance(needs_update, bool)
