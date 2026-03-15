"""
Vegetation Analysis Engine (VAE) para ForestGuard.

Servicio de análisis de vegetación que proporciona:
- Monitoreo de recuperación post-incendio (UC-06)
- Detección de cambios de uso del suelo (UC-08)
- Análisis temporal para reportes históricos (UC-12)

Usa GEE Service como capa base para obtener datos y aplica
lógica de negocio específica del dominio forestal.

Arquitectura:
    Endpoints → VAE Service → GEE Service → Storage Service
                    ↓
              Business Logic
              (Umbrales, clasificación, anomalías)

Autor: ForestGuard Dev Team
Versión: 1.0.0
Última actualización: 2025-01-29
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import ee

# Umbrales unificados (D-02)
from app.core.recovery_thresholds import classify_recovery_status

# Importar servicios base
if __package__:
    from .gee_service import (
        GEEImageNotFoundError,
        GEEService,
        GEEServiceUnavailableError,
        NDVIResult,
    )
    from .storage_service import StorageService
    from app.core.circuit_breaker import GEECircuitOpenError, gee_circuit
else:
    # Para testing standalone
    from gee_service import GEEImageNotFoundError, GEEService, NDVIResult
    from storage_service import StorageService
    gee_circuit = None  # type: ignore
    GEECircuitOpenError = Exception  # type: ignore
    GEEServiceUnavailableError = Exception  # type: ignore

logger = logging.getLogger(__name__)


class BaselineNotAvailableError(Exception):
    """Raised when pre-fire baseline NDVI cannot be determined."""
    pass


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================


class RecoveryStatus(Enum):
    """Estados de recuperación de vegetación (alineados con recovery_thresholds.py)."""

    NOT_STARTED = "not_started"  # sin datos
    PENDING = "pending"  # análisis en curso
    STALLED = "stalled"  # 0-9% del baseline
    EARLY_RECOVERY = "early_recovery"  # 10-39%
    MODERATE_RECOVERY = "moderate_recovery"  # 40-69%
    ADVANCED_RECOVERY = "advanced_recovery"  # 70-89%
    FULL_RECOVERY = "full_recovery"  # ≥ 90%
    ANOMALY_DETECTED = "anomaly_detected"  # anomalía activa


class LandUseChangeType(Enum):
    """Tipos de cambio de uso del suelo detectados."""

    NATURAL_RECOVERY = "natural_recovery"
    BARE_SOIL = "bare_soil"
    AGRICULTURE = "agriculture_detected"
    CONSTRUCTION = "construction_detected"
    ROADS = "roads_detected"
    MINING = "mining_activity"
    DEFORESTATION = "deforestation"
    UNCERTAIN = "uncertain"


class AnomalyType(Enum):
    """Tipos de anomalías detectadas."""

    NONE = "none"
    SUDDEN_DROP = "sudden_ndvi_drop"  # Caída súbita de NDVI
    NO_RECOVERY = "no_recovery"  # Sin recuperación esperada
    GEOMETRIC_PATTERN = "geometric_pattern"  # Patrones geométricos (construcción)
    RAPID_GREENING = "rapid_greening"  # Revegetación artificial (agricultura)


class Severity(Enum):
    """Severidad de cambios/anomalías."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Umbrales de NDVI para clasificación
NDVI_THRESHOLDS = {
    "bare_soil": 0.1,  # NDVI < 0.1 = suelo desnudo
    "sparse_vegetation": 0.2,  # 0.1-0.2 = vegetación escasa
    "moderate_vegetation": 0.4,  # 0.2-0.4 = vegetación moderada
    "dense_vegetation": 0.6,  # 0.4-0.6 = vegetación densa
    "very_dense": 0.8,  # > 0.6 = muy densa (bosque)
}

# Umbrales de recuperación por meses post-incendio
EXPECTED_RECOVERY = {
    3: 0.15,  # 3 meses: 15% mínimo
    6: 0.30,  # 6 meses: 30% mínimo
    12: 0.50,  # 1 año: 50% mínimo
    24: 0.70,  # 2 años: 70% mínimo
    36: 0.85,  # 3 años: 85% mínimo
}


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class RecoveryAnalysis:
    """Resultado del análisis de recuperación de vegetación."""

    fire_event_id: str
    analysis_date: date
    months_after_fire: int

    # NDVI values
    baseline_ndvi: float  # NDVI pre-incendio
    current_ndvi: float  # NDVI actual
    ndvi_change: float  # Diferencia

    # Recovery metrics
    recovery_percentage: float  # 0-100
    recovery_status: RecoveryStatus
    expected_recovery: float  # Lo esperado para este tiempo
    recovery_deviation: float  # Desviación de lo esperado

    # Anomaly detection
    anomaly_detected: bool
    anomaly_type: AnomalyType
    anomaly_confidence: float  # 0-1

    # Time series (opcional)
    ndvi_history: List[Tuple[date, float]] = field(default_factory=list)

    # Metadata
    image_date: Optional[date] = None
    cloud_cover: Optional[float] = None


