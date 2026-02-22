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

# Importar servicios base
if __package__:
    from .gee_service import GEEImageNotFoundError, GEEService, NDVIResult
    from .storage_service import StorageService
else:
    # Para testing standalone
    from gee_service import GEEImageNotFoundError, GEEService, NDVIResult
    from storage_service import StorageService

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS Y CONSTANTES
# =============================================================================


class RecoveryStatus(Enum):
    """Estados de recuperación de vegetación."""

    NOT_STARTED = "not_started"  # < 10% recuperación
    EARLY_RECOVERY = "early_recovery"  # 10-30%
    MODERATE_RECOVERY = "moderate_recovery"  # 30-60%
    ADVANCED_RECOVERY = "advanced_recovery"  # 60-90%
    FULL_RECOVERY = "full_recovery"  # > 90%
    ANOMALY_DETECTED = "anomaly_detected"  # Recuperación anormal


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

        # Recovery percentage (0-100)
        if baseline_ndvi > 0:
            recovery_pct = min(100, max(0, (current_ndvi / baseline_ndvi) * 100))
        else:
            recovery_pct = (
                100 if current_ndvi > NDVI_THRESHOLDS["moderate_vegetation"] else 0
            )

        # Clasificar estado
        recovery_status = self._classify_recovery_status(recovery_pct)

        # Calcular desviación de lo esperado
        expected = self._get_expected_recovery(months_after)
        deviation = recovery_pct - (expected * 100)

        # Detectar anomalías
        anomaly_type, anomaly_conf = self._detect_recovery_anomaly(
            baseline_ndvi=baseline_ndvi,
            current_ndvi=current_ndvi,
            months_after=months_after,
            recovery_pct=recovery_pct,
        )

        if anomaly_type != AnomalyType.NONE:
            recovery_status = RecoveryStatus.ANOMALY_DETECTED

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
        """Map RecoveryStatus enum to API-friendly string."""
        mapping = {
            RecoveryStatus.NOT_STARTED: "critical",
            RecoveryStatus.EARLY_RECOVERY: "poor",
            RecoveryStatus.MODERATE_RECOVERY: "moderate",
            RecoveryStatus.ADVANCED_RECOVERY: "good",
            RecoveryStatus.FULL_RECOVERY: "excellent",
            RecoveryStatus.ANOMALY_DETECTED: "suspicious",
        }
        return mapping.get(status, "unknown")

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

    def _get_baseline_ndvi(self, bbox: Dict[str, float], fire_date: date) -> float:
        """Obtiene NDVI pre-incendio (baseline)."""
        try:
            # Buscar imagen 15-45 días antes del incendio
            pre_start = fire_date - timedelta(days=45)
            pre_end = fire_date - timedelta(days=5)

            collection = self._gee.get_sentinel_collection(
                bbox=bbox, start_date=pre_start, end_date=pre_end, max_cloud_cover=25
            )

            image = self._gee.get_best_image(
                collection, target_date=fire_date - timedelta(days=15)
            )
            ndvi_result = self._gee.calculate_ndvi(image, bbox)

            return ndvi_result.mean

        except GEEImageNotFoundError:
            # Fallback: valor típico de vegetación moderada
            logger.warning("No pre-fire image found, using default baseline")
            return 0.45

    def _get_current_ndvi(self, bbox: Dict[str, float], target_date: date) -> float:
        """Obtiene NDVI para una fecha específica."""
        # Ventana de ±30 días
        start = target_date - timedelta(days=30)
        end = target_date + timedelta(days=30)

        collection = self._gee.get_sentinel_collection(
            bbox=bbox, start_date=start, end_date=end, max_cloud_cover=30
        )

        image = self._gee.get_best_image(collection, target_date=target_date)
        ndvi_result = self._gee.calculate_ndvi(image, bbox)

        return ndvi_result.mean

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

    def _classify_recovery_status(self, recovery_pct: float) -> RecoveryStatus:
        """Clasifica el estado de recuperación."""
        if recovery_pct < 10:
            return RecoveryStatus.NOT_STARTED
        elif recovery_pct < 30:
            return RecoveryStatus.EARLY_RECOVERY
        elif recovery_pct < 60:
            return RecoveryStatus.MODERATE_RECOVERY
        elif recovery_pct < 90:
            return RecoveryStatus.ADVANCED_RECOVERY
        else:
            return RecoveryStatus.FULL_RECOVERY

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
