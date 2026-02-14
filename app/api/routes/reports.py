"""
=============================================================================
FORESTGUARD API - REPORTS ENDPOINTS (UC-02, UC-11)
=============================================================================

Report generation endpoints for legal and historical documentation.

Use Cases:
    - UC-02: Peritaje Judicial - Forensic evidence for court cases
    - UC-11: Reportes Históricos - Historical fire reports for protected areas

Endpoints:
    - POST /reports/judicial - Generate forensic report (idempotent)
    - POST /reports/historical - Generate historical fire report (idempotent)
    - GET /reports/{report_id} - Retrieve existing report
    - GET /reports/{report_id}/verify - Verify report hash

Idempotency:
-----------
POST endpoints support idempotency keys via the X-Idempotency-Key header.
If the same key is sent again, the cached response is returned without
generating a duplicate report.

Author: ForestGuard Team
Version: 1.1.0
Last Updated: 2026-01-29
=============================================================================
"""

import hashlib
import io
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

# Imports
try:
    from app.db.session import get_db
except ImportError:
    from app.api.deps import get_db

# Use correct imports from the new service structure
from app.core.idempotency import IdempotencyManager, get_idempotency_key
from app.core.rate_limiter import check_rate_limit
from app.api.auth_deps import get_current_user
from app.services.ers_service import (
    ERSService,
    ReportRequest,
    ReportResult,
    ReportStatus,
    ReportType,
)

# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


def _classify_judicial_failure(error_message: Optional[str]) -> tuple[int, str]:
    raw = (error_message or "Unknown error").strip()
    lower = raw.lower()

    if "fire event not found" in lower:
        return 404, "Evento de incendio no encontrado"

    validation_markers = (
        "required",
        "invalid",
        "must be",
        "validation",
        "date",
    )
    if any(marker in lower for marker in validation_markers):
        return 400, raw

    return 503, raw


# =============================================================================
# SCHEMAS
# =============================================================================


class JudicialReportRequest(BaseModel):
    """Request for judicial forensic report generation."""

    fire_event_id: UUID = Field(..., description="UUID of fire event")
    report_type: str = Field(
        default="full_forensic",
        description="Type: full_forensic, summary, chronology",
    )
    include_climate: bool = Field(
        default=True, description="Include climate data"
    )
    include_imagery: bool = Field(
        default=True, description="Include satellite imagery"
    )
    language: Literal["es"] = Field(default="es", description="Language: es")
    requester_name: Optional[str] = Field(
        None, description="Name of requesting party"
    )
    case_reference: Optional[str] = Field(
        None, description="Court case reference number"
    )


