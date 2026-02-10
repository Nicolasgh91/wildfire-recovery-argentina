import csv
import io
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.visitor import (
    Shelter,
    VisitorLog,
    VisitorLogCompanion,
    VisitorLogRevision,
)
from app.schemas.visitor import (
    ShelterListResponse,
    ShelterResponse,
    VisitorLogCreate,
    VisitorLogListResponse,
    VisitorLogResponse,
    VisitorLogUpdate,
)
from app.services.visitor_service import can_edit_log

router = APIRouter()


@router.post(
    "/visitor-logs",
    response_model=VisitorLogResponse,
    summary="Create visitor log (UC-12)",
)
def create_visitor_log(
    request: VisitorLogCreate, db: Session = Depends(get_db)
) -> VisitorLogResponse:
    """Create a visitor log entry and persist companions."""
    shelter = (
        db.query(Shelter).filter(Shelter.id == request.shelter_id).first()
    )
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found")

    total_people = 1 + len(request.companions)
    log = VisitorLog(
        shelter_id=request.shelter_id,
        visit_date=request.visit_date,
        registration_type=request.registration_type,
        group_leader_name=request.group_leader_name,
        group_leader_document=request.group_leader_document,
        contact_email=request.contact_email,
        contact_phone=request.contact_phone,
        total_people=total_people,
    )

    for companion in request.companions:
        log.companions.append(
            VisitorLogCompanion(
                full_name=companion.full_name,
                age_range=companion.age_range,
                document=companion.document,
            )
        )

    db.add(log)
    db.commit()
    db.refresh(log)

    return VisitorLogResponse(
        id=log.id,
        shelter_id=log.shelter_id,
        visit_date=log.visit_date,
        registration_type=log.registration_type,
        group_leader_name=log.group_leader_name,
        group_leader_document=log.group_leader_document,
        contact_email=log.contact_email,
        contact_phone=log.contact_phone,
        total_people=log.total_people,
        companions=[
            {
                "full_name": c.full_name,
                "age_range": c.age_range,
                "document": c.document,
            }
            for c in log.companions
        ],
        created_at=log.created_at,
    )


@router.patch(
    "/visitor-logs/{log_id}",
    response_model=VisitorLogResponse,
    summary="Update visitor log (UC-12)",
)
def update_visitor_log(
    log_id: UUID, request: VisitorLogUpdate, db: Session = Depends(get_db)
) -> VisitorLogResponse:
    """Update an existing visitor log within the allowed edit window."""
    log = db.query(VisitorLog).filter(VisitorLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Visitor log not found")

    now = datetime.utcnow()
    if not can_edit_log(log.first_submitted_at or log.created_at, now):
        raise HTTPException(
            status_code=403, detail="Edit window expired (30 minutes)"
        )

    before_snapshot = {
        "registration_type": log.registration_type,
        "group_leader_name": log.group_leader_name,
        "group_leader_document": log.group_leader_document,
        "contact_email": log.contact_email,
        "contact_phone": log.contact_phone,
        "companions": [
            {
                "full_name": c.full_name,
                "age_range": c.age_range,
                "document": c.document,
            }
            for c in log.companions
        ],
    }

    if request.registration_type is not None:
        log.registration_type = request.registration_type
    if request.group_leader_name is not None:
        log.group_leader_name = request.group_leader_name
    if request.group_leader_document is not None:
        log.group_leader_document = request.group_leader_document
    if request.contact_email is not None:
        log.contact_email = request.contact_email
    if request.contact_phone is not None:
        log.contact_phone = request.contact_phone

    if request.companions is not None:
        log.companions.clear()
        for companion in request.companions:
            log.companions.append(
                VisitorLogCompanion(
                    full_name=companion.full_name,
                    age_range=companion.age_range,
                    document=companion.document,
                )
            )
        log.total_people = 1 + len(log.companions)

    revision = VisitorLogRevision(
        visitor_log_id=log.id,
        changes=f"before={before_snapshot}",
    )
    db.add(revision)
    db.commit()
    db.refresh(log)

    return VisitorLogResponse(
        id=log.id,
        shelter_id=log.shelter_id,
        visit_date=log.visit_date,
        registration_type=log.registration_type,
        group_leader_name=log.group_leader_name,
        group_leader_document=log.group_leader_document,
        contact_email=log.contact_email,
        contact_phone=log.contact_phone,
        total_people=log.total_people,
        companions=[
            {
                "full_name": c.full_name,
                "age_range": c.age_range,
                "document": c.document,
            }
            for c in log.companions
        ],
        created_at=log.created_at,
    )


@router.get(
    "/visitor-logs",
    response_model=VisitorLogListResponse,
    summary="List visitor logs (UC-12)",
)
def list_visitor_logs(
    shelter_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
) -> VisitorLogListResponse:
    """List visitor logs with optional shelter and date filters."""
    query = db.query(VisitorLog)
    if shelter_id:
        query = query.filter(VisitorLog.shelter_id == shelter_id)
    if date_from:
        query = query.filter(VisitorLog.visit_date >= date_from)
    if date_to:
        query = query.filter(VisitorLog.visit_date <= date_to)

    logs = query.order_by(VisitorLog.visit_date.desc()).all()

    return VisitorLogListResponse(
        total=len(logs),
        logs=[
            VisitorLogResponse(
                id=log.id,
                shelter_id=log.shelter_id,
                visit_date=log.visit_date,
                registration_type=log.registration_type,
                group_leader_name=log.group_leader_name,
                group_leader_document=log.group_leader_document,
                contact_email=log.contact_email,
                contact_phone=log.contact_phone,
                total_people=log.total_people,
                companions=[
                    {
                        "full_name": c.full_name,
                        "age_range": c.age_range,
                        "document": c.document,
                    }
                    for c in log.companions
                ],
                created_at=log.created_at,
            )
            for log in logs
        ],
    )


@router.get("/visitor-logs/export", summary="Export visitor logs (UC-12)")
def export_visitor_logs(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    shelter_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Export visitor logs as CSV with optional filters."""
    query = db.query(VisitorLog)
    if shelter_id:
        query = query.filter(VisitorLog.shelter_id == shelter_id)
    if date_from:
        query = query.filter(VisitorLog.visit_date >= date_from)
    if date_to:
        query = query.filter(VisitorLog.visit_date <= date_to)

    rows = query.order_by(VisitorLog.visit_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "shelter_id",
            "visit_date",
            "registration_type",
            "group_leader_name",
            "total_people",
            "created_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                str(row.id),
                str(row.shelter_id),
                row.visit_date.isoformat(),
                row.registration_type,
                row.group_leader_name,
                row.total_people,
                row.created_at.isoformat() if row.created_at else None,
            ]
        )

    output.seek(0)
    filename = (
        f"visitor_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/shelters",
    response_model=ShelterListResponse,
    summary="List shelters (UC-12)",
)
def list_shelters(
    province: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> ShelterListResponse:
    """List active shelters with optional province and name search filters."""
    shelter_query = db.query(Shelter).filter(Shelter.is_active.is_(True))
    if province:
        shelter_query = shelter_query.filter(Shelter.province == province)
    if query:
        shelter_query = shelter_query.filter(Shelter.name.ilike(f"%{query}%"))

    shelters = shelter_query.order_by(Shelter.name.asc()).all()

    return ShelterListResponse(
        total=len(shelters),
        shelters=[
            ShelterResponse(
                id=shelter.id,
                name=shelter.name,
                province=shelter.province,
                location_description=shelter.location_description,
                carrying_capacity=shelter.carrying_capacity,
                is_active=shelter.is_active,
            )
            for shelter in shelters
        ],
    )
