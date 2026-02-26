"""
=============================================================================
FORESTGUARD API - MONITORING ENDPOINTS (UC-06 / UC-F12)
=============================================================================

Vegetation recovery monitoring endpoints for tracking post-fire vegetation
regeneration over 36 months.

Use Cases:
    - UC-06: Reforestación - Track vegetation recovery with NDVI
    - UC-F12: Recuperación y cambio de uso (VAE)
    - Monitor recovery progress for authorities and researchers
    - Identify areas with suspicious lack of recovery

Endpoints:
    - GET  /monitoring/recovery/{fire_event_id}    - Get recovery timeline
    - GET  /monitoring/recovery/by-episode/{episode_id} - Aggregated recovery by episode (Fase 6)
    - GET  /monitoring/recovery/summary            - Get summary for multiple fires
    - GET  /monitoring/land-use-changes/{fire_event_id} - Get land use changes
    - POST /monitoring/recovery/trigger            - Manual trigger (admin only)

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-23
=============================================================================
"""

import logging
import time
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

from app.api.auth_deps import get_current_user
from app.core.rate_limiter import (
    make_generation_rate_limiter,
    make_recovery_trigger_rate_limiter,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter()

# Rate limiters for trigger endpoint: 5/6h per user + 10/h per IP (GEE quota, spec §3.4)
_trigger_rate_limit = make_generation_rate_limiter()
_trigger_ip_limit = make_recovery_trigger_rate_limiter()

# =============================================================================
# SCHEMAS
# =============================================================================


class MonthlyNDVI(BaseModel):
    """Monthly NDVI measurement."""

    month: int = Field(
        ..., ge=0, le=36, description="Month number after fire (0-36)"
    )
    date: str = Field(..., description="ISO date of measurement")
    ndvi_mean: float = Field(..., ge=-1, le=1, description="Mean NDVI value")
    recovery_percentage: Optional[float] = Field(
        None, description="Recovery % relative to baseline"
    )
    cloud_cover_pct: Optional[float] = Field(
        None, description="Cloud cover percentage"
    )


class RecoveryResponse(BaseModel):
    """Response for recovery monitoring endpoint."""

    fire_event_id: str
    fire_date: str
    fire_location: dict

    baseline_ndvi: Optional[float] = Field(
        None, description="Pre-fire NDVI baseline"
    )
    current_ndvi: Optional[float] = Field(
        None, description="Latest NDVI measurement"
    )

    months_monitored: int = Field(
        ..., description="Number of months with data"
    )
    recovery_status: str = Field(
        ..., description="Overall recovery classification"
    )
    recovery_percentage: Optional[float] = Field(
        None, description="Current recovery %"
    )
    anomaly_detected: Optional[str] = Field(
        None, description="Anomaly type if any"
    )

    monitoring_data: List[MonthlyNDVI]
    query_duration_ms: int
    message: Optional[str] = Field(
        None,
        description="Mensaje opcional, p. ej. cuando recovery_status es pending",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "fire_event_id": "550e8400-e29b-41d4-a716-446655440000",
                "fire_date": "2024-08-15",
                "fire_location": {"lat": -27.465, "lon": -58.834},
                "baseline_ndvi": 0.62,
                "current_ndvi": 0.45,
                "months_monitored": 12,
                "recovery_status": "moderate",
                "recovery_percentage": 72.5,
                "anomaly_detected": None,
                "monitoring_data": [],
                "query_duration_ms": 150,
            }
        }
    )


class RecoverySummaryItem(BaseModel):
    """Summary item for multiple fires."""

    fire_event_id: str
    fire_date: str
    province: Optional[str] = None
    recovery_status: str
    recovery_percentage: Optional[float] = None
    is_suspicious: bool


class RecoverySummaryResponse(BaseModel):
    """Response for recovery summary endpoint."""

    total_fires: int
    fires_analyzed: int
    status_breakdown: dict
    suspicious_count: int
    fires: List[RecoverySummaryItem]


class LandUseChangeItem(BaseModel):
    """Single land use change record."""

    id: str
    change_detected_at: str
    months_after_fire: Optional[int] = None
    change_type: str
    change_severity: Optional[str] = None
    affected_area_hectares: Optional[float] = None
    is_potential_violation: bool
    violation_confidence: Optional[str] = None
    status: str
    notes: Optional[str] = None