class HistoricalReportRequestBase(BaseModel):
    """Request for historical fire report."""

    protected_area_id: Optional[UUID] = Field(
        None, description="Protected area UUID"
    )
    protected_area_name: Optional[str] = Field(
        None, description="Protected area name (alternative)"
    )
    start_date: date = Field(
        ..., description="Start date for historical query"
    )
    end_date: date = Field(..., description="End date for historical query")
    include_monthly_images: bool = Field(
        default=True, description="Include monthly post-fire images"
    )
    max_images: int = Field(
        default=12, ge=1, le=12, description="Max images to include"
    )
    language: Literal["es"] = Field(default="es", description="Language: es")


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
                    "download_url": "/api/v1/reports/FG-JUD-2026-A1B2C3/download",
                },
                "query_duration_ms": 3500,
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
    
    **Idempotency Support**: Send `X-Idempotency-Key` header with a unique ID (UUID recommended)
    to prevent duplicate report generation on retry. Cached responses expire after 24 hours.
    """,
    dependencies=[Depends(check_rate_limit)],
)
async def generate_judicial_report(
    payload: JudicialReportRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user=Depends(get_current_user),
) -> JudicialReportResponse:
    """
    Generate forensic judicial report for a fire event.

    Supports idempotency via X-Idempotency-Key header.
    """
    endpoint = "/api/v1/reports/judicial"
    idempotency = IdempotencyManager(db)
    request_id = getattr(http_request.state, "request_id", None)

    # Check for cached response (idempotency)
    cached = await idempotency.get_cached_response(
        idempotency_key, endpoint, payload.model_dump(mode="json")
    )
    if cached:
        return JSONResponse(
            content=cached["body"],
            status_code=cached["status"],
            headers={"X-Idempotency-Replayed": "true"},
        )

    start_time = time.time()

    # Initialize ERS Service
    ers = ERSService(db=db)

    requester_id = hashlib.sha256(
        str(current_user.id).encode("utf-8")
    ).hexdigest()

    # Create ERS ReportRequest
    ers_request = ReportRequest(
        report_type=ReportType.JUDICIAL,
        fire_event_id=str(payload.fire_event_id),
        requester_name=payload.requester_name,
        requester_email=current_user.email,
        requester_id=requester_id,
        case_reference=payload.case_reference,
        include_climate=payload.include_climate,
        include_imagery=payload.include_imagery,
        language=payload.language,
        output_format="pdf",
    )

    try:
        # Generate report using new service
        # This handles data fetching, analysis, and PDF generation
        result = ers.generate_report(ers_request)
        if result.status == ReportStatus.FAILED:
            status_code, message = _classify_judicial_failure(result.error_message)
            log_payload = {
                "request_id": request_id,
                "user_id": str(current_user.id),
                "fire_event_id": str(payload.fire_event_id),
                "endpoint": endpoint,
                "idempotency_key_present": bool(idempotency_key),
                "error_type": "ers_failed",
                "error_message": result.error_message or "Unknown error",
                "status_code": status_code,
            }
            if status_code >= 500:
                logger.error("judicial_report_failed", extra=log_payload)
                raise HTTPException(
                    status_code=status_code,
                    detail={
                        "message": f"Report generation failed: {message}",
                        "request_id": request_id,
                    },
                )

            logger.warning("judicial_report_failed", extra=log_payload)
            raise HTTPException(
                status_code=status_code,
                detail=f"Report generation failed: {message}",
            )

        # Store report metadata in DB (if table exists)
        # Note: In a real migration we would ensure table exists
        insert_query = text(
            """
            INSERT INTO generated_reports (
                id, report_type, fire_event_id, verification_hash,
                generated_at, valid_until, requester_name, case_reference,
                pdf_size_bytes
            ) VALUES (
                :report_id, 'judicial', :fire_id, :hash,
                NOW(), NOW() + INTERVAL '1 year', :requester, :case_ref,
                :size
            )
        """
        )

        try:
            db.execute(
                insert_query,
                {
                    "report_id": result.report_id,
                    "fire_id": str(payload.fire_event_id),
                    "hash": result.verification_hash,
                    "requester": payload.requester_name,
                    "case_ref": payload.case_reference,
                    "size": 0,  # We don't have size here easily without head request or from upload result
                },
            )
            db.commit()
        except Exception as write_exc:
            # Table might not exist yet or constraints - continue without storing for now
            logger.warning(
                "judicial_report_metadata_persist_failed request_id=%s report_id=%s error=%s",
                request_id,
                result.report_id,
                write_exc,
            )

        query_duration_ms = int((time.time() - start_time) * 1000)
        now = datetime.now()

        response = JudicialReportResponse(
            success=True,
            report=ReportMetadataResponse(
                report_id=result.report_id,
                report_type="judicial",
                fire_event_id=str(payload.fire_event_id),
                generated_at=now,
                valid_until=datetime(now.year + 1, now.month, now.day),
                verification_hash=result.verification_hash,
                pdf_url=result.pdf_url
                or f"/api/v1/reports/{result.report_id}",
                download_url=f"/api/v1/reports/{result.report_id}/download",
            ),
            query_duration_ms=query_duration_ms,
        )

        # Cache response for idempotency
        await idempotency.cache_response(
            idempotency_key,
            endpoint,
            payload.model_dump(mode="json"),
            200,
            response.model_dump(mode="json"),
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "judicial_report_unhandled_error request_id=%s user_id=%s fire_event_id=%s endpoint=%s idempotency_key_present=%s error_type=%s error_message=%s",
            request_id,
            current_user.id,
            payload.fire_event_id,
            endpoint,
            bool(idempotency_key),
            type(e).__name__,
            str(e),
        )
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Error generating report",
                "request_id": request_id,
            },
        )


@router.post(
    "/historical",
    response_model=HistoricalResponse,
    summary="Generate historical fire report",
    description="""
    **UC-11: Reportes Históricos**
    
    Generates a historical fire report for a protected area and date range.
    
    **Idempotency Support**: Send `X-Idempotency-Key` header with a unique ID (UUID recommended)
    to prevent duplicate report generation on retry. Cached responses expire after 24 hours.
    """,
    dependencies=[Depends(check_rate_limit)],
)
async def generate_historical_report(
    request: HistoricalReportRequestBase,
    db: Session = Depends(get_db),
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user=Depends(get_current_user),
) -> HistoricalResponse:
    """
    Generate historical fire report for a protected area.

    Supports idempotency via X-Idempotency-Key header.
    """
    endpoint = "/api/v1/reports/historical"
    idempotency = IdempotencyManager(db)

    # Check for cached response (idempotency)
    cached = await idempotency.get_cached_response(
        idempotency_key, endpoint, request.model_dump(mode="json")
    )
    if cached:
        return JSONResponse(
            content=cached["body"],
            status_code=cached["status"],
            headers={"X-Idempotency-Replayed": "true"},
        )

    start_time = time.time()

    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=400, detail="end_date must be after start_date"
        )

    # Initialize ERS Service
    ers = ERSService(db=db)

    # Create ERS ReportRequest
    ers_request = ReportRequest(
        report_type=ReportType.HISTORICAL,
        protected_area_id=str(request.protected_area_id)
        if request.protected_area_id
        else None,
        protected_area_name=request.protected_area_name,
        date_range_start=request.start_date,
        date_range_end=request.end_date,
        max_images=request.max_images,
        include_monthly_images=request.include_monthly_images,
        language=request.language,
        output_format="pdf",
    )

    try:
        result = ers.generate_report(ers_request)
        if result.status == ReportStatus.FAILED:
            raise HTTPException(
                status_code=503,
                detail=f"Report generation failed: {result.error_message or 'Unknown error'}",
            )

        query_duration_ms = int((time.time() - start_time) * 1000)
        now = datetime.now()

        response = HistoricalResponse(
            success=True,
            fires_included=result.fire_events_found,
            date_range={
                "start": request.start_date.isoformat(),
                "end": request.end_date.isoformat(),
            },
            report=ReportMetadataResponse(
                report_id=result.report_id,
                report_type="historical",
                protected_area_id=str(request.protected_area_id)
                if request.protected_area_id
                else None,
                generated_at=now,
                valid_until=datetime(now.year + 1, now.month, now.day),
                verification_hash=result.verification_hash,
                pdf_url=result.pdf_url
                or f"/api/v1/reports/{result.report_id}",
                download_url=f"/api/v1/reports/{result.report_id}/download",
            ),
            query_duration_ms=query_duration_ms,
        )

        # Cache response for idempotency
        await idempotency.cache_response(
            idempotency_key,
            endpoint,
            request.model_dump(mode="json"),
            200,
            response.model_dump(mode="json"),
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Error generating report: {str(e)}"
        )


@router.get(
    "/{report_id}/verify",
    response_model=VerifyReportResponse,
    summary="Verify report authenticity",
    description="Verify the SHA-256 hash of a generated report.",
)
async def verify_report(
    report_id: str,
    hash_to_verify: str = Query(..., description="SHA-256 hash to verify"),
    db: Session = Depends(get_db),
) -> VerifyReportResponse:
    """
    Verify report authenticity by comparing hashes.
    """
    # Look up stored hash
    query = text(
        """
        SELECT verification_hash
        FROM generated_reports
        WHERE id = :report_id
    """
    )

    try:
        result = db.execute(query, {"report_id": report_id}).fetchone()
    except Exception:
        db.rollback()
        result = None

    stored_hash = None
    if result:
        stored_hash = result.verification_hash

    if not stored_hash:
        try:
            audit_row = db.execute(
                text(
                    """
                    SELECT details::jsonb->>'verification_hash' AS verification_hash
                      FROM audit_events
                     WHERE action = 'report_generated'
                       AND details::jsonb->>'report_id' = :report_id
                     ORDER BY created_at DESC
                     LIMIT 1
                    """
                ),
                {"report_id": report_id},
            ).fetchone()
        except Exception:
            db.rollback()
            audit_row = None
        if audit_row:
            stored_hash = audit_row.verification_hash

    if not stored_hash:
        raise HTTPException(status_code=404, detail="Report not found")
    is_valid = stored_hash.lower() == hash_to_verify.lower()

    return VerifyReportResponse(
        is_valid=is_valid,
        report_id=report_id,
        original_hash=stored_hash[:16]
        + "..."
        + stored_hash[-16:],  # Partial for security
        verified_at=datetime.now(),
        message="Document is authentic"
        if is_valid
        else "Hash mismatch - document may be altered",
    )