@dataclass
class LandUseAnalysis:
    """Resultado del análisis de cambio de uso del suelo."""

    fire_event_id: str
    analysis_date: date
    months_after_fire: int

    # Detection
    change_detected: bool
    change_type: LandUseChangeType
    change_confidence: float  # 0-1

    # Spatial
    affected_area_hectares: float
    centroid_lat: float
    centroid_lon: float

    # Legal
    is_potential_violation: bool
    violation_severity: Severity

    # Evidence
    before_ndvi: float
    after_ndvi: float
    ndvi_change: float

    # Additional indicators
    geometric_index: float  # 0-1 (1 = muy geométrico)
    texture_change: float  # Cambio en textura

    # Recommendations
    requires_field_verification: bool
    recommended_action: str


@dataclass
class TemporalAnalysis:
    """Análisis temporal completo para UC-12."""

    fire_event_id: str
    protected_area_name: str
    fire_date: date
    analysis_period: Tuple[date, date]

    # Pre-fire baseline
    pre_fire_ndvi: float
    pre_fire_date: date

    # Post-fire series
    post_fire_series: List[RecoveryAnalysis]

    # Summary
    total_images_analyzed: int
    images_with_anomalies: int
    final_recovery_status: RecoveryStatus
    overall_recovery_percentage: float

    # Trend
    recovery_trend: str  # "improving", "stagnant", "declining"
    trend_confidence: float


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================


