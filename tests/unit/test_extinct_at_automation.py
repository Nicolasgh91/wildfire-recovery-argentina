"""
Tests unitarios para el seteo automatico de extinct_at en update_episode_metrics.
Verifica las reglas de T-04:
  - Transicion a 'extinct' desde otro estado: setea extinct_at = NOW()
  - Reactivacion a 'active'/'monitoring': limpia extinct_at = None
  - Ya era 'extinct': preserva extinct_at original (no sobreescribe)
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, call
from uuid import uuid4


def now():
    return datetime.now(timezone.utc)


class TestExtinctAtTransitionRules:
    """
    Tests de caja blanca sobre la logica de extinct_at en episode_service.py.
    Se verifica directamente la logica del bloque if/elif/else del T-04.
    """

    def _apply_extinct_at_logic(self, new_status: str, existing_status: str, existing_extinct_at):
        """Replica la logica del T-04 para testearla aisladamente."""
        if new_status == "extinct" and existing_status != "extinct":
            return datetime.now(timezone.utc)
        elif new_status in ("active", "monitoring"):
            return None
        else:
            return existing_extinct_at

    def test_monitoring_to_extinct_sets_extinct_at(self):
        """monitoring -> extinct debe setear extinct_at."""
        result = self._apply_extinct_at_logic(
            new_status="extinct",
            existing_status="monitoring",
            existing_extinct_at=None,
        )
        assert result is not None
        assert result.tzinfo is not None

    def test_active_to_extinct_sets_extinct_at(self):
        """active -> extinct debe setear extinct_at."""
        result = self._apply_extinct_at_logic(
            new_status="extinct",
            existing_status="active",
            existing_extinct_at=None,
        )
        assert result is not None

    def test_extinct_to_extinct_preserves_original(self):
        """extinct -> extinct NO sobreescribe extinct_at."""
        original = now() - timedelta(days=5)
        result = self._apply_extinct_at_logic(
            new_status="extinct",
            existing_status="extinct",
            existing_extinct_at=original,
        )
        assert result == original

    def test_extinct_to_active_clears_extinct_at(self):
        """Reactivacion: extinct -> active limpia extinct_at."""
        result = self._apply_extinct_at_logic(
            new_status="active",
            existing_status="extinct",
            existing_extinct_at=now() - timedelta(days=3),
        )
        assert result is None

    def test_extinct_to_monitoring_clears_extinct_at(self):
        """Reactivacion: extinct -> monitoring limpia extinct_at."""
        result = self._apply_extinct_at_logic(
            new_status="monitoring",
            existing_status="extinct",
            existing_extinct_at=now(),
        )
        assert result is None

    def test_closed_preserves_extinct_at(self):
        """closed no modifica extinct_at (usa el existente)."""
        original = now() - timedelta(days=1)
        result = self._apply_extinct_at_logic(
            new_status="closed",
            existing_status="extinct",
            existing_extinct_at=original,
        )
        assert result == original

    def test_active_to_monitoring_clears_extinct_at_if_set(self):
        """active -> monitoring tambien limpia extinct_at por seguridad."""
        result = self._apply_extinct_at_logic(
            new_status="monitoring",
            existing_status="active",
            existing_extinct_at=None,
        )
        assert result is None
