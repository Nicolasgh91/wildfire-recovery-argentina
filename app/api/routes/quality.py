"""
=============================================================================
FORESTGUARD API - QUALITY ENDPOINTS (UC-10)
=============================================================================

Data quality and reliability metrics for fire events.

Use Cases:
    - UC-10: Calidad del Dato - Reliability scores for forensic use
    - Validate data for legal proceedings
    - Identify data gaps and coverage issues

Features:
    - Reliability score calculation (0-100)
    - Data source metadata
    - Coverage analysis
    - Uncertainty quantification

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

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


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(prefix="/quality", tags=["Calidad de Datos"])


# =============================================================================
# SCHEMAS
# =============================================================================

class DataSource(BaseModel):
    """Data source metadata."""
    name: str
    provider: str
    resolution_meters: int
    temporal_resolution_hours: int
    coverage: str
    url: Optional[str] = None


class QualityMetrics(BaseModel):
    """Detailed quality metrics for a fire event."""
    
    # Core reliability score (0-100)
    reliability_score: float = Field(..., ge=0, le=100, description="Overall reliability score")
    reliability_grade: str = Field(..., description="Grade: A (excellent) to F (poor)")
    
    # Component scores
    confidence_score: float = Field(..., description="Based on detection confidence (40% weight)")
    imagery_score: float = Field(..., description="Based on satellite imagery availability (20% weight)")
    climate_score: float = Field(..., description="Based on climate data availability (20% weight)")
    detection_score: float = Field(..., description="Based on detection count (20% weight)")
    
    # Data completeness
    has_satellite_imagery: bool
    has_climate_data: bool
    has_ndvi_analysis: bool
    detection_count: int
    
    # Uncertainty bounds
    area_uncertainty_pct: Optional[float] = Field(None, description="Area estimate uncertainty %")
    date_uncertainty_days: Optional[int] = Field(None, description="Date uncertainty in days")


class QualityResponse(BaseModel):
    """Response for quality metrics endpoint."""
    fire_event_id: str
    fire_date: str
    province: Optional[str]
    
    # Quality assessment
    metrics: QualityMetrics
    
    # Data sources used
    data_sources: List[DataSource]
    
    # Recommendations
    recommendations: List[str]
    
    # Legal usability
    suitable_for_legal: bool
    legal_notes: Optional[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "fire_event_id": "550e8400...",
                "fire_date": "2024-08-15",
                "province": "Chaco",
                "metrics": {
                    "reliability_score": 85.5,
                    "reliability_grade": "B",
                    "confidence_score": 90.0,
                    "imagery_score": 80.0,
                    "climate_score": 75.0,
                    "detection_score": 100.0,
                    "has_satellite_imagery": True,
                    "has_climate_data": True,
                    "has_ndvi_analysis": True,
                    "detection_count": 15
                },
                "data_sources": [],
                "recommendations": [],
                "suitable_for_legal": True,
                "legal_notes": None
            }
        }


class BatchQualityResponse(BaseModel):
    """Response for batch quality assessment."""
    total_events: int
    assessed: int
    average_reliability: float
    grade_distribution: dict
    legal_suitable_count: int
    events: List[dict]


# =============================================================================
# CONSTANTS
# =============================================================================

# Standard data sources
DATA_SOURCES = [
    DataSource(
        name="NASA FIRMS VIIRS",
        provider="NASA",
        resolution_meters=375,
        temporal_resolution_hours=12,
        coverage="Global",
        url="https://firms.modaps.eosdis.nasa.gov/"
    ),
    DataSource(
        name="NASA FIRMS MODIS",
        provider="NASA",
        resolution_meters=1000,
        temporal_resolution_hours=12,
        coverage="Global",
        url="https://firms.modaps.eosdis.nasa.gov/"
    ),
    DataSource(
        name="Copernicus Sentinel-2",
        provider="ESA",
        resolution_meters=10,
        temporal_resolution_hours=120,  # 5 days
        coverage="Global land",
        url="https://scihub.copernicus.eu/"
    ),
    DataSource(
        name="ERA5-Land",
        provider="ECMWF",
        resolution_meters=9000,
        temporal_resolution_hours=1,
        coverage="Global",
        url="https://cds.climate.copernicus.eu/"
    )
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calculate_reliability_score(
    avg_confidence: float,
    detection_count: int,
    has_imagery: bool,
    has_climate: bool
) -> float:
    """
    Calculate overall reliability score (0-100).
    
    Weights:
    - avg_confidence: 40%
    - has_imagery: 20%
    - has_climate: 20%
    - detection_count >= 3: 20%
    """
    # Confidence score (normalized to 0-100)
    confidence_score = min(avg_confidence, 100) * 0.4
    
    # Imagery score
    imagery_score = 20 if has_imagery else 0
    
    # Climate score
    climate_score = 20 if has_climate else 0
    
    # Detection count score
    if detection_count >= 5:
        detection_score = 20
    elif detection_count >= 3:
        detection_score = 15
    elif detection_count >= 1:
        detection_score = 10
    else:
        detection_score = 0
    
    total = confidence_score + imagery_score + climate_score + detection_score
    return round(total, 1)


def get_reliability_grade(score: float) -> str:
    """Convert score to letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def get_recommendations(metrics: QualityMetrics) -> List[str]:
    """Generate recommendations based on quality metrics."""
    recommendations = []
    
    if not metrics.has_satellite_imagery:
        recommendations.append(
            "Satellite imagery not available. Request manual imagery acquisition "
            "or use alternative sources (Planet, Landsat-9)."
        )
    
    if not metrics.has_climate_data:
        recommendations.append(
            "Climate data missing. Cross-reference with local weather stations "
            "for temperature and wind data at the time of the fire."
        )
    
    if metrics.detection_count < 3:
        recommendations.append(
            "Low detection count may indicate a small or brief fire. "
            "Corroborate with ground reports if available."
        )
    
    if metrics.confidence_score < 70:
        recommendations.append(
            "Detection confidence is below threshold for legal use. "
            "Consider requesting ground verification."
        )
    
    if metrics.reliability_score < 60:
        recommendations.append(
            "Overall reliability is low. This data should be supplemented "
            "with additional evidence before use in legal proceedings."
        )
    
    if not recommendations:
        recommendations.append(
            "Data quality is adequate for standard reporting purposes."
        )
    
    return recommendations


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "/fire-event/{fire_event_id}",
    response_model=QualityResponse,
    summary="Get quality metrics for fire event",
    description="""
    **UC-10: Calidad del Dato (Data Quality)**
    
    Returns reliability score and metadata for a fire event.
    
    **Reliability Score Components:**
    - **Confidence Score (40%)**: Based on satellite detection confidence
    - **Imagery Score (20%)**: Whether satellite imagery is available
    - **Climate Score (20%)**: Whether climate data is available
    - **Detection Score (20%)**: Based on number of fire detections
    
    **Reliability Grades:**
    - **A (90-100)**: Excellent - High confidence data
    - **B (80-89)**: Good - Suitable for most purposes
    - **C (70-79)**: Acceptable - May need corroboration
    - **D (60-69)**: Limited - Should supplement with other data
    - **F (<60)**: Poor - Not recommended for legal use
    
    **Legal Use:**
    Events with grade C or higher (score >= 70) are considered
    suitable for legal proceedings under Ley 26.815.
    """,
    responses={
        200: {"description": "Quality metrics retrieved"},
        404: {"description": "Fire event not found"}
    }
)
async def get_fire_quality_metrics(
    fire_event_id: UUID,
    db: Session = Depends(get_db)
) -> QualityResponse:
    """
    Get data quality metrics for a fire event.
    """
    # Fetch fire event with quality indicators
    query = text("""
        SELECT 
            fe.id,
            fe.start_date,
            fe.province,
            fe.avg_confidence,
            fe.detection_count,
            fe.estimated_area_hectares,
            -- Check for related data
            EXISTS(SELECT 1 FROM satellite_images si WHERE si.fire_event_id = fe.id) as has_imagery,
            EXISTS(SELECT 1 FROM climate_observations co WHERE co.fire_event_id = fe.id) as has_climate,
            EXISTS(SELECT 1 FROM vegetation_monitoring vm WHERE vm.fire_event_id = fe.id) as has_ndvi
        FROM fire_events fe
        WHERE fe.id = :fire_id
    """)
    
    try:
        result = db.execute(query, {"fire_id": str(fire_event_id)}).fetchone()
    except Exception:
        # Simplified query if some tables don't exist
        query = text("""
            SELECT 
                id,
                start_date,
                province,
                avg_confidence,
                detection_count,
                estimated_area_hectares
            FROM fire_events
            WHERE id = :fire_id
        """)
        result = db.execute(query, {"fire_id": str(fire_event_id)}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Fire event not found")
    
    # Extract values with defaults
    avg_confidence = result.avg_confidence or 0
    detection_count = result.detection_count or getattr(result, 'detection_count', 1)
    has_imagery = getattr(result, 'has_imagery', False)
    has_climate = getattr(result, 'has_climate', False)
    has_ndvi = getattr(result, 'has_ndvi', False)
    
    # Calculate reliability score
    reliability_score = calculate_reliability_score(
        avg_confidence=avg_confidence,
        detection_count=detection_count,
        has_imagery=has_imagery,
        has_climate=has_climate
    )
    
    reliability_grade = get_reliability_grade(reliability_score)
    
    # Build metrics
    metrics = QualityMetrics(
        reliability_score=reliability_score,
        reliability_grade=reliability_grade,
        confidence_score=min(avg_confidence, 100),
        imagery_score=100 if has_imagery else 0,
        climate_score=100 if has_climate else 0,
        detection_score=100 if detection_count >= 3 else (detection_count / 3) * 100,
        has_satellite_imagery=has_imagery,
        has_climate_data=has_climate,
        has_ndvi_analysis=has_ndvi,
        detection_count=detection_count,
        area_uncertainty_pct=15.0 if detection_count < 5 else 10.0,
        date_uncertainty_days=1 if detection_count >= 3 else 2
    )
    
    # Get recommendations
    recommendations = get_recommendations(metrics)
    
    # Legal suitability
    suitable_for_legal = reliability_score >= 70
    legal_notes = None
    if not suitable_for_legal:
        legal_notes = (
            f"Reliability score {reliability_score:.1f} is below the 70-point threshold "
            "recommended for legal proceedings. Additional evidence is recommended."
        )
    
    return QualityResponse(
        fire_event_id=str(fire_event_id),
        fire_date=result.start_date.isoformat() if hasattr(result.start_date, 'isoformat') else str(result.start_date),
        province=result.province,
        metrics=metrics,
        data_sources=DATA_SOURCES,
        recommendations=recommendations,
        suitable_for_legal=suitable_for_legal,
        legal_notes=legal_notes
    )


@router.get(
    "/batch",
    response_model=BatchQualityResponse,
    summary="Batch quality assessment",
    description="Get quality assessment for multiple fire events."
)
async def batch_quality_assessment(
    province: Optional[str] = Query(None, description="Filter by province"),
    min_score: float = Query(default=0, ge=0, le=100, description="Minimum reliability score"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    db: Session = Depends(get_db)
) -> BatchQualityResponse:
    """
    Get quality metrics for multiple fire events.
    """
    query = text("""
        SELECT 
            id,
            start_date,
            province,
            avg_confidence,
            detection_count
        FROM fire_events
        WHERE (:province IS NULL OR province = :province)
        ORDER BY start_date DESC
        LIMIT :limit
    """)
    
    results = db.execute(query, {
        "province": province,
        "limit": limit
    }).fetchall()
    
    events = []
    grade_distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    total_score = 0
    legal_count = 0
    
    for row in results:
        avg_conf = row.avg_confidence or 0
        det_count = row.detection_count or 1
        
        score = calculate_reliability_score(avg_conf, det_count, False, False)
        grade = get_reliability_grade(score)
        
        grade_distribution[grade] += 1
        total_score += score
        if score >= 70:
            legal_count += 1
        
        events.append({
            "fire_event_id": str(row.id),
            "fire_date": row.start_date.isoformat() if hasattr(row.start_date, 'isoformat') else str(row.start_date),
            "province": row.province,
            "reliability_score": score,
            "reliability_grade": grade
        })
    
    avg_reliability = total_score / len(events) if events else 0
    
    return BatchQualityResponse(
        total_events=len(events),
        assessed=len(events),
        average_reliability=round(avg_reliability, 1),
        grade_distribution=grade_distribution,
        legal_suitable_count=legal_count,
        events=events
    )
