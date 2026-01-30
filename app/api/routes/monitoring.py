"""
=============================================================================
FORESTGUARD API - MONITORING ENDPOINTS (UC-06)
=============================================================================

Vegetation recovery monitoring endpoints for tracking post-fire vegetation
regeneration over 36 months.

Use Cases:
    - UC-06: Reforestación - Track vegetation recovery with NDVI
    - Monitor recovery progress for authorities and researchers
    - Identify areas with suspicious lack of recovery

Endpoints:
    - GET /monitoring/recovery/{fire_event_id} - Get recovery timeline
    - GET /monitoring/recovery/summary - Get summary for multiple fires

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

import time
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

# Imports
try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

from app.services.vae_service import VAEService, RecoveryStatus, AnomalyType


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================

class MonthlyNDVI(BaseModel):
    """Monthly NDVI measurement."""
    month: int = Field(..., ge=1, le=36, description="Month number after fire (1-36)")
    date: str = Field(..., description="ISO date of measurement")
    ndvi_mean: float = Field(..., ge=-1, le=1, description="Mean NDVI value")
    recovery_percentage: Optional[float] = Field(None, description="Recovery % relative to baseline")
    cloud_cover_pct: Optional[float] = Field(None, description="Cloud cover percentage")


class RecoveryResponse(BaseModel):
    """
    Response for recovery monitoring endpoint.
    
    Uses VAE Service to calculate NDVI timeline and recovery status.
    """
    fire_event_id: str
    fire_date: str
    fire_location: dict
    
    # Baseline and current status
    baseline_ndvi: Optional[float] = Field(None, description="Pre-fire NDVI baseline")
    current_ndvi: Optional[float] = Field(None, description="Latest NDVI measurement")
    
    # Recovery metrics
    months_monitored: int = Field(..., description="Number of months with data")
    recovery_status: str = Field(..., description="Overall recovery classification")
    recovery_percentage: Optional[float] = Field(None, description="Current recovery %")
    anomaly_detected: Optional[str] = Field(None, description="Anomaly type if any")
    
    # Timeline data
    monitoring_data: List[MonthlyNDVI]
    
    # Metadata
    query_duration_ms: int
    
    class Config:
        json_schema_extra = {
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
                "query_duration_ms": 1250
            }
        }


class RecoverySummaryItem(BaseModel):
    """Summary item for multiple fires."""
    fire_event_id: str
    fire_date: str
    province: Optional[str]
    recovery_status: str
    recovery_percentage: Optional[float]
    is_suspicious: bool


class RecoverySummaryResponse(BaseModel):
    """Response for recovery summary endpoint."""
    total_fires: int
    fires_analyzed: int
    status_breakdown: dict
    suspicious_count: int
    fires: List[RecoverySummaryItem]


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
    """
)
async def get_recovery_summary(
    province: Optional[str] = Query(None, description="Filter by province"),
    min_months: int = Query(default=6, ge=1, description="Minimum months since fire"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    db: Session = Depends(get_db)
) -> RecoverySummaryResponse:
    """
    Get recovery summary for multiple fire events.
    
    Returns a high-level summary without detailed NDVI timelines
    (those are stored in vegetation_monitoring table).
    """
    # Query fires with monitoring data
    query = text("""
        SELECT 
            fe.id as fire_event_id,
            fe.start_date,
            fe.province,
            vm.months_after_fire,
            vm.recovery_percentage,
            vm.anomaly_type
        FROM fire_events fe
        LEFT JOIN LATERAL (
            SELECT 
                months_after_fire,
                recovery_percentage,
                anomaly_type
            FROM vegetation_monitoring
            WHERE fire_event_id = fe.id
            ORDER BY months_after_fire DESC
            LIMIT 1
        ) vm ON true
        WHERE (:province IS NULL OR fe.province = :province)
        AND fe.start_date < NOW() - INTERVAL ':min_months months'
        ORDER BY fe.start_date DESC
        LIMIT :limit
    """)
    
    try:
        results = db.execute(query, {
            "province": province,
            "min_months": min_months,
            "limit": limit
        }).fetchall()
    except Exception:
        # If vegetation_monitoring table doesn't exist yet, return empty
        results = []
    
    # Process results
    fires = []
    status_counts = {
        "excellent": 0,
        "good": 0,
        "moderate": 0,
        "poor": 0,
        "critical": 0,
        "suspicious": 0,
        "unknown": 0
    }
    suspicious_count = 0
    
    for row in results:
        recovery_pct = row.recovery_percentage if hasattr(row, 'recovery_percentage') else None
        anomaly = row.anomaly_type if hasattr(row, 'anomaly_type') else None
        
        # Determine status
        if recovery_pct is None:
            status = "unknown"
        elif recovery_pct >= 90:
            status = "excellent"
        elif recovery_pct >= 70:
            status = "good"
        elif recovery_pct >= 50:
            status = "moderate"
        elif recovery_pct >= 25:
            status = "poor"
        else:
            status = "critical"
        
        is_suspicious = anomaly in ["bare_soil", "no_recovery", "construction", "agriculture"]
        if is_suspicious:
            status = "suspicious"
            suspicious_count += 1
        
        status_counts[status] += 1
        
        fires.append(RecoverySummaryItem(
            fire_event_id=str(row.fire_event_id),
            fire_date=row.start_date.isoformat() if hasattr(row.start_date, 'isoformat') else str(row.start_date),
            province=row.province if hasattr(row, 'province') else None,
            recovery_status=status,
            recovery_percentage=recovery_pct,
            is_suspicious=is_suspicious
        ))
    
    return RecoverySummaryResponse(
        total_fires=len(fires),
        fires_analyzed=len([f for f in fires if f.recovery_status != "unknown"]),
        status_breakdown=status_counts,
        suspicious_count=suspicious_count,
        fires=fires
    )


@router.get(
    "/recovery/{fire_event_id}",
    response_model=RecoveryResponse,
    summary="Get vegetation recovery timeline",
    description="""
    **UC-06: Vegetation Recovery Monitoring (Reforestación)**
    
    Tracks vegetation recovery over 36 months after a fire event using
    NDVI (Normalized Difference Vegetation Index) from Sentinel-2 imagery.
    
    **Returns:**
    - Baseline (pre-fire) NDVI
    - Monthly NDVI measurements
    - Recovery percentage for each month
    - Overall recovery status classification
    - Anomaly detection (bare soil, no recovery, etc.)
    
    **Recovery Status Classifications:**
    - `excellent`: >90% recovered
    - `good`: 70-90% recovered
    - `moderate`: 50-70% recovered
    - `poor`: 25-50% recovered
    - `critical`: <25% recovered
    - `suspicious`: Abnormal pattern detected
    
    **Note:** Initial call may be slow (10-30s) due to GEE processing.
    Subsequent calls use cached data.
    """,
    responses={
        200: {"description": "Recovery timeline retrieved successfully"},
        404: {"description": "Fire event not found"},
        503: {"description": "Google Earth Engine unavailable"}
    }
)
async def get_recovery_status(
    fire_event_id: UUID,
    max_months: int = Query(default=36, ge=1, le=36, description="Max months to analyze"),
    db: Session = Depends(get_db)
) -> RecoveryResponse:
    """
    Get vegetation recovery timeline for a fire event.
    
    Uses VAE Service to:
    1. Fetch pre-fire baseline NDVI
    2. Calculate monthly NDVI for each month since fire
    3. Compute recovery percentages
    4. Detect anomalies in the recovery pattern
    """
    start_time = time.time()
    
    # Fetch fire event details from DB
    fire_query = text("""
        SELECT 
            id,
            start_date,
            province,
            ST_Y(centroid::geometry) as lat,
            ST_X(centroid::geometry) as lon
        FROM fire_events
        WHERE id = :fire_id
    """)
    
    result = db.execute(fire_query, {"fire_id": str(fire_event_id)}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Fire event not found")
    
    fire_date = result.start_date
    fire_lat = result.lat
    fire_lon = result.lon
    
    try:
        # Initialize VAE Service
        vae = VAEService()
        
        # Get recovery timeline
        timeline = vae.get_recovery_timeline(
            fire_event_id=fire_event_id,
            fire_lat=fire_lat,
            fire_lon=fire_lon,
            fire_date=fire_date,
            max_months=max_months
        )
        
        # Build response
        monitoring_data = [
            MonthlyNDVI(
                month=m["month"],
                date=m["date"],
                ndvi_mean=m["ndvi_mean"],
                recovery_percentage=m.get("recovery_percentage"),
                cloud_cover_pct=m.get("cloud_cover_pct")
            )
            for m in timeline.get("monitoring_data", [])
        ]
        
        # Get current NDVI (latest measurement)
        current_ndvi = monitoring_data[-1].ndvi_mean if monitoring_data else None
        current_recovery = monitoring_data[-1].recovery_percentage if monitoring_data else None
        
        query_duration_ms = int((time.time() - start_time) * 1000)
        
        return RecoveryResponse(
            fire_event_id=str(fire_event_id),
            fire_date=fire_date.isoformat() if hasattr(fire_date, 'isoformat') else str(fire_date),
            fire_location={"lat": fire_lat, "lon": fire_lon},
            baseline_ndvi=timeline.get("baseline_ndvi"),
            current_ndvi=current_ndvi,
            months_monitored=len(monitoring_data),
            recovery_status=timeline.get("recovery_status", "unknown"),
            recovery_percentage=current_recovery,
            anomaly_detected=timeline.get("anomaly_detected"),
            monitoring_data=monitoring_data,
            query_duration_ms=query_duration_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error processing NDVI analysis: {str(e)}"
        )