class LandUseChangesResponse(BaseModel):
    """Response for land use changes endpoint."""

    fire_event_id: str
    total_changes: int
    violation_count: int
    changes: List[LandUseChangeItem]


class TriggerResponse(BaseModel):
    """Response for manual trigger endpoint."""

    fire_event_id: str
    status: str
    message: str


# =============================================================================
# HELPER: classify recovery status from percentage
# =============================================================================


def _enqueue_recovery_if_not_pending(fire_event_id: str) -> None:
    """
    Encola análisis GEE si no hay datos. La tarea es idempotente (UPSERT),
    por lo que múltiples encoles no generan duplicados en BD.
    """
    try:
        from workers.tasks.recovery import analyze_recovery

        analyze_recovery.apply_async(
            args=[fire_event_id],
            queue="gee",
            countdown=5,
        )
    except Exception as exc:
        logger.warning(
            "enqueue_recovery_failed",
            extra={
                "error_type": type(exc).__name__,
                "error_msg": str(exc)[:500],
                "fire_event_id": fire_event_id,
            },
        )


def _classify_status(recovery_pct: Optional[float], has_activity: bool) -> str:
    """
    Clasifica el estado de recuperación según datos del último registro.
    Retorna valores alineados con RecoveryStatusBadge del frontend.
    """
    if has_activity:
        return "anomaly_detected"
    if recovery_pct is None:
        return "pending"
    if recovery_pct >= 90:
        return "full_recovery"
    if recovery_pct >= 70:
        return "advanced_recovery"
    if recovery_pct >= 40:
        return "moderate_recovery"
    if recovery_pct >= 10:
        return "early_recovery"
    if recovery_pct >= 0:
        return "stalled"
    return "not_started"


# =============================================================================
# ENDPOINTS
# =============================================================================

# NOTE: Static routes must be defined BEFORE parameterized routes
# Otherwise /recovery/summary would match /recovery/{fire_event_id}


@router.get(
    "/recovery/summary",
    response_model=RecoverySummaryResponse,
    summary="Get recovery summary for multiple fires",
    description="""
    Get a summary of vegetation recovery status for multiple fire events.

    Useful for:
    - Dashboard overviews
    - Identifying areas needing attention
    - Generating reports for authorities
    """,
)
async def get_recovery_summary(
    province: Optional[str] = Query(None, description="Filter by province"),
    min_months: int = Query(
        default=6, ge=1, description="Minimum months since fire"
    ),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(
        default=50, ge=1, le=200, description="Maximum results"
    ),
    db: Session = Depends(get_db),
) -> RecoverySummaryResponse:
    """
    Get recovery summary for multiple fire events.

    Reads from vegetation_monitoring table (populated by workers).
    """
    query = text(
        """
        SELECT
            fe.id as fire_event_id,
            fe.start_date,
            fe.province,
            vm.months_after_fire,
            vm.recovery_percentage,
            vm.human_activity_detected,
            vm.activity_type
        FROM fire_events fe
        LEFT JOIN LATERAL (
            SELECT
                months_after_fire,
                recovery_percentage,
                human_activity_detected,
                activity_type
            FROM vegetation_monitoring
            WHERE fire_event_id = fe.id
            ORDER BY months_after_fire DESC
            LIMIT 1
        ) vm ON true
        WHERE (:province IS NULL OR fe.province = :province)
        AND fe.start_date < NOW() - (INTERVAL '1 month' * :min_months)
        ORDER BY fe.start_date DESC
        LIMIT :limit
    """
    )

    try:
        results = db.execute(
            query,
            {"province": province, "min_months": min_months, "limit": limit},
        ).fetchall()
    except Exception as exc:
        logger.error(
            "Failed to query recovery summary",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_msg": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=503,
            detail="Servicio de análisis temporalmente no disponible, reintente en unos instantes.",
        )

    fires = []
    status_counts = {
        "full_recovery": 0,
        "advanced_recovery": 0,
        "moderate_recovery": 0,
        "early_recovery": 0,
        "stalled": 0,
        "not_started": 0,
        "anomaly_detected": 0,
        "pending": 0,
    }
    suspicious_count = 0

    for row in results:
        recovery_pct = getattr(row, "recovery_percentage", None)
        has_activity = bool(getattr(row, "human_activity_detected", False))
        activity_type = getattr(row, "activity_type", None)

        # Check suspicious activity types
        if activity_type in [
            "bare_soil",
            "no_recovery",
            "construction",
            "agriculture",
        ]:
            has_activity = True

        recovery_status = _classify_status(recovery_pct, has_activity)
        is_suspicious = recovery_status == "anomaly_detected"
        if is_suspicious:
            suspicious_count += 1

        status_counts[recovery_status] += 1

        fires.append(
            RecoverySummaryItem(
                fire_event_id=str(row.fire_event_id),
                fire_date=row.start_date.isoformat()
                if hasattr(row.start_date, "isoformat")
                else str(row.start_date),
                province=getattr(row, "province", None),
                recovery_status=recovery_status,
                recovery_percentage=recovery_pct,
                is_suspicious=is_suspicious,
            )
        )

    return RecoverySummaryResponse(
        total_fires=len(fires),
        fires_analyzed=len(
            [f for f in fires if f.recovery_status != "pending"]
        ),
        status_breakdown=status_counts,
        suspicious_count=suspicious_count,
        fires=fires,
    )


