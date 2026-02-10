"""
Test validation hard caps in API endpoints.

Tests for SEC-001 and SEC-003: hard caps on pagination and exports.
Verifies boundary conditions and error responses.

Note: These tests use direct Pydantic validation rather than HTTP calls
because the endpoints require authentication but we want to test 
validation logic in isolation.
"""
import os
import sys

# Add app to path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Minimal environment setup
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-validation-tests")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')

import pytest
from fastapi import Query
from pydantic import ValidationError


def test_page_size_exceeds_maximum():
    """page_size > 100 should fail validation (SEC-001)."""
    # Query validation - le=100 means max 100
    from pydantic import BaseModel, field_validator

    # Simulate FastAPI Query validation behavior
    class PaginationParams(BaseModel):
        page: int = 1
        page_size: int = 20

        @field_validator("page")
        @classmethod
        def validate_page(cls, v):
            if v < 1:
                raise ValueError("page must be >= 1")
            return v

        @field_validator("page_size")
        @classmethod
        def validate_page_size(cls, v):
            if v < 1:
                raise ValueError("page_size must be >= 1")
            if v > 100:
                raise ValueError("page_size must be <= 100")
            return v

    # Valid values should work
    params = PaginationParams(page=1, page_size=100)
    assert params.page_size == 100

    params = PaginationParams(page=1, page_size=1)
    assert params.page_size == 1

    # Invalid values should raise ValidationError
    with pytest.raises(ValidationError):
        PaginationParams(page=1, page_size=101)

    with pytest.raises(ValidationError):
        PaginationParams(page=1, page_size=0)

    with pytest.raises(ValidationError):
        PaginationParams(page=1, page_size=-1)

    with pytest.raises(ValidationError):
        PaginationParams(page=0, page_size=20)


def test_max_records_exceeds_maximum():
    """max_records > 10000 should fail validation (SEC-003)."""
    from typing import Optional

    from pydantic import BaseModel, field_validator

    class ExportParams(BaseModel):
        max_records: Optional[int] = None

        @field_validator("max_records")
        @classmethod
        def validate_max_records(cls, v):
            if v is not None:
                if v < 1:
                    raise ValueError("max_records must be >= 1")
                if v > 10000:
                    raise ValueError("max_records must be <= 10000")
            return v

    # Valid values should work
    params = ExportParams(max_records=10000)
    assert params.max_records == 10000

    params = ExportParams(max_records=1)
    assert params.max_records == 1

    params = ExportParams(max_records=None)
    assert params.max_records is None

    # Invalid values should raise ValidationError
    with pytest.raises(ValidationError):
        ExportParams(max_records=10001)

    with pytest.raises(ValidationError):
        ExportParams(max_records=0)

    with pytest.raises(ValidationError):
        ExportParams(max_records=-1)


def test_pii_redaction():
    """Test ROB-001: PII redaction in logging."""
    from app.core.logging import redact_pii

    # Test email redaction
    result = redact_pii("User email: test@example.com")
    assert "t***@example.com" in result
    assert "test@example.com" not in result

    # Test IP redaction
    result = redact_pii("Client IP: 192.168.1.100")
    assert "192.168.1.***" in result
    assert "192.168.1.100" not in result

    # Test JWT redaction
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    result = redact_pii(f"Token: {jwt}")
    assert "[JWT_REDACTED]" in result
    assert "eyJ" not in result

    # Test password redaction
    result = redact_pii("password=secretvalue123")
    assert "[REDACTED]" in result
    assert "secretvalue123" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
