from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)

CANONICAL_EPISODE_FLOW_DEFAULTS: dict[str, float | int] = {
    "event_spatial_epsilon_meters": 2000.0,
    "event_temporal_window_hours": 48,
    "event_monitoring_window_hours": 168,
    "episode_spatial_epsilon_meters": 6000.0,
    "episode_temporal_window_hours": 96,
}


class CanonicalEpisodeFlowParametersError(RuntimeError):
    """Raised when canonical system parameters are missing in production."""


def _is_production_environment() -> bool:
    return (settings.ENVIRONMENT or "").strip().lower() == "production"


def _extract_numeric(raw_value: Any) -> float | None:
    value = raw_value
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def load_canonical_episode_flow_parameters(db: Session) -> dict[str, float | int]:
    """Load canonical FG-EP parameters with env-specific fallback policy."""
    defaults = dict(CANONICAL_EPISODE_FLOW_DEFAULTS)
    is_prod = _is_production_environment()

    try:
        table_exists = db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'system_parameters'
                )
                """
            )
        ).scalar_one()
    except Exception as exc:
        if is_prod:
            raise CanonicalEpisodeFlowParametersError(
                "Failed to verify system_parameters table in production."
            ) from exc
        logger.warning(
            "system_parameters table lookup failed; using defaults in %s: %s",
            settings.ENVIRONMENT,
            exc,
        )
        return defaults

    if not table_exists:
        if is_prod:
            raise CanonicalEpisodeFlowParametersError(
                "system_parameters table is missing in production; canonical keys are required."
            )
        logger.warning(
            "system_parameters table missing; using defaults in %s",
            settings.ENVIRONMENT,
        )
        return defaults

    rows = (
        db.execute(
            text(
                """
                SELECT param_key, param_value
                FROM system_parameters
                WHERE param_key IN :keys
                """
            ).bindparams(bindparam("keys", expanding=True)),
            {"keys": list(defaults.keys())},
        )
        .mappings()
        .all()
    )
    found = {row["param_key"]: row["param_value"] for row in rows}

    missing_keys = [key for key in defaults.keys() if key not in found]
    if missing_keys:
        message = (
            "Missing canonical system_parameters keys: " + ", ".join(sorted(missing_keys))
        )
        if is_prod:
            raise CanonicalEpisodeFlowParametersError(message)
        logger.warning("%s. Using defaults in %s.", message, settings.ENVIRONMENT)

    resolved: dict[str, float | int] = {}
    for key, default in defaults.items():
        raw_value = found.get(key, default)
        parsed = _extract_numeric(raw_value)
        if parsed is None:
            message = (
                f"Invalid numeric value for system_parameters.{key}: {raw_value!r}"
            )
            if is_prod:
                raise CanonicalEpisodeFlowParametersError(message)
            logger.warning("%s. Using default in %s.", message, settings.ENVIRONMENT)
            parsed = float(default)

        if isinstance(default, int):
            resolved[key] = int(parsed)
        else:
            resolved[key] = float(parsed)

    return resolved