@router.get(
    "/recovery/by-episode/{episode_id}",
    response_model=RecoveryResponse,
    summary="Get aggregated recovery timeline by episode",
    description="""
    **Fase 6 / analisis_ndvi Mejora 3:** Recovery agregado por episodio.

    Returns vegetation recovery data aggregated across all fire events
    belonging to the episode. Uses AVG(ndvi_mean), AVG(recovery_percentage),
    AVG(baseline_ndvi) per calendar month. Structure compatible with RecoveryResponse.
    """,
    responses={
        200: {"description": "Aggregated recovery timeline"},
        404: {"description": "Episode not found"},
    },
)
async def get_recovery_by_episode(
    episode_id: UUID,
    max_months: int = Query(default=36, ge=1, le=36),
    db: Session = Depends(get_db),
) -> RecoveryResponse:
    """Aggregated recovery by episode (JOIN vm + fire_events + fire_episode_events)."""
    start_time = time.time()

    episode_row = db.execute(
        text(
            "SELECT id, start_date, centroid_lat, centroid_lon "
            "FROM fire_episodes WHERE id = :eid"
        ),
        {"eid": str(episode_id)},
    ).fetchone()
    if not episode_row:
        raise HTTPException(status_code=404, detail="Episode not found")

    ep_start = episode_row.start_date
    ep_lat = float(episode_row.centroid_lat) if episode_row.centroid_lat is not None else 0.0
    ep_lon = float(episode_row.centroid_lon) if episode_row.centroid_lon is not None else 0.0

    agg_query = text(
        """
        SELECT
            DATE_TRUNC('month', vm.monitoring_date)::date AS month_start,
            AVG(vm.ndvi_mean) AS ndvi_mean,
            AVG(vm.recovery_percentage) AS recovery_percentage,
            AVG(vm.baseline_ndvi) AS baseline_ndvi,
            AVG(vm.cloud_cover_pct) AS cloud_cover_pct
        FROM vegetation_monitoring vm
        INNER JOIN fire_episode_events fee ON fee.event_id = vm.fire_event_id
        WHERE fee.episode_id = :eid
        AND vm.monitoring_date >= :ep_start
        AND vm.monitoring_date <= :ep_start + (INTERVAL '1 month' * :max_months)
        GROUP BY DATE_TRUNC('month', vm.monitoring_date)
        ORDER BY month_start ASC
        """
    )
    try:
        agg_rows = db.execute(
            agg_query,
            {
                "eid": str(episode_id),
                "ep_start": ep_start,
                "max_months": max_months,
            },
        ).fetchall()
    except Exception as exc:
        logger.error(
            "Failed to query recovery by episode",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_msg": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=503,
            detail="Servicio de análisis temporalmente no disponible, reintente en unos instantes.",
        )

    query_duration_ms = int((time.time() - start_time) * 1000)

    if not agg_rows:
        return RecoveryResponse(
            fire_event_id=str(episode_id),
            fire_date=ep_start.isoformat() if hasattr(ep_start, "isoformat") else str(ep_start),
            fire_location={"lat": ep_lat, "lon": ep_lon},
            baseline_ndvi=None,
            current_ndvi=None,
            months_monitored=0,
            recovery_status="pending",
            recovery_percentage=None,
            anomaly_detected=None,
            monitoring_data=[],
            query_duration_ms=query_duration_ms,
            message="No hay datos de monitoreo agregados para este episodio aún.",
        )

    monitoring_data = []
    baseline_ndvi = None
    for row in agg_rows:
        month_start = row.month_start
        ndvi = float(row.ndvi_mean) if row.ndvi_mean is not None else 0.0
        rec_pct = float(row.recovery_percentage) if row.recovery_percentage is not None else None
        base_ndvi = float(row.baseline_ndvi) if row.baseline_ndvi is not None else None
        cloud = float(row.cloud_cover_pct) if getattr(row, "cloud_cover_pct", None) is not None else None
        if baseline_ndvi is None and base_ndvi is not None:
            baseline_ndvi = base_ndvi
        months_after = (
            (month_start.year - ep_start.year) * 12
            + (month_start.month - ep_start.month)
            if hasattr(ep_start, "year") and hasattr(month_start, "year")
            else 0
        )
        monitoring_data.append(
            MonthlyNDVI(
                month=max(0, months_after),
                date=month_start.isoformat() if hasattr(month_start, "isoformat") else str(month_start),
                ndvi_mean=ndvi,
                recovery_percentage=rec_pct,
                cloud_cover_pct=cloud,
            )
        )

    latest = agg_rows[-1]
    current_ndvi = float(latest.ndvi_mean) if latest.ndvi_mean is not None else None
    current_recovery = float(latest.recovery_percentage) if latest.recovery_percentage is not None else None
    recovery_status = _classify_status(current_recovery, False)
    if baseline_ndvi is None and agg_rows:
        baseline_ndvi = next(
            (float(r.baseline_ndvi) for r in agg_rows if r.baseline_ndvi is not None),
            None,
        )

    return RecoveryResponse(
        fire_event_id=str(episode_id),
        fire_date=ep_start.isoformat() if hasattr(ep_start, "isoformat") else str(ep_start),
        fire_location={"lat": ep_lat, "lon": ep_lon},
        baseline_ndvi=baseline_ndvi,
        current_ndvi=current_ndvi,
        months_monitored=len(monitoring_data),
        recovery_status=recovery_status,
        recovery_percentage=current_recovery,
        anomaly_detected=None,
        monitoring_data=monitoring_data,
        query_duration_ms=query_duration_ms,
    )


