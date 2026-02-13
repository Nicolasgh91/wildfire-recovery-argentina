import pytest

from app.core.config import settings
from app.services.episode_flow_parameters import (
    CANONICAL_EPISODE_FLOW_DEFAULTS,
    CanonicalEpisodeFlowParametersError,
    load_canonical_episode_flow_parameters,
)


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _MappingsResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    def __init__(self, *, table_exists=True, rows=None, fail_table_lookup=False):
        self.table_exists = table_exists
        self.rows = rows or []
        self.fail_table_lookup = fail_table_lookup

    def execute(self, statement, params=None):
        sql = str(statement)
        if "information_schema.tables" in sql:
            if self.fail_table_lookup:
                raise RuntimeError("table lookup failed")
            return _ScalarResult(self.table_exists)
        if "SELECT param_key, param_value" in sql:
            return _MappingsResult(self.rows)
        raise AssertionError(f"Unexpected SQL in fake session: {sql}")


def test_load_params_fallbacks_to_defaults_when_table_missing_in_dev(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    db = _FakeSession(table_exists=False)

    params = load_canonical_episode_flow_parameters(db)

    assert params == CANONICAL_EPISODE_FLOW_DEFAULTS


def test_load_params_raises_when_table_missing_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    db = _FakeSession(table_exists=False)

    with pytest.raises(CanonicalEpisodeFlowParametersError):
        load_canonical_episode_flow_parameters(db)


def test_load_params_raises_when_canonical_key_is_missing_in_production(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    db = _FakeSession(
        table_exists=True,
        rows=[
            {
                "param_key": "event_spatial_epsilon_meters",
                "param_value": {"value": 2500},
            }
        ],
    )

    with pytest.raises(CanonicalEpisodeFlowParametersError):
        load_canonical_episode_flow_parameters(db)


def test_load_params_uses_defaults_for_missing_keys_in_dev(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    db = _FakeSession(
        table_exists=True,
        rows=[
            {
                "param_key": "event_spatial_epsilon_meters",
                "param_value": {"value": 2500},
            },
            {
                "param_key": "event_temporal_window_hours",
                "param_value": {"value": "36"},
            },
        ],
    )

    params = load_canonical_episode_flow_parameters(db)

    assert params["event_spatial_epsilon_meters"] == 2500.0
    assert params["event_temporal_window_hours"] == 36
    assert params["event_monitoring_window_hours"] == 168
