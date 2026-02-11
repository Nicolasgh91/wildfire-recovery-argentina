"""
=============================================================================
FORESTGUARD - FIRE EVENT SERVICE (UC-13, UC-14)
=============================================================================

Core service for wildfire event management, filtering, and statistics.

Features:
    - Fire event listing with advanced filtering (province, date, status)
    - Pagination with configurable page sizes (SEC-001 compliant)
    - Geospatial queries (bounding box, protected area filtering)
    - Fire statistics aggregation (by province, by month)
    - Year-to-date comparisons and trend analysis
    - Saved filter management for user preferences

Use Cases:
    UC-13: Fire Event Listing - Browse and filter detected wildfires
    UC-14: Fire Event Details - Get comprehensive fire event information

Key Classes:
    FireFilterParams: Dataclass for filter parameters
    FireService: Main service class with all fire-related operations

Dependencies:
    - SQLAlchemy + GeoAlchemy2 for spatial queries
    - app.models.fire: FireEvent, FireDetection models
    - app.schemas.fire: Response schemas

Performance:
    - Uses spatial indices for bounding box queries
    - Subqueries for protected area intersections
    - Configurable page size limits via system_parameters

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import calendar
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import and_, asc, case, desc, func, or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.evidence import SatelliteImage
from app.models.episode import FireEpisodeEvent
from app.models.fire import FireDetection, FireEvent
from app.models.region import FireProtectedAreaIntersection, ProtectedArea
from app.schemas.fire import (
    DetectionBrief,
    ExplorationPreviewResponse,
    ExplorationPreviewTimeline,
    FireDetailResponse,
    FireEventDetail,
    FireEventListItem,
    FireListResponse,
    FireSearchItem,
    FireSearchResponse,
    FireStatistics,
    FireStatus,
    MetricComparison,
    PaginationMeta,
    ProtectedAreaBrief,
    ProvinceStats,
    SavedFilterCreate,
    SavedFilterResponse,
    SortField,
    StatsResponse,
    StatusScope,
    TopFrpFire,
    YtdComparison,
)

logger = logging.getLogger(__name__)

CENTROID_GEOMETRY = Geometry(geometry_type="POINT", srid=4326)
PERIMETER_GEOMETRY = Geometry(geometry_type="POLYGON", srid=4326)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class FireFilterParams:
    """Filter parameters for fire listing queries."""
    province: Optional[List[str]] = None
    department: Optional[str] = None
    protected_area_id: Optional[UUID] = None
    in_protected_area: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    active_only: Optional[bool] = None
    status_scope: Optional[StatusScope] = None
    min_confidence: Optional[float] = None
    min_detections: Optional[int] = None
    is_significant: Optional[bool] = None
    has_imagery: Optional[bool] = None
    search: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None


class FireService:
    """Service for fire event queries and aggregations."""
    def __init__(self, db: Session):
        self.db = db

    def resolve_fire_status(self, fire: FireEvent) -> FireStatus:
        if fire.status:
            try:
                return FireStatus(fire.status)
            except ValueError:
                pass

        now = datetime.now(timezone.utc)
        if fire.end_date:
            end_date = fire.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            days_since_end = (now - end_date).days
            if days_since_end < 0:
                return FireStatus.ACTIVE
            if days_since_end < 3:
                return FireStatus.CONTROLLED
            if days_since_end < 14:
                return FireStatus.MONITORING
        return FireStatus.EXTINGUISHED

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
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("system_parameters lookup failed for %s: %s", key, exc)
            return fallback

        if not row:
            return fallback

        value = row.get("param_value")
        if isinstance(value, dict) and "value" in value:
            return value["value"]
        return value if value is not None else fallback

    def clamp_page_size(self, page_size: Optional[int]) -> int:
        default = int(
            self._system_param_value("dashboard_page_size_default", DEFAULT_PAGE_SIZE)
        )
        max_size = int(
            self._system_param_value("dashboard_page_size_max", MAX_PAGE_SIZE)
        )

        if page_size is None:
            page_size = default
        if page_size < 1:
            page_size = 1
        if page_size > max_size:
            page_size = max_size
        return page_size

    def build_sort_clause(self, sort_by: SortField, sort_desc: bool):
        field_map = {
            SortField.START_DATE: FireEvent.start_date,
            SortField.END_DATE: FireEvent.end_date,
            SortField.PROVINCE: FireEvent.province,
            SortField.CONFIDENCE: FireEvent.avg_confidence,
            SortField.DETECTIONS: FireEvent.total_detections,
            SortField.FRP: FireEvent.max_frp,
            SortField.AREA: FireEvent.estimated_area_hectares,
        }
        field = field_map.get(sort_by, FireEvent.start_date)
        return desc(field) if sort_desc else asc(field)

    def _date_filter_bounds(self, date_from: Optional[date], date_to: Optional[date]):
        start_dt = (
            datetime.combine(date_from, time.min, tzinfo=timezone.utc)
            if date_from
            else None
        )
        end_dt = (
            datetime.combine(date_to, time.max, tzinfo=timezone.utc)
            if date_to
            else None
        )
        return start_dt, end_dt

    def build_filter_conditions(self, params: FireFilterParams) -> List[Any]:
        filters: List[Any] = []
        if params.province:
            filters.append(FireEvent.province.in_(params.province))

        if params.department:
            filters.append(FireEvent.department.ilike(f"%{params.department}%"))

        if params.protected_area_id:
            pa_exists = (
                self.db.query(FireProtectedAreaIntersection.id)
                .filter(
                    FireProtectedAreaIntersection.fire_event_id == FireEvent.id,
                    FireProtectedAreaIntersection.protected_area_id
                    == params.protected_area_id,
                )
                .exists()
            )
            filters.append(pa_exists)

        if params.in_protected_area is not None:
            pa_any = (
                self.db.query(FireProtectedAreaIntersection.id)
                .filter(FireProtectedAreaIntersection.fire_event_id == FireEvent.id)
                .exists()
            )
            filters.append(pa_any if params.in_protected_area else ~pa_any)

        start_dt, end_dt = self._date_filter_bounds(params.date_from, params.date_to)
        if start_dt:
            filters.append(FireEvent.start_date >= start_dt)
        if end_dt:
            filters.append(FireEvent.start_date <= end_dt)

        active_statuses = [
            FireStatus.ACTIVE.value,
            FireStatus.CONTROLLED.value,
            FireStatus.MONITORING.value,
        ]

        if params.status_scope and params.status_scope != StatusScope.ALL:
            now = datetime.now(timezone.utc)
            if params.status_scope == StatusScope.ACTIVE:
                filters.append(
                    or_(
                        FireEvent.status.in_(active_statuses),
                        and_(FireEvent.status.is_(None), FireEvent.end_date >= now),
                    )
                )
            elif params.status_scope == StatusScope.HISTORICAL:
                filters.append(
                    or_(
                        FireEvent.status == FireStatus.EXTINGUISHED.value,
                        and_(FireEvent.status.is_(None), FireEvent.end_date < now),
                    )
                )
        elif params.active_only:
            now = datetime.now(timezone.utc)
            filters.append(
                or_(
                    FireEvent.status.in_(active_statuses),
                    and_(FireEvent.status.is_(None), FireEvent.end_date >= now),
                )
            )

        if params.min_confidence is not None:
            filters.append(FireEvent.avg_confidence >= params.min_confidence)

        if params.min_detections is not None:
            filters.append(FireEvent.total_detections >= params.min_detections)

        if params.is_significant is not None:
            filters.append(FireEvent.is_significant == params.is_significant)

        if params.has_imagery is not None:
            imagery_exists = (
                self.db.query(SatelliteImage.id)
                .filter(SatelliteImage.fire_event_id == FireEvent.id)
                .exists()
            )
            filters.append(imagery_exists if params.has_imagery else ~imagery_exists)

        if params.search:
            term = f"%{params.search}%"
            protected_match = (
                self.db.query(FireProtectedAreaIntersection.id)
                .join(
                    ProtectedArea,
                    ProtectedArea.id == FireProtectedAreaIntersection.protected_area_id,
                )
                .filter(
                    FireProtectedAreaIntersection.fire_event_id == FireEvent.id,
                    ProtectedArea.official_name.ilike(term),
                )
                .exists()
            )
            filters.append(
                or_(
                    FireEvent.province.ilike(term),
                    FireEvent.department.ilike(term),
                    protected_match,
                )
            )

        if params.bbox:
            west, south, east, north = params.bbox
            envelope = func.ST_MakeEnvelope(west, south, east, north, 4326)
            filters.append(
                func.ST_Within(
                    func.cast(FireEvent.centroid, CENTROID_GEOMETRY), envelope
                )
            )

        return filters

    def _protected_area_subqueries(self):
        protected_area_name_subq = (
            self.db.query(ProtectedArea.official_name)
            .select_from(FireProtectedAreaIntersection)
            .join(
                ProtectedArea,
                ProtectedArea.id == FireProtectedAreaIntersection.protected_area_id,
            )
            .filter(FireProtectedAreaIntersection.fire_event_id == FireEvent.id)
            .limit(1)
            .scalar_subquery()
        )

        protected_area_id_subq = (
            self.db.query(FireProtectedAreaIntersection.protected_area_id)
            .filter(FireProtectedAreaIntersection.fire_event_id == FireEvent.id)
            .limit(1)
            .scalar_subquery()
        )

        overlap_percentage_subq = (
            self.db.query(func.max(FireProtectedAreaIntersection.overlap_percentage))
            .filter(FireProtectedAreaIntersection.fire_event_id == FireEvent.id)
            .scalar_subquery()
        )

        protected_area_count_subq = (
            self.db.query(func.count(FireProtectedAreaIntersection.id))
            .filter(FireProtectedAreaIntersection.fire_event_id == FireEvent.id)
            .scalar_subquery()
        )

        return (
            protected_area_name_subq,
            protected_area_id_subq,
            overlap_percentage_subq,
            protected_area_count_subq,
        )

    def build_list_query(self):
        imagery_exists = (
            self.db.query(SatelliteImage.id)
            .filter(SatelliteImage.fire_event_id == FireEvent.id)
            .exists()
        )

        (
            protected_area_name_subq,
            protected_area_id_subq,
            overlap_percentage_subq,
            protected_area_count_subq,
        ) = self._protected_area_subqueries()

        return self.db.query(
            FireEvent,
            func.ST_Y(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lat"),
            func.ST_X(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lon"),
            imagery_exists.label("has_imagery"),
            protected_area_name_subq.label("protected_area_name"),
            protected_area_id_subq.label("protected_area_id"),
            overlap_percentage_subq.label("overlap_percentage"),
            protected_area_count_subq.label("protected_area_count"),
        )

    def build_search_query(self):
        imagery_exists = (
            self.db.query(SatelliteImage.id)
            .filter(SatelliteImage.fire_event_id == FireEvent.id)
            .exists()
        )

        return self.db.query(
            FireEvent,
            func.ST_Y(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lat"),
            func.ST_X(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label("lon"),
            imagery_exists.label("has_imagery"),
        )

    def _build_search_items(self, rows) -> List[FireSearchItem]:
        results: List[FireSearchItem] = []
        for row in rows:
            fire, lat, lon, has_imagery = row
            avg_confidence = float(fire.avg_confidence) if fire.avg_confidence else None
            results.append(
                FireSearchItem(
                    id=fire.id,
                    start_date=fire.start_date,
                    end_date=fire.end_date,
                    province=fire.province,
                    department=fire.department,
                    estimated_area_hectares=float(fire.estimated_area_hectares)
                    if fire.estimated_area_hectares
                    else None,
                    avg_confidence=avg_confidence,
                    quality_score=avg_confidence,
                    total_detections=fire.total_detections or 0,
                    has_satellite_imagery=bool(has_imagery),
                    centroid={
                        "latitude": float(lat) if lat is not None else 0,
                        "longitude": float(lon) if lon is not None else 0,
                    },
                    status=self.resolve_fire_status(fire),
                )
            )
        return results

    @staticmethod
    def _add_months(target: date, months: int) -> date:
        new_month = target.month + months
        new_year = target.year + (new_month - 1) // 12
        new_month = ((new_month - 1) % 12) + 1
        day = min(target.day, calendar.monthrange(new_year, new_month)[1])
        return date(new_year, new_month, day)

    def _build_preview_timeline(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> ExplorationPreviewTimeline:
        if not start_date:
            return ExplorationPreviewTimeline(before=[], during=[], after=[])

        start = start_date.date()
        end = end_date.date() if end_date else None

        def _dedupe(values: List[date]) -> List[date]:
            seen = set()
            result = []
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                result.append(value)
            return result

        before = _dedupe(
            [
                self._add_months(start, -12),
                self._add_months(start, -6),
            ]
        )

        during = [start]
        if end and end != start:
            during.append(end)

        base_after = end or start
        after = _dedupe(
            [
                self._add_months(base_after, 3),
                self._add_months(base_after, 6),
                self._add_months(base_after, 12),
                self._add_months(base_after, 24),
            ]
        )

        return ExplorationPreviewTimeline(
            before=before,
            during=during,
            after=after,
        )

    def _build_list_items(self, rows) -> List[FireEventListItem]:
        results: List[FireEventListItem] = []
        for row in rows:
            (
                fire,
                lat,
                lon,
                has_imagery,
                pa_name,
                pa_id,
                overlap_percentage,
                protected_area_count,
            ) = row

            duration_hours = (
                (fire.end_date - fire.start_date).total_seconds() / 3600
                if fire.end_date and fire.start_date
                else 0
            )
            results.append(
                FireEventListItem(
                    id=fire.id,
                    start_date=fire.start_date,
                    end_date=fire.end_date,
                    duration_hours=duration_hours,
                    centroid={
                        "latitude": float(lat) if lat is not None else 0,
                        "longitude": float(lon) if lon is not None else 0,
                    },
                    province=fire.province,
                    department=fire.department,
                    total_detections=fire.total_detections or 0,
                    avg_confidence=float(fire.avg_confidence)
                    if fire.avg_confidence
                    else 0,
                    max_frp=float(fire.max_frp) if fire.max_frp else 0,
                    estimated_area_hectares=float(fire.estimated_area_hectares)
                    if fire.estimated_area_hectares
                    else 0,
                    is_significant=bool(fire.is_significant),
                    has_satellite_imagery=bool(has_imagery),
                    protected_area_name=pa_name,
                    in_protected_area=pa_id is not None,
                    overlap_percentage=float(overlap_percentage)
                    if overlap_percentage is not None
                    else None,
                    count_protected_areas=int(protected_area_count)
                    if protected_area_count
                    else 0,
                    status=self.resolve_fire_status(fire),
                    slides_data=fire.slides_data,
                )
            )
        return results

    def list_fires(
        self,
        *,
        params: FireFilterParams,
        page: int,
        page_size: Optional[int],
        sort_by: SortField,
        sort_desc: bool,
    ) -> FireListResponse:
        page_size = self.clamp_page_size(page_size)
        if page < 1:
            page = 1

        query = self.build_list_query()
        filters = self.build_filter_conditions(params)
        if filters:
            query = query.filter(*filters)

        total = query.with_entities(func.count(FireEvent.id)).scalar() or 0
        query = query.order_by(self.build_sort_clause(sort_by, sort_desc))
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        results = self._build_list_items(items)

        filters_applied = {
            k: v
            for k, v in {
                "province": params.province,
                "department": params.department,
                "protected_area_id": str(params.protected_area_id)
                if params.protected_area_id
                else None,
                "in_protected_area": params.in_protected_area,
                "date_from": params.date_from.isoformat() if params.date_from else None,
                "date_to": params.date_to.isoformat() if params.date_to else None,
                "active_only": params.active_only,
                "status_scope": params.status_scope.value
                if params.status_scope
                else None,
                "min_confidence": params.min_confidence,
                "min_detections": params.min_detections,
                "is_significant": params.is_significant,
                "has_imagery": params.has_imagery,
                "search": params.search,
                "sort_by": sort_by.value,
                "sort_desc": sort_desc,
            }.items()
            if v is not None
        }

        return FireListResponse(
            fires=results,
            pagination=PaginationMeta.create(total, page, page_size),
            filters_applied=filters_applied,
        )

    def search_fire_events(
        self,
        *,
        params: FireFilterParams,
        page: int,
        page_size: Optional[int],
    ) -> FireSearchResponse:
        page_size = self.clamp_page_size(page_size)
        if page < 1:
            page = 1

        query = self.build_search_query()
        filters = self.build_filter_conditions(params)
        if filters:
            query = query.filter(*filters)

        total = query.with_entities(func.count(FireEvent.id)).scalar() or 0
        items = (
            query.order_by(desc(FireEvent.start_date))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        results = self._build_search_items(items)

        filters_applied = {
            k: v
            for k, v in {
                "province": params.province,
                "department": params.department,
                "date_from": params.date_from.isoformat() if params.date_from else None,
                "date_to": params.date_to.isoformat() if params.date_to else None,
                "search": params.search,
                "bbox": params.bbox,
            }.items()
            if v is not None
        }

        return FireSearchResponse(
            fires=results,
            pagination=PaginationMeta.create(total, page, page_size),
            filters_applied=filters_applied,
        )

    def get_exploration_preview(
        self,
        fire_id: UUID,
    ) -> Optional[ExplorationPreviewResponse]:
        imagery_exists = (
            self.db.query(SatelliteImage.id)
            .filter(SatelliteImage.fire_event_id == FireEvent.id)
            .exists()
        )

        perimeter_geom = func.cast(FireEvent.perimeter, PERIMETER_GEOMETRY)

        row = (
            self.db.query(
                FireEvent,
                func.ST_Y(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label(
                    "lat"
                ),
                func.ST_X(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label(
                    "lon"
                ),
                func.ST_AsGeoJSON(perimeter_geom).label("perimeter_geojson"),
                func.ST_XMin(perimeter_geom).label("bbox_minx"),
                func.ST_YMin(perimeter_geom).label("bbox_miny"),
                func.ST_XMax(perimeter_geom).label("bbox_maxx"),
                func.ST_YMax(perimeter_geom).label("bbox_maxy"),
                imagery_exists.label("has_imagery"),
            )
            .filter(FireEvent.id == fire_id)
            .first()
        )

        if not row:
            return None

        (
            fire,
            lat,
            lon,
            perimeter_geojson,
            bbox_minx,
            bbox_miny,
            bbox_maxx,
            bbox_maxy,
            has_imagery,
        ) = row

        centroid = None
        if lat is not None and lon is not None:
            centroid = {"latitude": float(lat), "longitude": float(lon)}

        bbox = None
        if (
            bbox_minx is not None
            and bbox_miny is not None
            and bbox_maxx is not None
            and bbox_maxy is not None
        ):
            bbox = {
                "west": float(bbox_minx),
                "south": float(bbox_miny),
                "east": float(bbox_maxx),
                "north": float(bbox_maxy),
            }

        perimeter = None
        if perimeter_geojson:
            try:
                perimeter = json.loads(perimeter_geojson)
            except json.JSONDecodeError:
                perimeter = None

        duration_days = None
        if fire.start_date and fire.end_date:
            duration_days = (fire.end_date - fire.start_date).days

        timeline = self._build_preview_timeline(fire.start_date, fire.end_date)

        return ExplorationPreviewResponse(
            fire_event_id=fire.id,
            province=fire.province,
            department=fire.department,
            start_date=fire.start_date,
            end_date=fire.end_date,
            extinguished_at=fire.extinguished_at,
            centroid=centroid,
            bbox=bbox,
            perimeter_geojson=perimeter,
            estimated_area_hectares=float(fire.estimated_area_hectares)
            if fire.estimated_area_hectares
            else None,
            duration_days=duration_days,
            has_satellite_imagery=bool(has_imagery),
            timeline=timeline,
        )

    def list_active_with_thumbnails(self, limit: int) -> FireListResponse:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)
        active_statuses = [
            FireStatus.ACTIVE.value,
            FireStatus.CONTROLLED.value,
            FireStatus.MONITORING.value,
        ]

        active_filter = or_(
            FireEvent.status.in_(active_statuses),
            and_(FireEvent.status.is_(None), FireEvent.end_date >= now),
        )
        extinguished_filter = and_(
            or_(
                FireEvent.status == FireStatus.EXTINGUISHED.value,
                and_(FireEvent.status.is_(None), FireEvent.end_date < now),
            ),
            func.coalesce(FireEvent.extinguished_at, FireEvent.end_date) >= cutoff,
        )

        query = self.build_list_query().filter(or_(active_filter, extinguished_filter))
        query = query.filter(
            FireEvent.slides_data.isnot(None),
            func.jsonb_array_length(FireEvent.slides_data) > 0,
        )

        total = query.with_entities(func.count(FireEvent.id)).scalar() or 0
        items = query.order_by(desc(FireEvent.start_date)).limit(limit).all()
        results = self._build_list_items(items)

        return FireListResponse(
            fires=results,
            pagination=PaginationMeta.create(total, 1, limit),
            filters_applied={
                "status_scope": "active+recent_extinguished",
                "extinguished_days": 30,
                "has_thumbnails": True,
            },
        )

    def get_fire_detail(self, fire_id: UUID) -> Optional[FireDetailResponse]:
        imagery_exists = (
            self.db.query(SatelliteImage.id)
            .filter(SatelliteImage.fire_event_id == FireEvent.id)
            .exists()
        )

        row = (
            self.db.query(
                FireEvent,
                func.ST_Y(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label(
                    "lat"
                ),
                func.ST_X(func.cast(FireEvent.centroid, CENTROID_GEOMETRY)).label(
                    "lon"
                ),
                imagery_exists.label("has_imagery"),
            )
            .filter(FireEvent.id == fire_id)
            .first()
        )

        if not row:
            return None

        fire, lat, lon, has_imagery = row
        duration_hours = (
            (fire.end_date - fire.start_date).total_seconds() / 3600
            if fire.end_date and fire.start_date
            else 0
        )

        centroid = None
        if lat is not None and lon is not None:
            centroid = {"latitude": float(lat), "longitude": float(lon)}

        protected_areas: List[ProtectedAreaBrief] = []
        overlap_values: List[float] = []

        for intersection in fire.protected_area_intersections or []:
            area = intersection.protected_area
            if area:
                protected_areas.append(
                    ProtectedAreaBrief(
                        id=area.id,
                        name=area.official_name,
                        category=area.category,
                        prohibition_until=intersection.prohibition_until,
                    )
                )
            if intersection.overlap_percentage is not None:
                overlap_values.append(float(intersection.overlap_percentage))

        overlap_percentage = max(overlap_values) if overlap_values else None
        protected_area_name = protected_areas[0].name if protected_areas else None
        count_protected_areas = len(protected_areas)

        detections = (
            self.db.query(FireDetection)
            .filter(FireDetection.fire_event_id == fire.id)
            .order_by(FireDetection.detected_at.desc())
            .limit(500)
            .all()
        )

        detection_briefs = [
            DetectionBrief(
                id=detection.id,
                satellite=detection.satellite,
                detected_at=detection.detected_at,
                latitude=float(detection.latitude),
                longitude=float(detection.longitude),
                frp=float(detection.fire_radiative_power)
                if detection.fire_radiative_power is not None
                else None,
                confidence=detection.confidence_normalized,
            )
            for detection in detections
        ]

        has_climate_data = False
        try:
            climate_row = self.db.execute(
                text(
                    "SELECT 1 FROM fire_climate_associations "
                    "WHERE fire_event_id = :fire_event_id LIMIT 1"
                ),
                {"fire_event_id": str(fire.id)},
            ).first()
            has_climate_data = climate_row is not None
        except SQLAlchemyError as exc:
            logger.warning("fire_climate_associations lookup failed: %s", exc)
            self.db.rollback()

        detail = FireEventDetail(
            id=fire.id,
            start_date=fire.start_date,
            end_date=fire.end_date,
            duration_hours=duration_hours,
            centroid=centroid,
            province=fire.province,
            department=fire.department,
            total_detections=fire.total_detections or 0,
            avg_confidence=float(fire.avg_confidence) if fire.avg_confidence else None,
            max_frp=float(fire.max_frp) if fire.max_frp else None,
            estimated_area_hectares=float(fire.estimated_area_hectares)
            if fire.estimated_area_hectares
            else None,
            is_significant=bool(fire.is_significant),
            has_satellite_imagery=bool(has_imagery),
            has_climate_data=has_climate_data,
            protected_area_name=protected_area_name,
            in_protected_area=count_protected_areas > 0,
            overlap_percentage=overlap_percentage,
            count_protected_areas=count_protected_areas,
            status=self.resolve_fire_status(fire),
            slides_data=fire.slides_data,
            avg_frp=float(fire.avg_frp) if fire.avg_frp else None,
            sum_frp=float(fire.sum_frp) if fire.sum_frp else None,
            has_legal_analysis=bool(fire.has_legal_analysis),
            processing_error=fire.processing_error,
            protected_areas=protected_areas,
            created_at=fire.created_at,
            updated_at=fire.updated_at,
        )

        return FireDetailResponse(
            fire=detail,
            detections=detection_briefs,
            related_fires_count=0,
        )

    def get_fire_detail_by_episode(self, episode_id: UUID) -> Optional[FireDetailResponse]:
        representative_event = (
            self.db.query(FireEvent.id)
            .join(FireEpisodeEvent, FireEpisodeEvent.event_id == FireEvent.id)
            .filter(FireEpisodeEvent.episode_id == episode_id)
            .order_by(
                case(
                    (
                        FireEvent.status.in_(
                            [FireStatus.ACTIVE.value, FireStatus.MONITORING.value]
                        ),
                        0,
                    ),
                    else_=1,
                ),
                desc(FireEvent.end_date),
                desc(FireEvent.start_date),
            )
            .first()
        )

        if not representative_event:
            return None

        return self.get_fire_detail(representative_event.id)

    def _summary_query(self, filters: List[Any]):
        now = datetime.now(timezone.utc)
        active_statuses = [
            FireStatus.ACTIVE.value,
            FireStatus.CONTROLLED.value,
            FireStatus.MONITORING.value,
        ]

        return (
            self.db.query(
                func.count(FireEvent.id).label("total_fires"),
                func.coalesce(func.sum(FireEvent.total_detections), 0).label(
                    "total_detections"
                ),
                func.coalesce(func.sum(FireEvent.estimated_area_hectares), 0).label(
                    "total_hectares"
                ),
                func.coalesce(func.avg(FireEvent.avg_confidence), 0).label(
                    "avg_confidence"
                ),
                func.coalesce(func.avg(FireEvent.estimated_area_hectares), 0).label(
                    "avg_hectares"
                ),
                func.coalesce(
                    func.sum(case((FireEvent.is_significant.is_(True), 1), else_=0)),
                    0,
                ).label("significant_fires"),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                or_(
                                    FireEvent.status.in_(active_statuses),
                                    and_(
                                        FireEvent.status.is_(None),
                                        FireEvent.end_date >= now,
                                    ),
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("active_fires"),
            )
            .filter(*filters)
            .one()
        )

    def _metric_comparison(self, current: float, previous: float) -> MetricComparison:
        delta = current - previous
        delta_pct = (delta / previous * 100) if previous else None
        return MetricComparison(
            current=float(current),
            previous=float(previous),
            delta=float(delta),
            delta_pct=float(delta_pct) if delta_pct is not None else None,
        )

    def _safe_previous_date(self, target: date) -> date:
        try:
            return date(target.year - 1, target.month, target.day)
        except ValueError:
            if target.month == 2 and target.day == 29:
                return date(target.year - 1, 2, 28)
            return date(target.year - 1, target.month, 1)

    def _kpi_snapshot(
        self,
        base_filters: List[Any],
        date_from: date,
        date_to: date,
    ):
        start_dt, end_dt = self._date_filter_bounds(date_from, date_to)
        filters = list(base_filters)
        if start_dt:
            filters.append(FireEvent.start_date >= start_dt)
        if end_dt:
            filters.append(FireEvent.start_date <= end_dt)

        summary = (
            self.db.query(
                func.count(FireEvent.id).label("total_fires"),
                func.coalesce(func.sum(FireEvent.total_detections), 0).label(
                    "total_detections"
                ),
                func.coalesce(func.sum(FireEvent.estimated_area_hectares), 0).label(
                    "total_hectares"
                ),
                func.coalesce(func.avg(FireEvent.avg_confidence), 0).label(
                    "avg_confidence"
                ),
                func.coalesce(
                    func.sum(case((FireEvent.is_significant.is_(True), 1), else_=0)),
                    0,
                ).label("significant_fires"),
            )
            .filter(*filters)
            .one()
        )
        return summary

    def get_stats(self, *, params: FireFilterParams) -> StatsResponse:
        filters = self.build_filter_conditions(params)

        summary = self._summary_query(filters)

        median_hectares = (
            self.db.query(
                func.percentile_cont(0.5).within_group(
                    FireEvent.estimated_area_hectares
                )
            )
            .filter(*filters, FireEvent.estimated_area_hectares.isnot(None))
            .scalar()
            or 0
        )

        by_province_rows = (
            self.db.query(
                FireEvent.province.label("province"),
                func.count(FireEvent.id).label("fire_count"),
                func.max(FireEvent.start_date).label("latest_fire"),
            )
            .filter(*filters)
            .group_by(FireEvent.province)
            .all()
        )

        by_month_rows = (
            self.db.query(
                func.date_trunc("month", FireEvent.start_date).label("month"),
                func.count(FireEvent.id).label("fire_count"),
            )
            .filter(*filters)
            .group_by(func.date_trunc("month", FireEvent.start_date))
            .order_by(func.date_trunc("month", FireEvent.start_date))
            .all()
        )

        fires_in_protected = (
            self.db.query(
                func.count(func.distinct(FireProtectedAreaIntersection.fire_event_id))
            )
            .join(
                FireEvent,
                FireEvent.id == FireProtectedAreaIntersection.fire_event_id,
            )
            .filter(*filters)
            .scalar()
            or 0
        )

        top_frp_rows = (
            self.db.query(
                FireEvent.id,
                FireEvent.max_frp,
                FireEvent.province,
                FireEvent.start_date,
            )
            .filter(*filters, FireEvent.max_frp.isnot(None))
            .order_by(desc(FireEvent.max_frp).nullslast())
            .limit(10)
            .all()
        )

        by_province = [
            ProvinceStats(
                name=row.province or "Unknown",
                fire_count=row.fire_count,
                latest_fire=row.latest_fire.date() if row.latest_fire else None,
            )
            for row in by_province_rows
        ]

        by_month = {
            row.month.strftime("%Y-%m"): row.fire_count
            for row in by_month_rows
            if row.month
        }

        total_fires = summary.total_fires or 0
        active_fires = summary.active_fires or 0
        historical_fires = max(total_fires - active_fires, 0)
        protected_percentage = (
            (fires_in_protected / total_fires * 100) if total_fires else 0
        )
        significant_fires = summary.significant_fires or 0
        significant_percentage = (
            (significant_fires / total_fires * 100) if total_fires else 0
        )

        period_from = params.date_from or date.today()
        period_to = params.date_to or date.today()

        stats = FireStatistics(
            total_fires=total_fires,
            active_fires=active_fires,
            historical_fires=historical_fires,
            total_detections=summary.total_detections,
            total_hectares=float(summary.total_hectares or 0),
            avg_hectares=float(summary.avg_hectares or 0),
            median_hectares=float(median_hectares or 0),
            avg_confidence=float(summary.avg_confidence or 0),
            fires_in_protected=fires_in_protected,
            protected_percentage=float(protected_percentage),
            significant_fires=significant_fires,
            significant_percentage=float(significant_percentage),
            top_frp_fires=[
                TopFrpFire(
                    id=row.id,
                    max_frp=float(row.max_frp) if row.max_frp is not None else None,
                    province=row.province,
                    start_date=row.start_date,
                )
                for row in top_frp_rows
            ],
            by_province=by_province,
            by_month=by_month,
        )

        ytd_end = params.date_to or date.today()
        ytd_start = date(ytd_end.year, 1, 1)
        prev_end = self._safe_previous_date(ytd_end)
        prev_start = date(prev_end.year, 1, 1)

        base_filters = self.build_filter_conditions(
            FireFilterParams(
                province=params.province,
                department=params.department,
                protected_area_id=params.protected_area_id,
                in_protected_area=params.in_protected_area,
                active_only=params.active_only,
                status_scope=params.status_scope,
                min_confidence=params.min_confidence,
                min_detections=params.min_detections,
                is_significant=params.is_significant,
                has_imagery=params.has_imagery,
                search=params.search,
            )
        )

        current = self._kpi_snapshot(base_filters, ytd_start, ytd_end)
        previous = self._kpi_snapshot(base_filters, prev_start, prev_end)

        ytd = YtdComparison(
            total_fires=self._metric_comparison(
                current.total_fires or 0, previous.total_fires or 0
            ),
            total_hectares=self._metric_comparison(
                float(current.total_hectares or 0), float(previous.total_hectares or 0)
            ),
            total_detections=self._metric_comparison(
                current.total_detections or 0, previous.total_detections or 0
            ),
            avg_confidence=self._metric_comparison(
                float(current.avg_confidence or 0), float(previous.avg_confidence or 0)
            ),
            significant_fires=self._metric_comparison(
                current.significant_fires or 0, previous.significant_fires or 0
            ),
        )

        return StatsResponse(
            period={"from": period_from, "to": period_to},
            stats=stats,
            ytd_comparison=ytd,
        )

    def list_provinces(self) -> List[dict]:
        rows = (
            self.db.query(
                FireEvent.province.label("province"),
                func.count(FireEvent.id).label("fire_count"),
                func.max(FireEvent.start_date).label("latest_fire"),
            )
            .group_by(FireEvent.province)
            .order_by(FireEvent.province.asc().nulls_last())
            .all()
        )

        results: List[dict] = []
        for row in rows:
            latest = row.latest_fire.date() if row.latest_fire else None
            results.append(
                {
                    "name": row.province or "Unknown",
                    "fire_count": int(row.fire_count or 0),
                    "latest_fire": latest,
                }
            )
        return results

    def list_saved_filters(self, user_id: UUID) -> List[SavedFilterResponse]:
        rows = (
            self.db.execute(
                text(
                    """
                    SELECT id, filter_name, filter_config, is_default,
                           created_at, last_used_at, use_count
                      FROM user_saved_filters
                     WHERE user_id = :user_id
                  ORDER BY is_default DESC,
                           last_used_at DESC NULLS LAST,
                           created_at DESC
                    """
                ),
                {"user_id": str(user_id)},
            )
            .mappings()
            .all()
        )
        return [SavedFilterResponse(**row) for row in rows]

    def upsert_saved_filter(
        self, user_id: UUID, payload: SavedFilterCreate
    ) -> SavedFilterResponse:
        if payload.is_default:
            self.db.execute(
                text(
                    "UPDATE user_saved_filters SET is_default = false "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": str(user_id)},
            )

        row = (
            self.db.execute(
                text(
                    """
                    INSERT INTO user_saved_filters (
                        user_id, filter_name, filter_config, is_default
                    )
                    VALUES (
                        :user_id, :filter_name, :filter_config::jsonb, :is_default
                    )
                    ON CONFLICT (user_id, filter_name)
                    DO UPDATE SET
                        filter_config = EXCLUDED.filter_config,
                        is_default = EXCLUDED.is_default
                    RETURNING id, filter_name, filter_config, is_default,
                              created_at, last_used_at, use_count
                    """
                ),
                {
                    "user_id": str(user_id),
                    "filter_name": payload.filter_name,
                    "filter_config": json.dumps(payload.filter_config or {}),
                    "is_default": payload.is_default,
                },
            )
            .mappings()
            .one()
        )

        self.db.commit()
        return SavedFilterResponse(**row)

    def delete_saved_filter(self, user_id: UUID, filter_id: UUID) -> bool:
        result = self.db.execute(
            text(
                "DELETE FROM user_saved_filters "
                "WHERE id = :filter_id AND user_id = :user_id"
            ),
            {"filter_id": str(filter_id), "user_id": str(user_id)},
        )
        self.db.commit()
        return result.rowcount > 0
