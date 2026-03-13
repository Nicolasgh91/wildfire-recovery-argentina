"""
Umbrales unificados de clasificación de recuperación de vegetación.

Fuente única de verdad para VAEService, workers y API.
Basados en decisión de negocio D-02 (2026-03-12).

Métrica: baseline ratio = (current_ndvi / baseline_ndvi) * 100
Interpretación: porcentaje del NDVI pre-incendio alcanzado.
NO es "recuperación desde el nadir post-incendio".
"""

RECOVERY_THRESHOLDS = {
    "full_recovery": 90,
    "advanced_recovery": 70,
    "moderate_recovery": 40,
    "early_recovery": 10,
    "stalled": 0,
}

# Estados que no dependen de umbrales numéricos
SPECIAL_STATES = {
    "not_started",  # sin datos / sin baseline
    "pending",  # análisis en curso
    "anomaly_detected",  # anomalía activa (overrides clasificación numérica)
}

# Todos los estados válidos (para validación en API y frontend)
ALL_RECOVERY_STATES = (
    list(RECOVERY_THRESHOLDS.keys())
    + ["not_started", "pending", "anomaly_detected"]
)


def classify_recovery_status(
    recovery_pct: float | None,
    has_anomaly: bool = False,
) -> str:
    """
    Clasificación unificada de estado de recuperación.

    Args:
        recovery_pct: porcentaje del baseline alcanzado (0-100+), o None si no hay datos.
        has_anomaly: True si se detectó anomalía activa.

    Returns:
        String con el estado de recuperación.

    Examples:
        >>> classify_recovery_status(95.0)
        'full_recovery'
        >>> classify_recovery_status(42.0)
        'moderate_recovery'
        >>> classify_recovery_status(None)
        'not_started'
        >>> classify_recovery_status(50.0, has_anomaly=True)
        'anomaly_detected'
    """
    if has_anomaly:
        return "anomaly_detected"
    if recovery_pct is None:
        return "not_started"
    if recovery_pct >= RECOVERY_THRESHOLDS["full_recovery"]:
        return "full_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["advanced_recovery"]:
        return "advanced_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["moderate_recovery"]:
        return "moderate_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["early_recovery"]:
        return "early_recovery"
    return "stalled"
