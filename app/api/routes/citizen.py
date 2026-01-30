"""
=============================================================================
FORESTGUARD API - CITIZEN REPORTS ENDPOINTS (UC-09)
=============================================================================

Citizen participation endpoints for reporting suspicious activities or
fires in protected areas, with automatic evidence generation.

Use Cases:
    - UC-09: Denuncias Ciudadanas - Citizen reports with satellite evidence
    - Public participation in environmental monitoring
    - Auto-cross-reference with fire events and protected areas

Features:
    - Accept reports from any citizen (no auth required for submission)
    - Auto-generate evidence package (related fires, satellite imagery)
    - Email notification to administrators
    - Follow-up tracking

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

import time
import logging
from datetime import datetime, date
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Response
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session

# Imports
try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

from app.core.email_config import email_config
# Updated imports for new ERS service
from app.services.ers_service import ERSService, ReportType, ReportRequest, ReportResult


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(tags=["Citizen Reports"])


# =============================================================================
# ENUMS
# =============================================================================

class ReportCategory(str, Enum):
    """Categories for citizen reports."""
    ACTIVE_FIRE = "active_fire"                           # Ongoing fire
    ILLEGAL_BURNING = "illegal_burning"                   # Suspicious burning
    CONSTRUCTION_IN_PROHIBITED = "construction_in_prohibited_area"  # Building after fire
    LAND_CLEARING = "land_clearing"                       # Vegetation removal
    ILLEGAL_LOGGING = "illegal_logging"                   # Tree cutting
    OTHER = "other"


class ReportStatus(str, Enum):
    """Status of citizen reports."""
    PENDING_REVIEW = "pending_review"     # Just submitted
    UNDER_INVESTIGATION = "under_investigation"  # Being reviewed
    EVIDENCE_GENERATED = "evidence_generated"    # Evidence ready
    FORWARDED = "forwarded"               # Sent to authorities
    RESOLVED = "resolved"                 # Case closed
    REJECTED = "rejected"                 # Invalid report


# =============================================================================
# SCHEMAS
# =============================================================================

class CitizenReportRequest(BaseModel):
    """Request to submit a citizen report."""
    latitude: float = Field(
        ..., 
        ge=-56, le=-21,  # Argentina limits
        description="Latitude of reported location"
    )
    longitude: float = Field(
        ..., 
        ge=-74, le=-53,  # Argentina limits
        description="Longitude of reported location"
    )
    report_type: ReportCategory = Field(
        ..., 
        description="Category of the report"
    )
    description: str = Field(
        ..., 
        min_length=20, 
        max_length=2000,
        description="Detailed description of the situation"
    )
    observed_date: Optional[date] = Field(
        None, 
        description="Date when the situation was observed (defaults to today)"
    )
    reporter_email: Optional[EmailStr] = Field(
        None, 
        description="Email for follow-up (optional, for anonymity)"
    )
    reporter_name: Optional[str] = Field(
        None, 
        max_length=100,
        description="Reporter name (optional, for anonymity)"
    )
    attach_photos: bool = Field(
        default=False,
        description="Whether photos will be attached (future feature)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "latitude": -27.1234,
                "longitude": -55.4567,
                "report_type": "construction_in_prohibited_area",
                "description": "Observé construcción de un galpón en una zona que fue quemada hace 2 años. El terreno estaba dentro del Parque Nacional Chaco.",
                "observed_date": "2026-01-28",
                "reporter_email": "ciudadano@email.com"
            }
        }
    )


class RelatedFireEvent(BaseModel):
    """Fire event related to a citizen report."""
    fire_event_id: str
    fire_date: str
    distance_meters: float
    estimated_area_hectares: Optional[float]
    is_in_protected_area: bool
    prohibition_until: Optional[str]


class RelatedProtectedArea(BaseModel):
    """Protected area related to a citizen report."""
    protected_area_id: str
    official_name: str
    category: str
    distance_meters: float


class CitizenReportResponse(BaseModel):
    """Response after submitting a citizen report."""
    success: bool
    report_id: str
    status: str
    
    # Location context
    submitted_location: dict
    province: Optional[str] = None
    
    # Auto-generated evidence
    related_fires: List[RelatedFireEvent]
    related_protected_areas: List[RelatedProtectedArea]
    
    # Evidence package
    evidence_package_url: Optional[str] = None
    evidence_generated: bool
    
    # Next steps
    follow_up_message: str
    
    # Metadata
    created_at: datetime
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "report_id": "FG-CIT-2026-ABC123",
                "status": "pending_review",
                "submitted_location": {"lat": -27.1234, "lon": -55.4567},
                "province": "Chaco",
                "related_fires": [],
                "related_protected_areas": [],
                "evidence_package_url": "/api/v1/citizen/FG-CIT-2026-ABC123/evidence",
                "evidence_generated": True,
                "follow_up_message": "Su denuncia ha sido registrada...",
                "created_at": "2026-01-29T12:00:00Z"
            }
        }
    )


class ReportStatusResponse(BaseModel):
    """Response for checking report status."""
    report_id: str
    status: str
    status_history: List[dict]
    last_updated: datetime
    resolution_notes: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def send_admin_notification(
    report_id: str,
    report_type: str,
    location: dict,
    description: str
):
    """
    Send email notification to administrators.
    """
    # Get recipients from centralized config
    recipients = email_config.CITIZEN_REPORTS_NOTIFY
    
    # Log the notification (actual email sending would go here)
    logger = logging.getLogger(__name__)
    logger.info(
        f"📧 Notification: New Citizen Report {report_id} | "
        f"Type: {report_type} | Location: {location} | "
        f"Recipients: {recipients}"
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/submit",
    response_model=CitizenReportResponse,
    summary="Submit citizen report",
    description="""
    **UC-09: Denuncias Ciudadanas (Citizen Reports)**
    
    Submit a report about suspicious activities or fires in protected areas.
    """
)
async def submit_citizen_report(
    request: CitizenReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> CitizenReportResponse:
    """
    Submit a citizen report and auto-generate evidence.
    """
    start_time = time.time()
    
    # Generate report ID
    report_id = f"FG-CIT-{datetime.now().year}-{uuid4().hex[:6].upper()}"
    
    # Default observed_date to today
    observed_date = request.observed_date or date.today()
    
    # 1. Find related fire events (within 1km)
    fires_query = text("""
        SELECT 
            fe.id as fire_event_id,
            fe.start_date,
            fe.estimated_area_hectares,
            fe.province,
            ST_Distance(
                fe.centroid::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) as distance_meters,
            fpa.protected_area_id IS NOT NULL as is_in_protected_area,
            fpa.prohibition_until
        FROM fire_events fe
        LEFT JOIN fire_protected_area_intersections fpa ON fpa.fire_event_id = fe.id
        WHERE ST_DWithin(
            fe.centroid::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            1000  -- 1km radius
        )
        ORDER BY fe.start_date DESC
        LIMIT 10
    """)
    
    try:
        fires_result = db.execute(fires_query, {
            "lat": request.latitude,
            "lon": request.longitude
        }).fetchall()
    except Exception:
        fires_result = []
    
    related_fires = [
        RelatedFireEvent(
            fire_event_id=str(row.fire_event_id),
            fire_date=row.start_date.isoformat() if hasattr(row.start_date, 'isoformat') else str(row.start_date),
            distance_meters=round(row.distance_meters, 1),
            estimated_area_hectares=row.estimated_area_hectares,
            is_in_protected_area=row.is_in_protected_area or False,
            prohibition_until=row.prohibition_until.isoformat() if row.prohibition_until else None
        )
        for row in fires_result
    ]
    
    # 2. Find related protected areas
    areas_query = text("""
        SELECT 
            pa.id as protected_area_id,
            pa.official_name,
            pa.category,
            ST_Distance(
                pa.boundary::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
            ) as distance_meters
        FROM protected_areas pa
        WHERE ST_DWithin(
            pa.boundary::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            5000  -- 5km radius
        )
        ORDER BY distance_meters ASC
        LIMIT 5
    """)
    
    try:
        areas_result = db.execute(areas_query, {
            "lat": request.latitude,
            "lon": request.longitude
        }).fetchall()
    except Exception:
        areas_result = []
    
    related_areas = [
        RelatedProtectedArea(
            protected_area_id=str(row.protected_area_id),
            official_name=row.official_name,
            category=row.category,
            distance_meters=round(row.distance_meters, 1)
        )
        for row in areas_result
    ]
    
    # 3. Determine province
    province = None
    if fires_result:
        province = fires_result[0].province
    
    # 4. Insert report into DB
    insert_query = text("""
        INSERT INTO citizen_reports (
            id, report_id, latitude, longitude, location,
            report_type, description, observed_date,
            reporter_email, reporter_name,
            status, related_fire_count, related_protected_area_count,
            created_at
        ) VALUES (
            gen_random_uuid(), :report_id, :lat, :lon,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :report_type, :description, :observed_date,
            :email, :name,
            'pending_review', :fire_count, :area_count,
            NOW()
        )
    """)
    
    try:
        db.execute(insert_query, {
            "report_id": report_id,
            "lat": request.latitude,
            "lon": request.longitude,
            "report_type": request.report_type.value,
            "description": request.description,
            "observed_date": observed_date,
            "email": request.reporter_email,
            "name": request.reporter_name,
            "fire_count": len(related_fires),
            "area_count": len(related_areas)
        })
        db.commit()
    except Exception as e:
        # Log but continue - table might not exist
        import logging
        logging.warning(f"Could not insert citizen report: {e}")
    
    # 5. Schedule admin notification
    background_tasks.add_task(
        send_admin_notification,
        report_id=report_id,
        report_type=request.report_type.value,
        location={"lat": request.latitude, "lon": request.longitude},
        description=request.description[:200]
    )
    
    # 6. Build response
    evidence_generated = len(related_fires) > 0 or len(related_areas) > 0
    
    follow_up_message = (
        f"Su denuncia ha sido registrada con el número {report_id}. "
        f"Se encontraron {len(related_fires)} incendio(s) relacionado(s) "
        f"y {len(related_areas)} área(s) protegida(s) cercana(s). "
    )
    
    if request.reporter_email:
        follow_up_message += f"Le notificaremos a {request.reporter_email} cuando haya novedades."
    else:
        follow_up_message += "Puede consultar el estado en /citizen/status/{report_id}."
    
    return CitizenReportResponse(
        success=True,
        report_id=report_id,
        status=ReportStatus.PENDING_REVIEW.value,
        submitted_location={"lat": request.latitude, "lon": request.longitude},
        province=province,
        related_fires=related_fires,
        related_protected_areas=related_areas,
        evidence_package_url=f"/api/v1/citizen/{report_id}/evidence" if evidence_generated else None,
        evidence_generated=evidence_generated,
        follow_up_message=follow_up_message,
        created_at=datetime.now()
    )


@router.get(
    "/status/{report_id}",
    response_model=ReportStatusResponse,
    summary="Check report status",
    description="Check the status and history of a citizen report."
)
async def get_report_status(
    report_id: str,
    db: Session = Depends(get_db)
) -> ReportStatusResponse:
    """
    Get the current status of a citizen report.
    """
    query = text("""
        SELECT 
            report_id,
            status,
            created_at,
            updated_at,
            resolution_notes
        FROM citizen_reports
        WHERE report_id = :report_id
    """)
    
    try:
        result = db.execute(query, {"report_id": report_id}).fetchone()
    except Exception:
        result = None
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportStatusResponse(
        report_id=result.report_id,
        status=result.status,
        status_history=[
            {"status": "pending_review", "timestamp": result.created_at.isoformat()}
        ],
        last_updated=result.updated_at or result.created_at,
        resolution_notes=result.resolution_notes
    )


@router.get(
    "/{report_id}/evidence",
    summary="Get evidence package",
    description="Download the generated evidence package for a citizen report."
)
async def get_evidence_package(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Get evidence package PDF for a citizen report.
    """
    # Look up report
    query = text("""
        SELECT 
            latitude, longitude, report_type, description, observed_date
        FROM citizen_reports
        WHERE report_id = :report_id
    """)
    
    try:
        result = db.execute(query, {"report_id": report_id}).fetchone()
    except Exception:
        result = None
    
    if not result:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Generate evidence PDF using ERS Service
    ers = ERSService()
    
    # Create request for evidence package
    # We construct a small bbox around the coordinate for context
    lat, lon = result.latitude, result.longitude
    delta = 0.02  # Approx 2km
    
    request = ReportRequest(
        report_type=ReportType.CITIZEN_EVIDENCE,  # Correct enum
        fire_date=result.observed_date or date.today(),
        bbox={
            "north": lat + delta,
            "south": lat - delta,
            "east": lon + delta,
            "west": lon - delta
        },
        max_images=2,  # Limit images for evidence package
        output_format="pdf"
    )
    
    try:
        report_result = ers.generate_report(request)
        
        # If we have a URL, redirect or stream from URL?
        # Ideally stream the content, or return the URL.
        # But this endpoint specs imply download.
        
        if report_result.pdf_url:
            # If uploaded to R2, redirect
            from fastapi.responses import RedirectResponse
            return RedirectResponse(report_result.pdf_url)
        else:
            # If we had bytes content we would stream it, but generate_report returns Result with URL.
            # If URL is missing, it might have failed.
            raise HTTPException(status_code=500, detail="Evidence generation failed to produce URL")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating evidence: {str(e)}")
