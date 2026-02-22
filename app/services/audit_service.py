"""
=============================================================================
FORESTGUARD - LAND USE AUDIT SERVICE (UC-01)
=============================================================================

Core service for Ley 26.815 land use change audit functionality.

Features:
    - Geospatial queries to find fires within radius of coordinates
    - Protected area intersection detection
    - Prohibition period calculation (30/60 years based on area type)
    - Audit response generation with cryptographic hash
    - Evidence thumbnail aggregation

Use Case:
    UC-01: Land Use Audit - Check if land is under fire prohibition
    
    A prospective buyer/developer queries coordinates to verify if land
    use change is prohibited due to historical fire activity. Returns
    prohibition status, affected fires, and evidence thumbnails.

Legal Context:
    Ley 26.815 (Argentina) prohibits land use changes in areas affected
    by fires for 30 years (general) or 60 years (in protected areas).

Response Includes:
    - is_prohibited: Boolean indicating active prohibition
    - prohibition_until: Date when prohibition expires
    - fires: List of fires affecting the queried location
    - evidence: Satellite imagery thumbnails for verification
    - audit_hash: SHA-256 hash for audit trail integrity

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.audit import AuditFire, AuditResponse, EvidenceThumbnail
from app.utils.hash_utils import sha256_with_secret

logger = logging.getLogger(__name__)

DEFAULT_RADIUS_METERS = 500
MAX_RADIUS_METERS = 5000


class AuditService:
    """Service layer for land use audit workflows."""
    def __init__(self, db: Session):
        self.db = db

    def _system_param_value(self, key: str, fallback: Any) -> Any:
        try:
            row = (
                self.db.execute(
                    text(
                        "SELECT param_value FROM system_parameters WHERE param_key = :key"
                    ),
                    {"key": key},
                )
                .mappings()
                .first()
            )
        except SQLAlchemyError as exc:
            logger.warning("system_parameters lookup failed for %s: %s", key, exc)
            return fallback

        if not row:
            return fallback

        value = row.get("param_value")
        if isinstance(value, dict) and "value" in value:
            return value["value"]
        return value if value is not None else fallback

    def resolve_radius(self, radius_meters: Optional[int]) -> int:
        default_radius = int(
            self._system_param_value(
                "audit_search_radius_default", DEFAULT_RADIUS_METERS
            )
        )
        max_radius = int(
            self._system_param_value("audit_search_radius_max", MAX_RADIUS_METERS)
        )

        if radius_meters is None:
            radius_meters = default_radius

        if radius_meters < 1:
            raise ValueError("radius_meters must be positive")
        if radius_meters > max_radius:
            raise ValueError(f"radius_meters exceeds max allowed ({max_radius})")
        return int(radius_meters)

    def _fetch_fire_rows(
        self, lat: float, lon: float, radius_meters: int
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        warnings: List[str] = []

        query = text(
            """
            SELECT
                fe.id AS fire_event_id,
                fe.start_date AS fire_date,
                fe.province,
                fe.estimated_area_hectares,
                fe.avg_confidence,
                ST_Distance(
                    fe.centroid::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distance_meters,
                MAX(fpa.prohibition_until) AS max_prohibition_until,
                array_remove(array_agg(DISTINCT pa.official_name), NULL) AS protected_area_names,
                array_remove(array_agg(DISTINCT pa.category), NULL) AS protected_area_categories
            FROM fire_events fe
            LEFT JOIN fire_protected_area_intersections fpa
                ON fpa.fire_event_id = fe.id
            LEFT JOIN protected_areas pa
                ON pa.id = fpa.protected_area_id
            WHERE ST_DWithin(
                fe.centroid::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            GROUP BY fe.id
            ORDER BY fe.start_date DESC
            """
        )

        try:
            rows = (
                self.db.execute(
                    query, {"lat": lat, "lon": lon, "radius": radius_meters}
                )
                .mappings()
                .all()
            )
            return [dict(row) for row in rows], warnings
        except SQLAlchemyError as exc:
            logger.warning("Protected area join failed: %s", exc)
            self.db.rollback()
            warnings.append("Protected areas data unavailable; using 30-year default.")

        fallback_query = text(
            """
            SELECT
                fe.id AS fire_event_id,
                fe.start_date AS fire_date,
                fe.province,
                fe.estimated_area_hectares,
                fe.avg_confidence,
                ST_Distance(
                    fe.centroid::geography,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                ) AS distance_meters
            FROM fire_events fe
            WHERE ST_DWithin(
                fe.centroid::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius
            )
            ORDER BY fe.start_date DESC
            """
        )

        rows = (
            self.db.execute(
                fallback_query, {"lat": lat, "lon": lon, "radius": radius_meters}
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows], warnings

    def _fire_date(self, value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        raise ValueError("Invalid fire_date value")

    def _build_fire_entries(self, rows: Sequence[Dict[str, Any]]) -> List[AuditFire]:
        fires: List[AuditFire] = []
        today = date.today()

        for row in rows:
            fire_date = self._fire_date(row["fire_date"])
            max_prohibition = row.get("max_prohibition_until")
            if isinstance(max_prohibition, datetime):
                max_prohibition = max_prohibition.date()

            in_protected_area = max_prohibition is not None
            prohibition_until = (
                max_prohibition
                if max_prohibition is not None
                else fire_date + timedelta(days=30 * 365)
            )
            years_remaining = max(0, (prohibition_until - today).days // 365)

            protected_area_names = row.get("protected_area_names") or []
            protected_area_categories = row.get("protected_area_categories") or []

            protected_area_names = sorted(
                {name for name in protected_area_names if name}
            )
            protected_area_categories = sorted(
                {category for category in protected_area_categories if category}
            )

            fires.append(
                AuditFire(
                    fire_event_id=row["fire_event_id"],
                    fire_date=fire_date,
                    distance_meters=float(row.get("distance_meters") or 0),
                    in_protected_area=in_protected_area,
                    prohibition_until=prohibition_until,
                    years_remaining=years_remaining,
                    province=row.get("province"),
                    avg_confidence=float(row.get("avg_confidence"))
                    if row.get("avg_confidence") is not None
                    else None,
                    estimated_area_hectares=float(row.get("estimated_area_hectares"))
                    if row.get("estimated_area_hectares") is not None
                    else None,
                    protected_area_names=list(protected_area_names),
                    protected_area_categories=list(protected_area_categories),
                )
            )

        return fires

    def _fetch_thumbnails(self, fire_ids: Sequence[UUID]) -> List[EvidenceThumbnail]:
        if not fire_ids:
            return []

        query = text(
            """
                SELECT
                    fire_event_id,
                    thumbnail_url,
                    acquisition_date,
                    image_type,
                    gee_system_index
                FROM satellite_images
                WHERE fire_event_id IN :fire_ids
                  AND thumbnail_url IS NOT NULL
                ORDER BY acquisition_date DESC NULLS LAST
                """
        ).bindparams(bindparam("fire_ids", expanding=True))

        rows = (
            self.db.execute(query, {"fire_ids": [str(fid) for fid in fire_ids]})
            .mappings()
            .all()
        )

        thumbnails: List[EvidenceThumbnail] = []
        for row in rows:
            thumbnails.append(
                EvidenceThumbnail(
                    fire_event_id=row["fire_event_id"],
                    thumbnail_url=row["thumbnail_url"],
                    acquisition_date=row.get("acquisition_date"),
                    image_type=row.get("image_type"),
                    gee_system_index=row.get("gee_system_index"),
                )
            )
        return thumbnails

    @staticmethod
    def _violation_severity(years_remaining: int) -> str:
        if years_remaining <= 0:
            return "none"
        if years_remaining > 50:
            return "critical"
        if years_remaining > 30:
            return "high"
        if years_remaining > 10:
            return "medium"
        return "low"

    def _land_use_audits_columns(self) -> Optional[set[str]]:
        try:
            rows = self.db.execute(
                text(
                    """
                    SELECT column_name
                      FROM information_schema.columns
                     WHERE table_schema = 'public'
                       AND table_name = 'land_use_audits'
                    """
                )
            ).scalars()
            columns = {row for row in rows}
            return columns or None
        except SQLAlchemyError as exc:
            logger.warning("Could not introspect land_use_audits columns: %s", exc)
            return None

    def _build_audit_insert(
        self,
        available_columns: Optional[set[str]],
        *,
        include_report_json: bool = True,
    ):
        column_specs = [
            ("id", ":id"),
            ("queried_latitude", ":lat"),
            ("queried_longitude", ":lon"),
            (
                "queried_location",
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography",
            ),
            ("search_radius_meters", ":radius"),
            ("queried_at", "NOW()"),
            ("fires_found", ":fires_found"),
            ("earliest_fire_date", ":earliest_fire_date"),
            ("latest_fire_date", ":latest_fire_date"),
            ("prohibition_until", ":prohibition_until"),
            ("is_violation", ":is_violation"),
            ("violation_severity", ":violation_severity"),
            ("report_json", "CAST(:report_json AS jsonb)"),
            ("user_ip", ":user_ip"),
            ("user_agent", ":user_agent"),
            ("query_duration_ms", ":query_duration_ms"),
            ("created_at", "NOW()"),
        ]

        if not include_report_json:
            column_specs = [spec for spec in column_specs if spec[0] != "report_json"]

        if available_columns is not None:
            column_specs = [
                spec for spec in column_specs if spec[0] in available_columns
            ]

        columns = ",\n                ".join(spec[0] for spec in column_specs)
        values = ",\n                ".join(spec[1] for spec in column_specs)

        return text(
            f"""
            INSERT INTO land_use_audits (
                {columns}
            ) VALUES (
                {values}
            )
            """
        )

    def run_audit(
        self,
        *,
        lat: float,
        lon: float,
        radius_meters: Optional[int] = None,
        cadastral_id: Optional[str] = None,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditResponse:
        start_time = time.perf_counter()

        resolved_radius = self.resolve_radius(radius_meters)
        rows, warnings = self._fetch_fire_rows(lat, lon, resolved_radius)
        fires = self._build_fire_entries(rows)

        fires_sorted = sorted(
            fires,
            key=lambda item: (item.fire_date, str(item.fire_event_id)),
            reverse=True,
        )

        fire_ids = [fire.fire_event_id for fire in fires_sorted]
        thumbnails = self._fetch_thumbnails(fire_ids)
        thumbnails_sorted = sorted(
            thumbnails,
            key=lambda item: (
                str(item.fire_event_id),
                item.acquisition_date or date.min,
            ),
        )

        max_prohibition = max(
            (fire.prohibition_until for fire in fires_sorted), default=None
        )
        is_prohibited = bool(max_prohibition and max_prohibition > date.today())

        years_remaining = 0
        if max_prohibition:
            years_remaining = max(0, (max_prohibition - date.today()).days // 365)

        audit_id = uuid4()
        generated_at = datetime.now(timezone.utc)

        payload: Dict[str, Any] = {
            "audit_id": str(audit_id),
            "is_prohibited": is_prohibited,
            "prohibition_until": max_prohibition,
            "fires_found": len(fires_sorted),
            "fires": [fire.model_dump(mode="json") for fire in fires_sorted],
            "evidence": {
                "thumbnails": [
                    thumb.model_dump(mode="json") for thumb in thumbnails_sorted
                ]
            },
            "location": {"lat": lat, "lon": lon},
            "radius_meters": resolved_radius,
            "cadastral_id": cadastral_id,
            "warnings": warnings,
            "generated_at": generated_at,
        }

        secret = settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else None
        if not secret:
            raise RuntimeError("SECRET_KEY must be set to hash audit responses")

        audit_hash = sha256_with_secret(payload, secret)
        payload["audit_hash"] = audit_hash

        query_duration_ms = int((time.perf_counter() - start_time) * 1000)
        violation_severity = self._violation_severity(years_remaining)

        available_columns = self._land_use_audits_columns()
        audit_insert = self._build_audit_insert(available_columns)

        fire_dates = [fire.fire_date for fire in fires_sorted]
        earliest_fire_date = min(fire_dates) if fire_dates else None
        latest_fire_date = max(fire_dates) if fire_dates else None

        insert_params = {
            "id": str(audit_id),
            "lat": lat,
            "lon": lon,
            "radius": resolved_radius,
            "fires_found": len(fires_sorted),
            "earliest_fire_date": earliest_fire_date,
            "latest_fire_date": latest_fire_date,
            "prohibition_until": max_prohibition,
            "is_violation": is_prohibited,
            "violation_severity": violation_severity,
            "report_json": json.dumps(payload, default=str),
            "user_ip": user_ip,
            "user_agent": user_agent,
            "query_duration_ms": query_duration_ms,
        }

        try:
            self.db.execute(audit_insert, insert_params)
        except SQLAlchemyError as exc:
            if "report_json" in str(exc):
                logger.warning("report_json column missing, retrying without it")
                self.db.rollback()
                audit_insert = self._build_audit_insert(
                    available_columns, include_report_json=False
                )
                self.db.execute(audit_insert, insert_params)
            else:
                raise
        self.db.commit()

        return AuditResponse.model_validate(payload)
