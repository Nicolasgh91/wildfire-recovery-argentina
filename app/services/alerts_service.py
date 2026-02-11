from dataclasses import dataclass
from typing import Optional

from app.schemas.alerts import ClimateSnapshot


@dataclass
class AlertAssessment:
    """Computed alert status for park capacity and climate risk."""
    occupancy_pct: float
    risk_score: float
    risk_level: str
    alert_level: str
    recommended_action: str


def _clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp a numeric value to the provided range."""
    return max(min_value, min(max_value, value))


def assess_park_capacity(
    visitor_count: int,
    carrying_capacity: int,
    climate: Optional[ClimateSnapshot] = None,
) -> AlertAssessment:
    """
    Evaluate park carrying capacity alerts (UC-04).

    Combines occupancy and climate risk into a normalized score.
    """
    occupancy_pct = visitor_count / carrying_capacity if carrying_capacity else 0
    occupancy_pct = _clamp(occupancy_pct, 0, 2)

    climate_score = 0.0
    if climate:
        if climate.temperature_c is not None and climate.temperature_c >= 32:
            climate_score += 0.15
        if climate.wind_speed_kmh is not None and climate.wind_speed_kmh >= 30:
            climate_score += 0.2
        if climate.humidity_pct is not None and climate.humidity_pct <= 25:
            climate_score += 0.2
        if climate.drought_index is not None:
            climate_score += _clamp(climate.drought_index / 5, 0, 1) * 0.25

    risk_score = _clamp(occupancy_pct + climate_score, 0, 2)

    if risk_score >= 1.2:
        risk_level = "high"
    elif risk_score >= 0.8:
        risk_level = "medium"
    else:
        risk_level = "low"

    if occupancy_pct >= 0.8 and risk_level == "high":
        alert_level = "alert"
        action = (
            "Reforzar vigilancia, restringir accesos y coordinar con guardaparques."
        )
    elif occupancy_pct >= 0.7 or risk_level == "medium":
        alert_level = "watch"
        action = "Monitorear ocupación y emitir recordatorios preventivos."
    else:
        alert_level = "normal"
        action = "Operación normal con monitoreo de rutina."

    return AlertAssessment(
        occupancy_pct=round(occupancy_pct * 100, 1),
        risk_score=round(risk_score, 2),
        risk_level=risk_level,
        alert_level=alert_level,
        recommended_action=action,
    )
