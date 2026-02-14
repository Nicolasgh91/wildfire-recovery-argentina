"""Tests for storage backend guardrail in production (BL-003 / SEC-012)."""
import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestStorageGuardrailConfig:
    """Settings.STORAGE_BACKEND validator blocks 'local' in production."""

    def test_production_local_raises(self):
        env = {
            "ENVIRONMENT": "production",
            "STORAGE_BACKEND": "local",
            "SECRET_KEY": "test-secret-key-for-prod",
        }
        with patch.dict(os.environ, env, clear=False):
            from app.core.config import Settings

            with pytest.raises(ValidationError, match="STORAGE_BACKEND.*local.*not allowed"):
                Settings(
                    ENVIRONMENT="production",
                    STORAGE_BACKEND="local",
                    SECRET_KEY="test-secret-key-for-prod",
                )

    def test_production_gcs_ok(self):
        from app.core.config import Settings

        s = Settings(
            ENVIRONMENT="production",
            STORAGE_BACKEND="gcs",
            SECRET_KEY="test-secret-key-for-prod",
        )
        assert s.STORAGE_BACKEND == "gcs"

    def test_local_env_local_backend_ok(self):
        from app.core.config import Settings

        s = Settings(ENVIRONMENT="local", STORAGE_BACKEND="local")
        assert s.STORAGE_BACKEND == "local"


class TestStorageGuardrailService:
    """StorageService.__init__ also blocks local in production."""

    def test_service_init_production_local_raises(self):
        from app.services.storage_service import StorageError, StorageService

        # Reset singleton for test
        StorageService._instance = None

        env = {"ENVIRONMENT": "production", "STORAGE_BACKEND": "local"}
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(StorageError, match="not allowed in production"):
                StorageService()

        # Clean up singleton
        StorageService._instance = None

    def test_service_init_local_env_ok(self):
        from app.services.storage_service import StorageService

        StorageService._instance = None

        env = {"ENVIRONMENT": "local", "STORAGE_BACKEND": "local"}
        with patch.dict(os.environ, env, clear=False):
            svc = StorageService()
            assert svc._backend == "local"

        StorageService._instance = None
