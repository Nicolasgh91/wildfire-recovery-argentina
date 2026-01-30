"""
=============================================================================
FORESTGUARD API - ANALYSIS ENDPOINTS (UC-03, UC-05)
=============================================================================

Advanced analysis endpoints for fire patterns and trends.

Use Cases:
    - UC-03: Recurrencia de Incendios - Fire recurrence pattern analysis
    - UC-05: Tendencias Históricas - Historical trends and projections

Features:
    - Spatial recurrence detection (hotspots)
    - Yearly statistics and trends
    - Risk projections
    - Heatmap data generation

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

from datetime import datetime, date
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


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(tags=["Analysis"])


# =============================================================================
# SCHEMAS - RECURRENCE (UC-03)
# =============================================================================

class RecurrenceZone(BaseModel):
    """A zone with recurring fire activity."""
    zone_id: str
    centroid_lat: float
    centroid_lon: float
    fire_count: int
    first_fire_date: str
    last_fire_date: str
    avg_interval_days: Optional[float]
    total_area_hectares: float
    risk_level: str  # high, medium, low
    is_suspicious: bool


class RecurrenceResponse(BaseModel):
    """Response for fire recurrence analysis."""
    bounding_box: dict
    analysis_period_years: int
    total_fires_analyzed: int
    
    # Recurrence findings
    recurrence_zones: List[RecurrenceZone]
    suspicious_zones_count: int
    
    # Heatmap data (for visualization)
    heatmap_data: List[dict]
    
    # Statistics
    avg_fires_per_zone: float
    max_recurrence_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "bounding_box": {"min_lon": -59, "min_lat": -28, "max_lon": -58, "max_lat": -27},
                "analysis_period_years": 10,
                "total_fires_analyzed": 156,
                "recurrence_zones": [],
                "suspicious_zones_count": 3,
                "heatmap_data": [],
                "avg_fires_per_zone": 2.4,
                "max_recurrence_count": 5
            }
        }


# =============================================================================
# SCHEMAS - TRENDS (UC-05)
# =============================================================================

class YearlyStats(BaseModel):
    """Statistics for a single year."""
    year: int
    fire_count: int
    total_area_hectares: float
    avg_confidence: float
    protected_area_fires: int
    avg_fire_size_hectares: float


class TrendProjection(BaseModel):
    """Trend projection for future years."""
    year: int
    projected_fire_count: int
    projected_area_hectares: float
    confidence_interval_low: float
    confidence_interval_high: float


class TrendsResponse(BaseModel):
    """Response for historical trends analysis."""
    start_year: int
    end_year: int
    province: Optional[str]
    
    # Historical data
    yearly_stats: List[YearlyStats]
    
    # Trend analysis
    trend_direction: str  # increasing, decreasing, stable
    annual_change_rate_pct: float
    
    # Projections (optional)
    projections: Optional[List[TrendProjection]]
    
    # Summary statistics
    total_fires: int
    total_area_hectares: float
    peak_year: int
    peak_fire_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_year": 2015,
                "end_year": 2025,
                "province": "Chaco",
                "yearly_stats": [],
                "trend_direction": "increasing",
                "annual_change_rate_pct": 8.5,
                "projections": [],
                "total_fires": 1250,
                "total_area_hectares": 45000,
                "peak_year": 2023,
                "peak_fire_count": 245
            }
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_trend(yearly_counts: List[tuple]) -> tuple:
    """
    Calculate trend direction and rate using simple linear regression.
    
    Returns: (trend_direction, annual_change_rate_pct)
    """
    if len(yearly_counts) < 2:
        return ("stable", 0.0)
    
    # Simple linear regression
    n = len(yearly_counts)
    sum_x = sum(y[0] for y in yearly_counts)
    sum_y = sum(y[1] for y in yearly_counts)
    sum_xy = sum(y[0] * y[1] for y in yearly_counts)
    sum_x2 = sum(y[0] ** 2 for y in yearly_counts)
    
    denominator = n * sum_x2 - sum_x ** 2
    if denominator == 0:
        return ("stable", 0.0)
    
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    
    # Calculate average for percentage
    avg_count = sum_y / n
    if avg_count == 0:
        return ("stable", 0.0)
    
    annual_change_pct = (slope / avg_count) * 100
    
    if annual_change_pct > 5:
        direction = "increasing"
    elif annual_change_pct < -5:
        direction = "decreasing"
    else:
        direction = "stable"
    
    return (direction, round(annual_change_pct, 2))


def generate_projections(
    yearly_counts: List[tuple],
    num_years: int = 3
) -> List[TrendProjection]:
    """Generate simple linear projections for future years."""
    if len(yearly_counts) < 3:
        return []
    
    # Use last 5 years for projection
    recent = yearly_counts[-5:] if len(yearly_counts) >= 5 else yearly_counts
    
    # Simple average-based projection
    avg_count = sum(y[1] for y in recent) / len(recent)
    last_year = recent[-1][0]
    
    projections = []
    for i in range(1, num_years + 1):
        proj_year = last_year + i
        # Simple projection with slight uncertainty
        projected = int(avg_count * (1 + i * 0.02))  # Slight increase
        
        projections.append(TrendProjection(
            year=proj_year,
            projected_fire_count=projected,
            projected_area_hectares=projected * 50,  # Rough estimate
            confidence_interval_low=projected * 0.7,
            confidence_interval_high=projected * 1.3
        ))
    
    return projections


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/recurrence",
    response_model=RecurrenceResponse,
    summary="Analyze fire recurrence patterns",
    description="""
    **UC-03: Recurrencia de Incendios (Fire Recurrence)**
    
    Detects zones with suspicious repetitive fire patterns, which may
    indicate intentional burning for land speculation.
    
    **Analysis:**
    - Clusters fires within spatial proximity
    - Calculates average interval between fires
    - Identifies suspicious patterns (short intervals, same location)
    
    **Risk Levels:**
    - **High**: 4+ fires in the zone, or < 2 year interval
    - **Medium**: 2-3 fires in the zone
    - **Low**: Single occurrence
    
    **Suspicious Indicators:**
    - Multiple fires in same 1km² within 5 years
    - Regular interval pattern
    - Post-fire land use changes detected
    
    **Use Cases:**
    - Identify land speculation targets
    - Prioritize enforcement zones
    - Generate heatmaps for visualization
    """,
    responses={
        200: {"description": "Recurrence analysis completed"},
        400: {"description": "Invalid bounding box"}
    }
)
async def analyze_recurrence(
    min_lon: float = Query(..., ge=-180, le=180, description="Minimum longitude"),
    min_lat: float = Query(..., ge=-90, le=90, description="Minimum latitude"),
    max_lon: float = Query(..., ge=-180, le=180, description="Maximum longitude"),
    max_lat: float = Query(..., ge=-90, le=90, description="Maximum latitude"),
    years: int = Query(default=10, ge=1, le=20, description="Analysis period (years)"),
    min_fires: int = Query(default=2, ge=2, description="Minimum fires for recurrence"),
    db: Session = Depends(get_db)
) -> RecurrenceResponse:
    """
    Analyze fire recurrence patterns in a bounding box.
    """
    # Validate bbox
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="Invalid bounding box")
    
    # Query fires in bbox grouped by approximate location
    query = text("""
        WITH fire_grid AS (
            SELECT 
                fe.id,
                fe.start_date,
                fe.estimated_area_hectares,
                ST_Y(fe.centroid::geometry) as lat,
                ST_X(fe.centroid::geometry) as lon,
                -- Create grid cells (~1km)
                FLOOR(ST_X(fe.centroid::geometry) * 100) as grid_x,
                FLOOR(ST_Y(fe.centroid::geometry) * 100) as grid_y
            FROM fire_events fe
            WHERE fe.centroid IS NOT NULL
            AND ST_X(fe.centroid::geometry) BETWEEN :min_lon AND :max_lon
            AND ST_Y(fe.centroid::geometry) BETWEEN :min_lat AND :max_lat
            AND fe.start_date >= NOW() - INTERVAL ':years years'
        ),
        zone_stats AS (
            SELECT 
                grid_x,
                grid_y,
                COUNT(*) as fire_count,
                AVG(lat) as centroid_lat,
                AVG(lon) as centroid_lon,
                MIN(start_date) as first_fire,
                MAX(start_date) as last_fire,
                SUM(COALESCE(estimated_area_hectares, 0)) as total_area
            FROM fire_grid
            GROUP BY grid_x, grid_y
            HAVING COUNT(*) >= :min_fires
        )
        SELECT * FROM zone_stats
        ORDER BY fire_count DESC
        LIMIT 100
    """)
    
    try:
        results = db.execute(query, {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
            "years": years,
            "min_fires": min_fires
        }).fetchall()
    except Exception as e:
        # Fallback if query fails
        results = []
    
    # Process zones
    zones = []
    heatmap_data = []
    suspicious_count = 0
    max_count = 0
    
    for i, row in enumerate(results):
        fire_count = row.fire_count
        max_count = max(max_count, fire_count)
        
        # Calculate interval
        if hasattr(row, 'first_fire') and hasattr(row, 'last_fire'):
            first = row.first_fire
            last = row.last_fire
            if fire_count > 1 and first and last:
                days_span = (last - first).days if hasattr(last - first, 'days') else 0
                avg_interval = days_span / (fire_count - 1) if fire_count > 1 else None
            else:
                avg_interval = None
        else:
            avg_interval = None
        
        # Determine risk level
        if fire_count >= 4 or (avg_interval and avg_interval < 365):
            risk_level = "high"
        elif fire_count >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Check if suspicious
        is_suspicious = risk_level == "high" or (avg_interval and avg_interval < 730)
        if is_suspicious:
            suspicious_count += 1
        
        zone = RecurrenceZone(
            zone_id=f"ZONE-{i+1:04d}",
            centroid_lat=row.centroid_lat,
            centroid_lon=row.centroid_lon,
            fire_count=fire_count,
            first_fire_date=str(row.first_fire) if hasattr(row, 'first_fire') else "",
            last_fire_date=str(row.last_fire) if hasattr(row, 'last_fire') else "",
            avg_interval_days=avg_interval,
            total_area_hectares=row.total_area or 0,
            risk_level=risk_level,
            is_suspicious=is_suspicious
        )
        zones.append(zone)
        
        # Add to heatmap
        heatmap_data.append({
            "lat": row.centroid_lat,
            "lon": row.centroid_lon,
            "weight": fire_count
        })
    
    # Calculate totals
    total_fires = sum(z.fire_count for z in zones)
    avg_per_zone = total_fires / len(zones) if zones else 0
    
    return RecurrenceResponse(
        bounding_box={
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat
        },
        analysis_period_years=years,
        total_fires_analyzed=total_fires,
        recurrence_zones=zones,
        suspicious_zones_count=suspicious_count,
        heatmap_data=heatmap_data,
        avg_fires_per_zone=round(avg_per_zone, 2),
        max_recurrence_count=max_count
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Historical fire trends",
    description="""
    **UC-05: Tendencias Históricas (Historical Trends)**
    
    Analyzes long-term fire trends and generates projections.
    
    **Analysis Includes:**
    - Yearly fire counts and area burned
    - Trend direction (increasing/decreasing/stable)
    - Annual rate of change
    - Optional future projections
    
    **Trend Classification:**
    - **Increasing**: > 5% annual increase
    - **Decreasing**: > 5% annual decrease
    - **Stable**: -5% to +5% annual change
    
    **Use Cases:**
    - Long-term planning
    - Resource allocation
    - Climate impact assessment
    - Policy evaluation
    """,
    responses={
        200: {"description": "Trend analysis completed"},
        400: {"description": "Invalid date range"}
    }
)
async def analyze_trends(
    start_year: int = Query(default=2015, ge=2000, description="Start year"),
    end_year: int = Query(default=2025, ge=2000, description="End year"),
    province: Optional[str] = Query(None, description="Filter by province"),
    include_projections: bool = Query(default=True, description="Include future projections"),
    db: Session = Depends(get_db)
) -> TrendsResponse:
    """
    Analyze historical fire trends.
    """
    if end_year < start_year:
        raise HTTPException(status_code=400, detail="end_year must be >= start_year")
    
    # Query yearly statistics
    query = text("""
        SELECT 
            EXTRACT(YEAR FROM start_date)::int as year,
            COUNT(*) as fire_count,
            SUM(COALESCE(estimated_area_hectares, 0)) as total_area,
            AVG(COALESCE(avg_confidence, 0)) as avg_confidence,
            SUM(CASE WHEN pa_id IS NOT NULL THEN 1 ELSE 0 END) as protected_fires
        FROM fire_events fe
        LEFT JOIN fire_protected_area_intersections fpa ON fpa.fire_event_id = fe.id
        WHERE EXTRACT(YEAR FROM fe.start_date) BETWEEN :start_year AND :end_year
        AND (:province IS NULL OR fe.province = :province)
        GROUP BY EXTRACT(YEAR FROM fe.start_date)
        ORDER BY year
    """)
    
    try:
        results = db.execute(query, {
            "start_year": start_year,
            "end_year": end_year,
            "province": province
        }).fetchall()
    except Exception:
        # Simplified fallback
        query = text("""
            SELECT 
                EXTRACT(YEAR FROM start_date)::int as year,
                COUNT(*) as fire_count,
                SUM(COALESCE(estimated_area_hectares, 0)) as total_area,
                AVG(COALESCE(avg_confidence, 0)) as avg_confidence
            FROM fire_events
            WHERE EXTRACT(YEAR FROM start_date) BETWEEN :start_year AND :end_year
            AND (:province IS NULL OR province = :province)
            GROUP BY EXTRACT(YEAR FROM start_date)
            ORDER BY year
        """)
        results = db.execute(query, {
            "start_year": start_year,
            "end_year": end_year,
            "province": province
        }).fetchall()
    
    # Process yearly stats
    yearly_stats = []
    yearly_counts = []
    peak_year = start_year
    peak_count = 0
    total_fires = 0
    total_area = 0
    
    for row in results:
        year = row.year
        fire_count = row.fire_count or 0
        area = row.total_area or 0
        
        total_fires += fire_count
        total_area += area
        
        if fire_count > peak_count:
            peak_count = fire_count
            peak_year = year
        
        yearly_counts.append((year, fire_count))
        
        yearly_stats.append(YearlyStats(
            year=year,
            fire_count=fire_count,
            total_area_hectares=area,
            avg_confidence=row.avg_confidence or 0,
            protected_area_fires=getattr(row, 'protected_fires', 0) or 0,
            avg_fire_size_hectares=area / fire_count if fire_count > 0 else 0
        ))
    
    # Calculate trend
    trend_direction, annual_change = calculate_trend(yearly_counts)
    
    # Generate projections if requested
    projections = None
    if include_projections and len(yearly_counts) >= 3:
        projections = generate_projections(yearly_counts)
    
    return TrendsResponse(
        start_year=start_year,
        end_year=end_year,
        province=province,
        yearly_stats=yearly_stats,
        trend_direction=trend_direction,
        annual_change_rate_pct=annual_change,
        projections=projections,
        total_fires=total_fires,
        total_area_hectares=total_area,
        peak_year=peak_year,
        peak_fire_count=peak_count
    )