class VAEService:
    """
    Vegetation Analysis Engine - Motor de análisis de vegetación.

    Proporciona análisis de alto nivel sobre datos de GEE:
    - Monitoreo de recuperación (UC-06)
    - Detección de cambios ilegales (UC-08)
    - Análisis temporal (UC-12)

    Ejemplo de uso:
        vae = VAEService()

        # Analizar recuperación
        recovery = vae.analyze_recovery(
            fire_event_id="uuid-123",
            bbox={"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4},
            fire_date=date(2020, 8, 15),
            analysis_date=date(2023, 8, 15)
        )

        # Detectar cambios de uso
        changes = vae.detect_land_use_change(
            fire_event_id="uuid-123",
            bbox=bbox,
            fire_date=date(2020, 8, 15)
        )
    """

    def __init__(
        self,
        gee_service: Optional[GEEService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        """
        Inicializa el servicio VAE.

        Args:
            gee_service: Instancia de GEEService (se crea si no se proporciona)
            storage_service: Instancia de StorageService (se crea si no se proporciona)
        """
        self._gee = gee_service or GEEService()
        self._storage = storage_service or StorageService()

    # =========================================================================
    # UC-06: MONITOREO DE RECUPERACIÓN
    # =========================================================================

    def analyze_recovery(
        self,
        fire_event_id: str,
        bbox: Dict[str, float],
        fire_date: date,
        analysis_date: Optional[date] = None,
        baseline_ndvi: Optional[float] = None,
    ) -> RecoveryAnalysis:
        """
        Analiza el estado de recuperación de vegetación post-incendio.

        Args:
            fire_event_id: ID del evento de incendio
            bbox: Bounding box del área afectada
            fire_date: Fecha del incendio
            analysis_date: Fecha de análisis (default: hoy)
            baseline_ndvi: NDVI pre-incendio (si se conoce)

        Returns:
            RecoveryAnalysis con métricas completas
        """
        self._gee.authenticate()

        analysis_date = analysis_date or date.today()
        months_after = self._months_between(fire_date, analysis_date)

        logger.info(
            f"Analyzing recovery for {fire_event_id}, {months_after} months after fire"
        )

        # Obtener baseline si no se proporciona
        if baseline_ndvi is None:
            baseline_ndvi = self._get_baseline_ndvi(bbox, fire_date)

        # Obtener NDVI actual
        current_ndvi = self._get_current_ndvi(bbox, analysis_date)

        # Calcular métricas
        ndvi_change = current_ndvi - baseline_ndvi

        # Métrica: porcentaje del NDVI pre-incendio alcanzado (baseline ratio).
        # NO es "recuperación desde el nadir post-incendio".
        # Fórmula: (current_ndvi / baseline_ndvi) * 100
        # Decisión D-01: se mantiene esta fórmula. nadir_ndvi no se persiste.
        if baseline_ndvi > 0:
            recovery_pct = min(100, max(0, (current_ndvi / baseline_ndvi) * 100))
        else:
            recovery_pct = (
                100 if current_ndvi > NDVI_THRESHOLDS["moderate_vegetation"] else 0
            )

        # Detectar anomalías (antes de clasificar para que has_anomaly sea correcto)
        anomaly_type, anomaly_conf = self._detect_recovery_anomaly(
            baseline_ndvi=baseline_ndvi,
            current_ndvi=current_ndvi,
            months_after=months_after,
            recovery_pct=recovery_pct,
        )
        has_anomaly = anomaly_type != AnomalyType.NONE

        # Clasificar estado (umbrales unificados: recovery_thresholds.py)
        status_str = classify_recovery_status(recovery_pct, has_anomaly=has_anomaly)
        recovery_status = RecoveryStatus(status_str)

        # Calcular desviación de lo esperado
        expected = self._get_expected_recovery(months_after)
        deviation = recovery_pct - (expected * 100)

        return RecoveryAnalysis(
            fire_event_id=fire_event_id,
            analysis_date=analysis_date,
            months_after_fire=months_after,
            baseline_ndvi=baseline_ndvi,
            current_ndvi=current_ndvi,
            ndvi_change=ndvi_change,
            recovery_percentage=recovery_pct,
            recovery_status=recovery_status,
            expected_recovery=expected * 100,
            recovery_deviation=deviation,
            anomaly_detected=anomaly_type != AnomalyType.NONE,
            anomaly_type=anomaly_type,
            anomaly_confidence=anomaly_conf,
        )

    def get_recovery_time_series(
        self,
        fire_event_id: str,
        bbox: Dict[str, float],
        fire_date: date,
        interval_months: int = 3,
        max_months: int = 36,
    ) -> List[RecoveryAnalysis]:
        """
        Genera serie temporal de recuperación.

        Útil para generar gráficos de evolución.

        Args:
            fire_event_id: ID del evento
            bbox: Bounding box
            fire_date: Fecha del incendio
            interval_months: Intervalo entre análisis
            max_months: Máximo de meses a analizar

        Returns:
            Lista de RecoveryAnalysis ordenada cronológicamente
        """
        self._gee.authenticate()

        # Obtener baseline una sola vez
        baseline_ndvi = self._get_baseline_ndvi(bbox, fire_date)

        results = []
        current_date = fire_date

        # Primer punto: inmediatamente post-incendio (1 mes)
        analysis_dates = []
        months = 1
        while months <= max_months:
            target = self._add_months(fire_date, months)
            if target <= date.today():
                analysis_dates.append((months, target))
            months += interval_months

        for months_after, analysis_date in analysis_dates:
            try:
                analysis = self.analyze_recovery(
                    fire_event_id=fire_event_id,
                    bbox=bbox,
                    fire_date=fire_date,
                    analysis_date=analysis_date,
                    baseline_ndvi=baseline_ndvi,
                )
                results.append(analysis)
            except GEEImageNotFoundError:
                logger.warning(f"No image available for {analysis_date}")
                continue

        return results

    def get_recovery_timeline(
        self,
        fire_event_id: str,
        fire_lat: float,
        fire_lon: float,
        fire_date: date,
        max_months: int = 36,
        buffer_degrees: float = 0.01,
    ) -> Dict[str, Any]:
        """
        Get recovery timeline for a fire event.

        Wrapper method that converts lat/lon to bbox and returns
        a dictionary format compatible with the monitoring API endpoint.

        Args:
            fire_event_id: ID of the fire event
            fire_lat: Latitude of fire centroid
            fire_lon: Longitude of fire centroid
            fire_date: Date of the fire
            max_months: Maximum months to analyze (default 36)
            buffer_degrees: Buffer around centroid for bbox (default ~1km)

        Returns:
            Dictionary with recovery timeline data for API response
        """
        # Convert lat/lon to bbox
        bbox = {
            "west": fire_lon - buffer_degrees,
            "south": fire_lat - buffer_degrees,
            "east": fire_lon + buffer_degrees,
            "north": fire_lat + buffer_degrees,
        }

        # Get baseline NDVI
        baseline_ndvi = self._get_baseline_ndvi(bbox, fire_date)

        # Get time series analysis
        series = self.get_recovery_time_series(
            fire_event_id=str(fire_event_id),
            bbox=bbox,
            fire_date=fire_date,
            interval_months=1,  # Monthly for detailed timeline
            max_months=max_months,
        )

        # Convert to API response format
        monitoring_data = []
        for analysis in series:
            monitoring_data.append(
                {
                    "month": analysis.months_after_fire,
                    "date": analysis.analysis_date.isoformat(),
                    "ndvi_mean": analysis.current_ndvi,
                    "recovery_percentage": analysis.recovery_percentage,
                    "cloud_cover_pct": analysis.cloud_cover,
                }
            )

        # Determine overall status
        if series:
            latest = series[-1]
            recovery_status = self._map_recovery_status_to_string(
                latest.recovery_status
            )
            anomaly_detected = (
                latest.anomaly_type.value if latest.anomaly_detected else None
            )
        else:
            recovery_status = "unknown"
            anomaly_detected = None

        return {
            "baseline_ndvi": baseline_ndvi,
            "monitoring_data": monitoring_data,
            "recovery_status": recovery_status,
            "anomaly_detected": anomaly_detected,
        }

    def _map_recovery_status_to_string(self, status: RecoveryStatus) -> str:
        """Map RecoveryStatus enum to API string (taxonomía unificada F4)."""
        return status.value

    # =========================================================================
    # UC-08: DETECCIÓN DE CAMBIO DE USO
    # =========================================================================

    def detect_land_use_change(
        self,
        fire_event_id: str,
        bbox: Dict[str, float],
        fire_date: date,
        analysis_date: Optional[date] = None,
        area_hectares: float = 0,
    ) -> LandUseAnalysis:
        """
        Detecta cambios de uso del suelo que podrían indicar violación legal.

        Busca patrones de:
        - Construcción (patrones geométricos, bajo NDVI persistente)
        - Agricultura (NDVI alto en patrón regular)
        - Caminos (líneas con bajo NDVI)
        - Minería (cambios drásticos de textura)

        Args:
            fire_event_id: ID del evento
            bbox: Bounding box
            fire_date: Fecha del incendio
            analysis_date: Fecha de análisis
            area_hectares: Área afectada conocida

        Returns:
            LandUseAnalysis con detección y clasificación
        """
        self._gee.authenticate()

        analysis_date = analysis_date or date.today()
        months_after = self._months_between(fire_date, analysis_date)

        logger.info(f"Detecting land use change for {fire_event_id}")

        # Obtener NDVI antes y después
        baseline_ndvi = self._get_baseline_ndvi(bbox, fire_date)
        current_ndvi = self._get_current_ndvi(bbox, analysis_date)
        ndvi_change = current_ndvi - baseline_ndvi

        # Analizar patrones
        change_type, confidence = self._classify_land_use_change(
            baseline_ndvi=baseline_ndvi,
            current_ndvi=current_ndvi,
            months_after=months_after,
        )

        # Determinar si es violación potencial
        is_violation = change_type in [
            LandUseChangeType.CONSTRUCTION,
            LandUseChangeType.AGRICULTURE,
            LandUseChangeType.ROADS,
            LandUseChangeType.MINING,
            LandUseChangeType.DEFORESTATION,
        ]

        # Determinar severidad
        severity = self._determine_severity(change_type, confidence, area_hectares)

        # Calcular índice geométrico (simplificado)
        geometric_index = self._estimate_geometric_index(current_ndvi, baseline_ndvi)

        # Recomendación
        requires_verification = is_violation and confidence > 0.6
        action = self._get_recommended_action(
            change_type, severity, requires_verification
        )

        # Centroide del bbox
        centroid_lat = (bbox["north"] + bbox["south"]) / 2
        centroid_lon = (bbox["east"] + bbox["west"]) / 2

        return LandUseAnalysis(
            fire_event_id=fire_event_id,
            analysis_date=analysis_date,
            months_after_fire=months_after,
            change_detected=change_type != LandUseChangeType.NATURAL_RECOVERY,
            change_type=change_type,
            change_confidence=confidence,
            affected_area_hectares=area_hectares,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            is_potential_violation=is_violation,
            violation_severity=severity,
            before_ndvi=baseline_ndvi,
            after_ndvi=current_ndvi,
            ndvi_change=ndvi_change,
            geometric_index=geometric_index,
            texture_change=abs(ndvi_change) / max(baseline_ndvi, 0.1),
            requires_field_verification=requires_verification,
            recommended_action=action,
        )

    # =========================================================================
    # UC-12: ANÁLISIS TEMPORAL COMPLETO
    # =========================================================================

    def analyze_temporal_series(
        self,
        fire_event_id: str,
        bbox: Dict[str, float],
        fire_date: date,
        protected_area_name: str,
        years_to_analyze: int = 5,
    ) -> TemporalAnalysis:
        """
        Análisis temporal completo para reportes históricos (UC-12).

        Genera análisis anual desde el incendio hasta hoy o N años.

        Args:
            fire_event_id: ID del evento
            bbox: Bounding box
            fire_date: Fecha del incendio
            protected_area_name: Nombre del área protegida
            years_to_analyze: Años a analizar post-incendio

        Returns:
            TemporalAnalysis con serie completa
        """
        self._gee.authenticate()

        logger.info(f"Temporal analysis for {fire_event_id} in {protected_area_name}")

        # Obtener baseline
        pre_fire_ndvi = self._get_baseline_ndvi(bbox, fire_date)
        pre_fire_date = fire_date - timedelta(days=15)  # Aproximado

        # Analizar cada año
        post_fire_series = []
        end_date = min(
            date.today(),
            date(fire_date.year + years_to_analyze, fire_date.month, fire_date.day),
        )

        # Análisis anual
        for year_offset in range(1, years_to_analyze + 1):
            target_date = date(
                fire_date.year + year_offset,
                fire_date.month,
                min(fire_date.day, 28),  # Evitar problemas con Feb 29
            )

            if target_date > date.today():
                break

            try:
                analysis = self.analyze_recovery(
                    fire_event_id=fire_event_id,
                    bbox=bbox,
                    fire_date=fire_date,
                    analysis_date=target_date,
                    baseline_ndvi=pre_fire_ndvi,
                )
                post_fire_series.append(analysis)
            except GEEImageNotFoundError:
                logger.warning(f"No image for year {target_date.year}")

        # Calcular resumen
        total_images = len(post_fire_series)
        anomaly_count = sum(1 for a in post_fire_series if a.anomaly_detected)

        # Estado final y tendencia
        if post_fire_series:
            final_recovery = post_fire_series[-1].recovery_percentage
            final_status = post_fire_series[-1].recovery_status
            trend, trend_conf = self._calculate_trend(post_fire_series)
        else:
            final_recovery = 0
            final_status = RecoveryStatus.NOT_STARTED
            trend = "unknown"
            trend_conf = 0

        return TemporalAnalysis(
            fire_event_id=fire_event_id,
            protected_area_name=protected_area_name,
            fire_date=fire_date,
            analysis_period=(fire_date, end_date),
            pre_fire_ndvi=pre_fire_ndvi,
            pre_fire_date=pre_fire_date,
            post_fire_series=post_fire_series,
            total_images_analyzed=total_images,
            images_with_anomalies=anomaly_count,
            final_recovery_status=final_status,
            overall_recovery_percentage=final_recovery,
            recovery_trend=trend,
            trend_confidence=trend_conf,
        )

    # =========================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # =========================================================================

    def _get_baseline_ndvi(
        self,
        bbox: Dict[str, float],
        fire_date: date,
        lookback_days: int = 365,
        max_cloud_cover: float = 30.0,
    ) -> float:
        """
        Calcula NDVI baseline como el máximo NDVI disponible.

        Estrategia de búsqueda (3 pasos):
        1. qualityMosaic sobre 365 días pre-incendio (pico de vegetación anual)
        2. qualityMosaic sobre 730 días pre-incendio (si paso 1 falla)
        3. qualityMosaic sobre 180-540 días post-incendio como fallback
           (para eventos sin cobertura Sentinel-2 pre-incendio, típicamente pre-2016)

        El paso 3 usa la vegetación post-incendio como aproximación del potencial
        del sitio. Es menos preciso que el baseline pre-incendio pero permite
        generar series temporales para eventos históricos.

        Args:
            bbox: bounding box del evento
            fire_date: fecha del incendio
            lookback_days: días hacia atrás para buscar (default 365)
            max_cloud_cover: máximo de nubosidad aceptable

        Returns:
            float: NDVI mean del composite de máximo NDVI

        Raises:
            BaselineNotAvailableError: si los 3 pasos fallan
        """

        def _do() -> float:
            from app.utils.bbox_utils import validate_and_convert_bbox

            bbox_val = validate_and_convert_bbox(bbox)
            for window in [lookback_days, lookback_days * 2]:
                try:
                    start = fire_date - timedelta(days=window)
                    end = fire_date - timedelta(days=1)

                    collection = self._gee.get_sentinel_collection(
                        bbox=bbox_val,
                        start_date=start,
                        end_date=end,
                        max_cloud_cover=max_cloud_cover,
                    )

                    def add_ndvi(image):
                        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
                        return image.addBands(ndvi)

                    ndvi_collection = collection.map(add_ndvi)
                    max_ndvi_composite = ndvi_collection.qualityMosaic("NDVI")

                    geometry = ee.Geometry.Rectangle(
                        [
                            bbox_val["west"],
                            bbox_val["south"],
                            bbox_val["east"],
                            bbox_val["north"],
                        ]
                    )
                    stats = (
                        max_ndvi_composite.select("NDVI")
                        .reduceRegion(
                            reducer=ee.Reducer.mean(),
                            geometry=geometry,
                            scale=30,
                            maxPixels=1e9,
                        )
                        .getInfo()
                    )

                    if stats is None:
                        logger.warning(
                            "Baseline reduceRegion returned None for window=%sd, fire_date=%s",
                            window,
                            fire_date,
                        )
                        continue

                    ndvi_mean = stats.get("NDVI") or stats.get("NDVI_mean")
                    if ndvi_mean is None or ndvi_mean < 0.05:
                        logger.warning(
                            "Baseline NDVI too low (%s) for window=%sd, fire_date=%s",
                            ndvi_mean,
                            window,
                            fire_date,
                        )
                        continue

                    logger.info(
                        "Baseline NDVI computed: %.4f (window=%sd, fire_date=%s)",
                        float(ndvi_mean),
                        window,
                        fire_date,
                    )
                    return float(ndvi_mean)

                except GEEImageNotFoundError:
                    logger.warning(
                        "No images found for baseline window=%sd, fire_date=%s",
                        window,
                        fire_date,
                    )
                    continue
                except Exception as e:
                    logger.warning(
                        "Baseline NDVI failed for window=%sd, fire_date=%s: %s",
                        window,
                        fire_date,
                        e,
                    )
                    continue

            # Paso 3: fallback post-incendio (6-18 meses después)
            # Para eventos sin cobertura Sentinel-2 pre-incendio (pre-2016)
            try:
                post_start = fire_date + timedelta(days=180)  # 6 meses después
                post_end = fire_date + timedelta(days=540)  # 18 meses después

                today = date.today()
                if post_end > today:
                    post_end = today
                if post_start > today:
                    raise GEEImageNotFoundError("Post-fire window is in the future")

                collection = self._gee.get_sentinel_collection(
                    bbox=bbox_val,
                    start_date=post_start,
                    end_date=post_end,
                    max_cloud_cover=max_cloud_cover,
                )

                def add_ndvi(image):
                    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
                    return image.addBands(ndvi)

                ndvi_collection = collection.map(add_ndvi)
                max_ndvi_composite = ndvi_collection.qualityMosaic("NDVI")

                geometry = ee.Geometry.Rectangle(
                    [
                        bbox_val["west"],
                        bbox_val["south"],
                        bbox_val["east"],
                        bbox_val["north"],
                    ]
                )
                stats = (
                    max_ndvi_composite.select("NDVI")
                    .reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=geometry,
                        scale=60,
                        maxPixels=1e9,
                    )
                    .getInfo()
                )

                ndvi_mean = stats.get("NDVI") or stats.get("NDVI_mean") if stats else None
                if ndvi_mean is not None and ndvi_mean >= 0.1:
                    logger.info(
                        "Baseline NDVI from POST-FIRE fallback: %.4f "
                        "(window=180-540d post, fire_date=%s)",
                        ndvi_mean,
                        fire_date,
                    )
                    return float(ndvi_mean)

                logger.warning(
                    "Post-fire baseline NDVI too low (%.4f) for fire_date=%s",
                    ndvi_mean if ndvi_mean is not None else 0,
                    fire_date,
                )

            except (GEEImageNotFoundError, Exception) as e:
                logger.warning(
                    "Post-fire baseline fallback failed for fire_date=%s: %s",
                    fire_date,
                    str(e)[:200],
                )

            raise BaselineNotAvailableError(
                f"No hay imágenes disponibles para calcular baseline NDVI "
                f"(fire_date={fire_date}, intentados: pre-365d, pre-730d, post-180-540d)"
            )

        if gee_circuit is None:
            return _do()
        try:
            return gee_circuit.call(_do)
        except GEECircuitOpenError as e:
            raise GEEServiceUnavailableError(
                str(e), retry_after=getattr(e, "retry_after", None)
            ) from e

    def _get_current_ndvi(self, bbox: Dict[str, float], target_date: date) -> float:
        """
        Obtiene NDVI para una fecha específica usando ImageCollection median.
        GEE envuelto en circuit breaker. Fallback iterativo se ejecuta dentro del mismo call.
        """
        from app.utils.bbox_utils import validate_and_convert_bbox

        def _do() -> float:
            import time

            bbox_val = validate_and_convert_bbox(bbox)
            logger.info("🔍 [MEDIAN_OPT] Getting NDVI for %s", target_date)
            start_time = time.time()
            try:
                start = target_date - timedelta(days=15)
                end = target_date + timedelta(days=15)
                collection = self._gee.get_sentinel_collection(
                    bbox=bbox_val, start_date=start, end_date=end, max_cloud_cover=80
                )
                composite = collection.median()
                ndvi_result = self._gee.calculate_ndvi(composite, bbox_val)
                logger.info(
                    "🔍 [MEDIAN_OPT] ✅ Median NDVI completed in %.2fs: %s",
                    time.time() - start_time,
                    ndvi_result.mean,
                )
                return ndvi_result.mean
            except Exception as e:
                logger.warning(
                    "🔍 [MEDIAN_OPT] Median failed, falling back to iterative search: %s",
                    e,
                )
                return self._get_current_ndvi_fallback(bbox_val, target_date)

        if gee_circuit is None:
            return _do()
        try:
            return gee_circuit.call(_do)
        except GEECircuitOpenError as e:
            raise GEEServiceUnavailableError(
                str(e), retry_after=getattr(e, "retry_after", None)
            ) from e
    
    def _get_current_ndvi_fallback(self, bbox: Dict[str, float], target_date: date) -> float:
        """
        Método fallback original con búsqueda iterativa por nubosidad.
        """
        import time
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 [FALLBACK] Starting iterative search for {target_date}")
        start_time = time.time()
        
        # Validate bbox first
        from app.utils.bbox_utils import validate_and_convert_bbox
        bbox = validate_and_convert_bbox(bbox)
        logger.info(f"🔍 [FALLBACK] Validated bbox: {bbox}")
        
        for max_cloud in [30, 50, 70]:
            for window_days in [30, 60, 90]:
                try:
                    logger.info(f"🔍 [FALLBACK] Trying cloud={max_cloud}%, window={window_days}days")
                    start_date = target_date - timedelta(days=window_days)
                    end_date = target_date + timedelta(days=window_days)

                    collection = self._gee.get_sentinel_collection(
                        bbox=bbox, start_date=start_date, end_date=end_date,
                        max_cloud_cover=max_cloud,
                    )

                    image = self._gee.get_best_image(
                        collection, target_date=target_date,
                    )
                    ndvi_result = self._gee.calculate_ndvi(image, bbox)
                    
                    elapsed = time.time() - start_time
                    logger.info(f"🔍 [FALLBACK] ✅ Found image in {elapsed:.2f}s: {ndvi_result.mean}")
                    return ndvi_result.mean
                except GEEImageNotFoundError:
                    logger.info(f"🔍 [FALLBACK] ❌ No image for cloud={max_cloud}%, window={window_days}days")
                    continue

        elapsed = time.time() - start_time
        logger.error(f"🔍 [FALLBACK] ❌ Exhausted all options after {elapsed:.2f}s")
        raise GEEImageNotFoundError(
            f"No suitable image found for {target_date} after extended search"
        )

    def _get_current_ndvi_with_cloud(
        self, bbox: Dict[str, float], target_date: date
    ) -> Tuple[NDVIResult, float]:
        """
        Obtiene NDVI actual y porcentaje de nubes para una fecha.
        Fallback escalonado: prueba cloud 30/50/70% y ventanas 30/60/90 días
        antes de declarar falta de imagen. F5-02.
        Returns (ndvi_result, cloud_cover_pct). GEE envuelto en circuit breaker.
        """
        from app.utils.bbox_utils import validate_and_convert_bbox

        cloud_thresholds = [30, 50, 70]
        window_days_options = [30, 60, 90]

        def _do() -> Tuple[NDVIResult, float]:
            bbox_val = validate_and_convert_bbox(bbox)
            for max_cloud in cloud_thresholds:
                for window_days in window_days_options:
                    try:
                        start = target_date - timedelta(days=window_days)
                        end = target_date + timedelta(days=window_days)
                        collection = self._gee.get_sentinel_collection(
                            bbox=bbox_val,
                            start_date=start,
                            end_date=end,
                            max_cloud_cover=float(max_cloud),
                        )
                        image = self._gee.get_best_image(
                            collection,
                            target_date=target_date,
                            bbox=bbox_val,
                            max_cloud_cover=float(max_cloud),
                        )
                        ndvi_result = self._gee.calculate_ndvi(image, bbox_val)
                        cloud_cover = self._gee.get_image_cloud_cover(image)
                        logger.info(
                            "NDVI obtenido con cloud_max=%s, window=%sd: ndvi=%.3f, cloud=%.1f%%",
                            max_cloud,
                            window_days,
                            ndvi_result.mean,
                            cloud_cover,
                        )
                        return (ndvi_result, float(cloud_cover))
                    except GEEImageNotFoundError:
                        continue
            raise GEEImageNotFoundError(
                f"No se encontró imagen utilizable para bbox={bbox}, "
                f"target={target_date} después de búsqueda extendida"
            )

        if gee_circuit is None:
            return _do()
        try:
            return gee_circuit.call(_do)
        except GEECircuitOpenError as e:
            raise GEEServiceUnavailableError(
                str(e), retry_after=getattr(e, "retry_after", None)
            ) from e

    def _months_between(self, date1: date, date2: date) -> int:
        """Calcula meses entre dos fechas."""
        return (date2.year - date1.year) * 12 + (date2.month - date1.month)

    def _add_months(self, d: date, months: int) -> date:
        """Suma meses a una fecha."""
        new_month = d.month + months
        new_year = d.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        try:
            return date(new_year, new_month, d.day)
        except ValueError:
            return date(new_year, new_month, 28)

    def _get_expected_recovery(self, months_after: int) -> float:
        """Obtiene recuperación esperada para N meses."""
        # Interpolar entre puntos conocidos
        sorted_months = sorted(EXPECTED_RECOVERY.keys())

        if months_after <= sorted_months[0]:
            return EXPECTED_RECOVERY[sorted_months[0]] * (
                months_after / sorted_months[0]
            )

        if months_after >= sorted_months[-1]:
            return EXPECTED_RECOVERY[sorted_months[-1]]

        # Interpolar
        for i, m in enumerate(sorted_months[:-1]):
            if m <= months_after < sorted_months[i + 1]:
                m1, m2 = m, sorted_months[i + 1]
                v1, v2 = EXPECTED_RECOVERY[m1], EXPECTED_RECOVERY[m2]
                ratio = (months_after - m1) / (m2 - m1)
                return v1 + (v2 - v1) * ratio

        return EXPECTED_RECOVERY[sorted_months[-1]]

    def _detect_recovery_anomaly(
        self,
        baseline_ndvi: float,
        current_ndvi: float,
        months_after: int,
        recovery_pct: float,
    ) -> Tuple[AnomalyType, float]:
        """Detecta anomalías en la recuperación."""
        expected = self._get_expected_recovery(months_after)

        # Sin recuperación cuando debería haber
        if months_after > 12 and recovery_pct < 20:
            return AnomalyType.NO_RECOVERY, 0.8

        # Caída súbita (posible nuevo incendio o deforestación)
        if current_ndvi < baseline_ndvi * 0.3:
            return AnomalyType.SUDDEN_DROP, 0.9

        # Recuperación demasiado rápida (posible agricultura)
        if months_after < 6 and recovery_pct > 80:
            return AnomalyType.RAPID_GREENING, 0.7

        # Muy por debajo de lo esperado
        if recovery_pct < (expected * 100) * 0.5:
            return AnomalyType.NO_RECOVERY, 0.6

        return AnomalyType.NONE, 0.0

    def _classify_land_use_change(
        self, baseline_ndvi: float, current_ndvi: float, months_after: int
    ) -> Tuple[LandUseChangeType, float]:
        """Clasifica el tipo de cambio de uso del suelo."""

        # NDVI muy bajo persistente = posible construcción
        if current_ndvi < NDVI_THRESHOLDS["bare_soil"] and months_after > 12:
            return LandUseChangeType.CONSTRUCTION, 0.7

        # NDVI bajo sin recuperación = suelo desnudo/caminos
        if current_ndvi < NDVI_THRESHOLDS["sparse_vegetation"] and months_after > 18:
            return LandUseChangeType.BARE_SOIL, 0.6

        # Recuperación muy rápida = posible agricultura
        expected = self._get_expected_recovery(months_after)
        recovery_pct = current_ndvi / max(baseline_ndvi, 0.1)

        if months_after < 6 and recovery_pct > 1.2:  # Más verde que antes
            return LandUseChangeType.AGRICULTURE, 0.6

        # Recuperación normal
        if recovery_pct > expected * 0.7:
            return LandUseChangeType.NATURAL_RECOVERY, 0.8

        # Incierto
        return LandUseChangeType.UNCERTAIN, 0.4

    def _determine_severity(
        self, change_type: LandUseChangeType, confidence: float, area_hectares: float
    ) -> Severity:
        """Determina severidad del cambio detectado."""

        if change_type == LandUseChangeType.NATURAL_RECOVERY:
            return Severity.LOW

        # Base severity por tipo
        base_severity = {
            LandUseChangeType.CONSTRUCTION: Severity.CRITICAL,
            LandUseChangeType.MINING: Severity.CRITICAL,
            LandUseChangeType.ROADS: Severity.HIGH,
            LandUseChangeType.AGRICULTURE: Severity.HIGH,
            LandUseChangeType.DEFORESTATION: Severity.CRITICAL,
            LandUseChangeType.BARE_SOIL: Severity.MEDIUM,
            LandUseChangeType.UNCERTAIN: Severity.LOW,
        }.get(change_type, Severity.LOW)

        # Ajustar por confianza
        if confidence < 0.5:
            # Bajar un nivel
            severity_order = [
                Severity.LOW,
                Severity.MEDIUM,
                Severity.HIGH,
                Severity.CRITICAL,
            ]
            idx = severity_order.index(base_severity)
            return severity_order[max(0, idx - 1)]

        # Ajustar por área
        if area_hectares > 50:
            # Subir un nivel
            severity_order = [
                Severity.LOW,
                Severity.MEDIUM,
                Severity.HIGH,
                Severity.CRITICAL,
            ]
            idx = severity_order.index(base_severity)
            return severity_order[min(len(severity_order) - 1, idx + 1)]

        return base_severity

    def _estimate_geometric_index(
        self, current_ndvi: float, baseline_ndvi: float
    ) -> float:
        """
        Estima índice de geometricidad (0-1).

        En una implementación completa, esto analizaría texturas y bordes.
        Por ahora, usamos una heurística simple.
        """
        # Heurística: cambios muy drásticos sugieren intervención humana
        change_ratio = abs(current_ndvi - baseline_ndvi) / max(baseline_ndvi, 0.1)

        if change_ratio > 0.8 and current_ndvi < 0.15:
            return 0.7  # Probable construcción
        elif change_ratio > 0.5:
            return 0.4  # Posible intervención
        else:
            return 0.1  # Probablemente natural

    def _get_recommended_action(
        self,
        change_type: LandUseChangeType,
        severity: Severity,
        requires_verification: bool,
    ) -> str:
        """Genera recomendación de acción."""

        if change_type == LandUseChangeType.NATURAL_RECOVERY:
            return "Continuar monitoreo estándar"

        if severity == Severity.CRITICAL:
            return "URGENTE: Notificar a autoridades ambientales. Posible violación de Ley 26.815."

        if severity == Severity.HIGH:
            return "Programar verificación en terreno en los próximos 30 días."

        if requires_verification:
            return "Verificación recomendada. Revisar imágenes de mayor resolución si disponibles."

        return "Mantener bajo observación. Repetir análisis en 3 meses."

    def _calculate_trend(self, series: List[RecoveryAnalysis]) -> Tuple[str, float]:
        """Calcula tendencia de la serie temporal."""
        if len(series) < 2:
            return "unknown", 0.0

        # Usar recovery_percentage para tendencia
        values = [a.recovery_percentage for a in series]

        # Regresión lineal simple
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stagnant", 0.5

        slope = numerator / denominator

        # Clasificar tendencia
        if slope > 5:  # >5% por año
            return "improving", min(0.9, 0.5 + slope / 20)
        elif slope < -5:
            return "declining", min(0.9, 0.5 + abs(slope) / 20)
        else:
            return "stagnant", 0.6

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self) -> Dict[str, Any]:
        """Verifica estado del servicio."""
        gee_status = self._gee.health_check()

        return {
            "service": "VAE",
            "status": "healthy" if gee_status["status"] == "healthy" else "degraded",
            "gee_status": gee_status,
            "thresholds_loaded": True,
            "expected_recovery_months": list(EXPECTED_RECOVERY.keys()),
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def get_vae_service() -> VAEService:
    """Factory function para dependency injection."""
    return VAEService()


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    vae = VAEService()

    # Health check
    status = vae.health_check()
    print(f"VAE Status: {status}")

    if status["status"] == "healthy":
        # Ejemplo de análisis
        bbox = {"west": -60.5, "south": -27.0, "east": -60.3, "north": -26.8}

        # Simular análisis de recuperación
        result = vae.analyze_recovery(
            fire_event_id="test-uuid-123",
            bbox=bbox,
            fire_date=date(2020, 8, 15),
            analysis_date=date(2023, 8, 15),
        )

        print(f"\nRecovery Analysis:")
        print(f"  Status: {result.recovery_status.value}")
        print(f"  Recovery: {result.recovery_percentage:.1f}%")
        print(f"  Anomaly: {result.anomaly_type.value}")