@router.get(
    "/recovery/{fire_event_id}",
    response_model=RecoveryResponse,
    summary="Get vegetation recovery timeline",
    description="""
    **UC-06 / UC-F12: Vegetation Recovery Monitoring**

    Returns vegetation recovery data for a fire event. Reads from the
    `vegetation_monitoring` table (populated by background workers).

    If no monitoring data exists yet, returns `status: "pending"` with
    an empty monitoring_data array.

    **Recovery Status Classifications:**
    - `full_recovery`: >=90% recovered
    - `advanced_recovery`: 70-90% recovered
    - `moderate_recovery`: 40-70% recovered
    - `early_recovery`: 10-40% recovered
    - `stalled`: 0-10% recovered
    - `not_started`: Negative recovery
    - `anomaly_detected`: Abnormal pattern detected
    - `pending`: No monitoring data yet
    """,
    responses={
        200: {"description": "Recovery timeline retrieved successfully"},
        404: {"description": "Fire event not found"},
    },
)
async def get_recovery_status(
    fire_event_id: UUID,
    max_months: int = Query(
        default=36, ge=1, le=36, description="Max months to analyze"
    ),
    db: Session = Depends(get_db),
) -> RecoveryResponse:
    """
    Get vegetation recovery timeline for a fire event.

    Reads pre-computed data from vegetation_monitoring table.
    If no data exists, returns pending status.
    """
    start_time = time.time()

    # Fetch fire event details
    fire_query = text(
        """
        SELECT
            id,
            start_date,
            province,
            ST_Y(centroid::geometry) as lat,
            ST_X(centroid::geometry) as lon
        FROM fire_events
        WHERE id = :fire_id
    """
    )

    result = db.execute(fire_query, {"fire_id": str(fire_event_id)}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Fire event not found")

    fire_date = result.start_date
    fire_lat = result.lat
    fire_lon = result.lon

    # Read monitoring data from DB (populated by workers)
    monitoring_query = text(
        """
        SELECT
            months_after_fire,
            monitoring_date,
            ndvi_mean,
            baseline_ndvi,
            recovery_percentage,
            cloud_cover_pct,
            recovery_status,
            human_activity_detected,
            activity_type,
            classification_confidence
        FROM vegetation_monitoring
        WHERE fire_event_id = :fire_id
        AND months_after_fire <= :max_months
        ORDER BY monitoring_date ASC
    """
    )

    try:
        rows = db.execute(
            monitoring_query,
            {"fire_id": str(fire_event_id), "max_months": max_months},
        ).fetchall()
    except Exception as exc:
        logger.error(
            "Failed to query vegetation_monitoring",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_msg": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=503,
            detail="Servicio de análisis temporalmente no disponible, reintente en unos instantes.",
        )

    query_duration_ms = int((time.time() - start_time) * 1000)

    # No monitoring data yet — encolar análisis y devolver pending
    if not rows:
        _enqueue_recovery_if_not_pending(str(fire_event_id))
        return RecoveryResponse(
            fire_event_id=str(fire_event_id),
            fire_date=fire_date.isoformat()
            if hasattr(fire_date, "isoformat")
            else str(fire_date),
            fire_location={"lat": fire_lat, "lon": fire_lon},
            baseline_ndvi=None,
            current_ndvi=None,
            months_monitored=0,
            recovery_status="pending",
            recovery_percentage=None,
            anomaly_detected=None,
            monitoring_data=[],
            query_duration_ms=query_duration_ms,
            message="Análisis en proceso. Los datos estarán disponibles en los próximos minutos.",
        )

    # Build response from DB data
    monitoring_data = []
    baseline_ndvi = None
    latest_activity_type = None

    for row in rows:
        if baseline_ndvi is None and row.baseline_ndvi is not None:
            baseline_ndvi = float(row.baseline_ndvi)

        monitoring_data.append(
            MonthlyNDVI(
                month=row.months_after_fire or 0,
                date=row.monitoring_date.isoformat()
                if hasattr(row.monitoring_date, "isoformat")
                else str(row.monitoring_date),
                ndvi_mean=float(row.ndvi_mean) if row.ndvi_mean is not None else 0.0,
                recovery_percentage=float(row.recovery_percentage)
                if row.recovery_percentage is not None
                else None,
                cloud_cover_pct=float(row.cloud_cover_pct)
                if getattr(row, "cloud_cover_pct", None) is not None
                else None,
            )
        )

        if row.human_activity_detected:
            latest_activity_type = row.activity_type

    # Determine current status from latest row
    latest = rows[-1]
    current_ndvi = float(latest.ndvi_mean) if latest.ndvi_mean is not None else None
    current_recovery = (
        float(latest.recovery_percentage)
        if latest.recovery_percentage is not None
        else None
    )
    has_activity = bool(latest.human_activity_detected)
    recovery_status = _classify_status(current_recovery, has_activity)

    return RecoveryResponse(
        fire_event_id=str(fire_event_id),
        fire_date=fire_date.isoformat()
        if hasattr(fire_date, "isoformat")
        else str(fire_date),
        fire_location={"lat": fire_lat, "lon": fire_lon},
        baseline_ndvi=baseline_ndvi,
        current_ndvi=current_ndvi,
        months_monitored=len(monitoring_data),
        recovery_status=recovery_status,
        recovery_percentage=current_recovery,
        anomaly_detected=latest_activity_type,
        monitoring_data=monitoring_data,
        query_duration_ms=query_duration_ms,
    )


@router.get(
    "/land-use-changes/{fire_event_id}",
    response_model=LandUseChangesResponse,
    summary="Get land use changes for a fire event",
    description="""
    **UC-F12: Land Use Change Detection**

    Returns detected land use changes in the area of a fire event.
    Changes are detected by background workers analyzing satellite imagery.

    Changes flagged as `is_potential_violation = true` may indicate
    illegal activity under Law 26.815 Art. 22 bis.
    """,
    responses={
        200: {"description": "Land use changes retrieved"},
        404: {"description": "Fire event not found"},
    },
)
async def get_land_use_changes(
    fire_event_id: UUID,
    db: Session = Depends(get_db),
) -> LandUseChangesResponse:
    """Get land use changes for a fire event from the land_use_changes table."""

    # Verify fire event exists
    fire_check = text(
        "SELECT id FROM fire_events WHERE id = :fire_id"
    )
    if not db.execute(fire_check, {"fire_id": str(fire_event_id)}).fetchone():
        raise HTTPException(status_code=404, detail="Fire event not found")

    query = text(
        """
        SELECT
            id,
            change_detected_at,
            months_after_fire,
            change_type,
            change_severity,
            affected_area_hectares,
            is_potential_violation,
            violation_confidence,
            status,
            notes
        FROM land_use_changes
        WHERE fire_event_id = :fire_id
        ORDER BY change_detected_at ASC
    """
    )

    try:
        rows = db.execute(query, {"fire_id": str(fire_event_id)}).fetchall()
    except Exception as exc:
        logger.error(
            "Failed to query land_use_changes",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_msg": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=503,
            detail="Servicio de análisis temporalmente no disponible, reintente en unos instantes.",
        )

    changes = []
    violation_count = 0

    for row in rows:
        is_violation = bool(getattr(row, "is_potential_violation", False))
        if is_violation:
            violation_count += 1

        changes.append(
            LandUseChangeItem(
                id=str(row.id),
                change_detected_at=row.change_detected_at.isoformat()
                if hasattr(row.change_detected_at, "isoformat")
                else str(row.change_detected_at),
                months_after_fire=getattr(row, "months_after_fire", None),
                change_type=row.change_type or "unknown",
                change_severity=getattr(row, "change_severity", None),
                affected_area_hectares=getattr(row, "affected_area_hectares", None),
                is_potential_violation=is_violation,
                violation_confidence=getattr(row, "violation_confidence", None),
                status=row.status or "pending_review",
                notes=getattr(row, "notes", None),
            )
        )

    return LandUseChangesResponse(
        fire_event_id=str(fire_event_id),
        total_changes=len(changes),
        violation_count=violation_count,
        changes=changes,
    )


@router.post(
    "/recovery/trigger",
    response_model=TriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual recovery analysis (admin only)",
    description="""
    **Admin Only** — Manually triggers a vegetation recovery analysis
    for a specific fire event. The analysis runs asynchronously via
    the `vae` Celery queue.

    Rate limited: 5 requests/6h per user and 10 requests/hour per IP (GEE quota).
    429 responses include retry_after (seconds) in body.
    """,
    responses={
        202: {"description": "Analysis job queued"},
        403: {"description": "Admin role required"},
        404: {"description": "Fire event not found"},
        429: {"description": "Rate limit exceeded (detail.retry_after in seconds)"},
    },
    dependencies=[Depends(_trigger_rate_limit), Depends(_trigger_ip_limit)],
)
async def trigger_recovery_analysis(
    fire_event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TriggerResponse:
    """Manually trigger recovery analysis for a fire event (admin only)."""

    # Admin check
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to trigger analysis",
        )

    # Verify fire event exists
    fire_check = text(
        "SELECT id FROM fire_events WHERE id = :fire_id"
    )
    if not db.execute(fire_check, {"fire_id": str(fire_event_id)}).fetchone():
        raise HTTPException(status_code=404, detail="Fire event not found")

    # Enqueue recovery and destruction tasks (cola gee, Fase 2)
    try:
        from workers.tasks.recovery import analyze_recovery
        from workers.tasks.destruction import detect_destruction

        analyze_recovery.apply_async(
            args=[str(fire_event_id)],
            queue="gee",
        )
        detect_destruction.apply_async(
            args=[str(fire_event_id)],
            queue="gee",
        )
    except Exception as exc:
        logger.error(
            "Failed to enqueue recovery/destruction tasks",
            exc_info=True,
            extra={"error_type": type(exc).__name__, "error_msg": str(exc)[:500]},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Servicio de análisis temporalmente no disponible, reintente en unos instantes.",
        )

    return TriggerResponse(
        fire_event_id=str(fire_event_id),
        status="queued",
        message="Recovery and land-use analysis jobs enqueued on gee queue",
    )
