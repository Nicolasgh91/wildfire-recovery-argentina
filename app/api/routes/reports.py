"""
=============================================================================
FORESTGUARD API - REPORTS ENDPOINTS (UC-02, UC-11)
=============================================================================

Report generation endpoints for legal and historical documentation.

Use Cases:
    - UC-02: Peritaje Judicial - Forensic evidence for court cases
    - UC-11: Reportes Históricos - Historical fire reports for protected areas

Endpoints:
    - POST /reports/judicial - Generate forensic report
    - POST /reports/historical - Generate historical fire report
    - GET /reports/{report_id} - Retrieve existing report
    - GET /reports/{report_id}/verify - Verify report hash

Author: ForestGuard Team
Version: 1.0.0
Last Updated: 2026-01-29
=============================================================================
"""

import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Header, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import text
from sqlalchemy.orm import Session
import io

# Imports
try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

# Use correct imports from the new service structure
from app.services.ers_service import ERSService, ReportType, ReportRequest, ReportResult


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(tags=["Reports"])


# =============================================================================
# SCHEMAS
# =============================================================================

class JudicialReportRequest(BaseModel):
    """Request for judicial forensic report generation."""
    fire_event_id: UUID = Field(..., description="UUID of fire event")
    report_type: str = Field(
        default="full_forensic",
        description="Type: full_forensic, summary, chronology"
    )
    include_climate: bool = Field(default=True, description="Include climate data")
    include_imagery: bool = Field(default=True, description="Include satellite imagery")
    language: str = Field(default="es", description="Language: es/en")
    requester_name: Optional[str] = Field(None, description="Name of requesting party")
    case_reference: Optional[str] = Field(None, description="Court case reference number")


class HistoricalReportRequestBase(BaseModel):
    """Request for historical fire report."""
    protected_area_id: Optional[UUID] = Field(None, description="Protected area UUID")
    protected_area_name: Optional[str] = Field(None, description="Protected area name (alternative)")
    start_date: date = Field(..., description="Start date for historical query")
    end_date: date = Field(..., description="End date for historical query")
    include_monthly_images: bool = Field(default=True, description="Include monthly post-fire images")
    max_images: int = Field(default=12, ge=1, le=24, description="Max images to include")
    language: str = Field(default="es", description="Language: es/en")


class ReportMetadataResponse(BaseModel):
    """Response with report metadata."""
    report_id: str
    report_type: str
    fire_event_id: Optional[str] = None
    protected_area_id: Optional[str] = None
    generated_at: datetime
    valid_until: datetime
    verification_hash: str
    pdf_url: str
    download_url: str


class JudicialReportResponse(BaseModel):
    """Response for judicial report generation."""
    success: bool
    report: ReportMetadataResponse
    query_duration_ms: int
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "report": {
                    "report_id": "FG-JUD-2026-A1B2C3",
                    "report_type": "judicial",
                    "fire_event_id": "550e8400-e29b-41d4-a716-446655440000",
                    "generated_at": "2026-01-29T12:00:00Z",
                    "valid_until": "2027-01-29T12:00:00Z",
                    "verification_hash": "abc123...",
                    "pdf_url": "/api/v1/reports/FG-JUD-2026-A1B2C3",
                    "download_url": "/api/v1/reports/FG-JUD-2026-A1B2C3/download"
                },
                "query_duration_ms": 3500
            }
        }
    )


class HistoricalResponse(BaseModel):
    """Response for historical report generation."""
    success: bool
    fires_included: int
    date_range: dict
    report: ReportMetadataResponse
    query_duration_ms: int


class VerifyReportResponse(BaseModel):
    """Response for report verification."""
    is_valid: bool
    report_id: str
    original_hash: str
    verified_at: datetime
    message: str


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/judicial",
    response_model=JudicialReportResponse,
    summary="Generate forensic judicial report",
    description="""
    **UC-02: Peritaje Judicial**
    
    Generates a comprehensive forensic report for a specific fire event.
    Designed for legal proceedings, insurance claims, and official investigations.
    """
)
async def generate_judicial_report(
    request: JudicialReportRequest,
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> JudicialReportResponse:
    """
    Generate forensic judicial report for a fire event.
    """
    start_time = time.time()
    
    # Initialize ERS Service
    ers = ERSService()
    
    # Create ERS ReportRequest
    ers_request = ReportRequest(
        report_type=ReportType.JUDICIAL,
        fire_event_id=str(request.fire_event_id),
        requester_name=request.requester_name,
        requester_email=None,  # Could be added to request
        output_format="pdf"
    )
    
    try:
        # Generate report using new service
        # This handles data fetching, analysis, and PDF generation
        result = ers.generate_report(ers_request)
        
        # Store report metadata in DB (if table exists)
        # Note: In a real migration we would ensure table exists
        insert_query = text("""
            INSERT INTO generated_reports (
                id, report_type, fire_event_id, verification_hash,
                generated_at, valid_until, requester_name, case_reference,
                pdf_size_bytes
            ) VALUES (
                :report_id, 'judicial', :fire_id, :hash,
                NOW(), NOW() + INTERVAL '1 year', :requester, :case_ref,
                :size
            )
        """)
        
        try:
            db.execute(insert_query, {
                "report_id": result.report_id,
                "fire_id": str(request.fire_event_id),
                "hash": result.verification_hash,
                "requester": request.requester_name,
                "case_ref": request.case_reference,
                "size": 0 # We don't have size here easily without head request or from upload result
            })
            db.commit()
        except Exception:
            # Table might not exist yet or constraints - continue without storing for now
            pass
        
        query_duration_ms = int((time.time() - start_time) * 1000)
        now = datetime.now()
        
        return JudicialReportResponse(
            success=True,
            report=ReportMetadataResponse(
                report_id=result.report_id,
                report_type="judicial",
                fire_event_id=str(request.fire_event_id),
                generated_at=now,
                valid_until=datetime(now.year + 1, now.month, now.day),
                verification_hash=result.verification_hash,
                pdf_url=result.pdf_url or f"/api/v1/reports/{result.report_id}",
                download_url=f"/api/v1/reports/{result.report_id}/download"
            ),
            query_duration_ms=query_duration_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Error generating report: {str(e)}"
        )


@router.post(
    "/historical",
    response_model=HistoricalResponse,
    summary="Generate historical fire report",
    description="""
    **UC-11: Reportes Históricos**
    """
)
async def generate_historical_report(
    request: HistoricalReportRequestBase,
    db: Session = Depends(get_db)
) -> HistoricalResponse:
    """
    Generate historical fire report for a protected area.
    """
    start_time = time.time()
    
    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")
    
    # Initialize ERS Service
    ers = ERSService()
    
    # Create ERS ReportRequest
    ers_request = ReportRequest(
        report_type=ReportType.HISTORICAL,
        protected_area_id=str(request.protected_area_id) if request.protected_area_id else None,
        protected_area_name=request.protected_area_name,
        date_range_start=request.start_date,
        date_range_end=request.end_date,
        max_images=request.max_images,
        output_format="pdf"
    )
    
    try:
        result = ers.generate_report(ers_request)
        
        query_duration_ms = int((time.time() - start_time) * 1000)
        now = datetime.now()
        
        return HistoricalResponse(
            success=True,
            fires_included=result.fire_events_found,
            date_range={
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat()
            },
            report=ReportMetadataResponse(
                report_id=result.report_id,
                report_type="historical",
                protected_area_id=str(request.protected_area_id) if request.protected_area_id else None,
                generated_at=now,
                valid_until=datetime(now.year + 1, now.month, now.day),
                verification_hash=result.verification_hash,
                pdf_url=result.pdf_url or f"/api/v1/reports/{result.report_id}",
                download_url=f"/api/v1/reports/{result.report_id}/download"
            ),
            query_duration_ms=query_duration_ms
        )
    except Exception as e:
         raise HTTPException(
            status_code=503,
            detail=f"Error generating report: {str(e)}"
        )


@router.get(
    "/{report_id}/verify",
    response_model=VerifyReportResponse,
    summary="Verify report authenticity",
    description="Verify the SHA-256 hash of a generated report."
)
async def verify_report(
    report_id: str,
    hash_to_verify: str = Query(..., description="SHA-256 hash to verify"),
    db: Session = Depends(get_db)
) -> VerifyReportResponse:
    """
    Verify report authenticity by comparing hashes.
    """
    # Look up stored hash
    query = text("""
        SELECT verification_hash
        FROM generated_reports
        WHERE id = :report_id
    """)
    
    try:
        result = db.execute(query, {"report_id": report_id}).fetchone()
    except Exception:
        result = None
    
    if not result:
        # Also try via service just in case (though verification usually needs known correct hash)
        # Or if we want to support verification of file content vs hash, that's different.
        # Here we just verify against DB record.
        raise HTTPException(status_code=404, detail="Report not found")
    
    stored_hash = result.verification_hash
    is_valid = stored_hash.lower() == hash_to_verify.lower()
    
    return VerifyReportResponse(
        is_valid=is_valid,
        report_id=report_id,
        original_hash=stored_hash[:16] + "..." + stored_hash[-16:],  # Partial for security
        verified_at=datetime.now(),
        message="Document is authentic" if is_valid else "Hash mismatch - document may be altered"
    )
