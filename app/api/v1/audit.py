"""
=============================================================================
FORESTGUARD API - LAND USE AUDIT ENDPOINTS (UC-01)
=============================================================================

Legal land-use verification under Argentina's Forest Law (Ley 26.815 Art. 22 bis).

Use Case (UC-01): Auditoría de Uso de Suelo
    Verifies if a parcel of land has legal restrictions due to previous
    wildfire events. Restrictions apply for 60 years post-fire when land
    was in a protected area or suffered significant damage.

Endpoints:
    POST /audit/land-use - Check legal restrictions for coordinates
    GET /audit/geocode - Geocode an address to coordinates

Authentication:
    All endpoints require API key authentication.

Legal Framework:
    - Ley 26.815 Art. 22 bis (Argentina)
    - 60-year restriction period for affected lands
    - Applies to land-use change, construction permits, subdivisions

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import unicodedata
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.core.rate_limiter import check_rate_limit
from app.core.security import verify_api_key
from app.schemas.audit import (
    AuditRequest,
    AuditResponse,
    AuditSearchBBox,
    AuditSearchDateRange,
    AuditSearchEpisode,
    AuditSearchResolvedPlace,
    AuditSearchResponse,
)
from app.schemas.geocode import GeocodeResponse
from app.services.audit_service import AuditService
from app.services.geocoding_service import GeocodingService

router = APIRouter()


def get_audit_service(db: Session = Depends(deps.get_db)) -> AuditService:
    return AuditService(db)


def get_geocoding_service() -> GeocodingService:
    return GeocodingService()


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return normalized.lower().strip()


def _load_province_lookup(db: Session) -> Dict[str, str]:
    provinces = set()
    rows = db.execute(
        text(
            "SELECT DISTINCT province FROM fire_events WHERE province IS NOT NULL"
        )
    ).fetchall()
    provinces.update({row[0] for row in rows if row[0]})

    episode_rows = db.execute(
        text(
            """
            SELECT DISTINCT unnest(provinces) AS province
              FROM fire_episodes
             WHERE provinces IS NOT NULL
            """
        )
    ).fetchall()
    provinces.update({row[0] for row in episode_rows if row[0]})

    return {_normalize_text(name): name for name in provinces}


def _fetch_episodes_by_province(
    db: Session, province: str, limit: int
) -> tuple[list[dict], dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT id,
                       start_date,
                       end_date,
                       status,
                       provinces,
                       estimated_area_hectares,
                       detection_count,
                       frp_max
                  FROM fire_episodes
                 WHERE :province = ANY(provinces)
                 ORDER BY end_date DESC NULLS LAST, start_date DESC NULLS LAST
                 LIMIT :limit
                """
            ),
            {"province": province, "limit": limit},
        )
        .mappings()
        .all()
    )

    stats = db.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   MIN(start_date) AS earliest,
                   COALESCE(MAX(end_date), MAX(start_date)) AS latest
              FROM fire_episodes
             WHERE :province = ANY(provinces)
            """
        ),
        {"province": province},
    ).mappings().first()

    return [dict(row) for row in rows], dict(stats or {})


def _fetch_episodes_by_protected_area(
    db: Session, area_id: str, limit: int
) -> tuple[list[dict], dict]:
    rows = (
        db.execute(
            text(
                """
                WITH area AS (
                    SELECT COALESCE(simplified_boundary, boundary)::geometry AS geom
                      FROM protected_areas
                     WHERE id = :area_id
                )
                SELECT fe.id,
                       fe.start_date,
                       fe.end_date,
                       fe.status,
                       fe.provinces,
                       fe.estimated_area_hectares,
                       fe.detection_count,
                       fe.frp_max
                  FROM fire_episodes fe, area
                 WHERE fe.bbox_minx IS NOT NULL
                   AND fe.bbox_miny IS NOT NULL
                   AND fe.bbox_maxx IS NOT NULL
                   AND fe.bbox_maxy IS NOT NULL
                   AND ST_Intersects(
                       ST_MakeEnvelope(fe.bbox_minx, fe.bbox_miny, fe.bbox_maxx, fe.bbox_maxy, 4326),
                       area.geom
                   )
                 ORDER BY fe.end_date DESC NULLS LAST, fe.start_date DESC NULLS LAST
                 LIMIT :limit
                """
            ),
            {"area_id": area_id, "limit": limit},
        )
        .mappings()
        .all()
    )

    stats = db.execute(
        text(
            """
            WITH area AS (
                SELECT COALESCE(simplified_boundary, boundary)::geometry AS geom
                  FROM protected_areas
                 WHERE id = :area_id
            )
            SELECT COUNT(*) AS total,
                   MIN(fe.start_date) AS earliest,
                   COALESCE(MAX(fe.end_date), MAX(fe.start_date)) AS latest
              FROM fire_episodes fe, area
             WHERE fe.bbox_minx IS NOT NULL
               AND fe.bbox_miny IS NOT NULL
               AND fe.bbox_maxx IS NOT NULL
               AND fe.bbox_maxy IS NOT NULL
               AND ST_Intersects(
                   ST_MakeEnvelope(fe.bbox_minx, fe.bbox_miny, fe.bbox_maxx, fe.bbox_maxy, 4326),
                   area.geom
               )
            """
        ),
        {"area_id": area_id},
    ).mappings().first()

    return [dict(row) for row in rows], dict(stats or {})


def _fetch_episodes_by_point(
    db: Session, lat: float, lon: float, radius_km: float, limit: int
) -> tuple[list[dict], dict]:
    radius_m = max(radius_km, 0.1) * 1000
    rows = (
        db.execute(
            text(
                """
                SELECT id,
                       start_date,
                       end_date,
                       status,
                       provinces,
                       estimated_area_hectares,
                       detection_count,
                       frp_max
                  FROM fire_episodes
                 WHERE centroid_lat IS NOT NULL
                   AND centroid_lon IS NOT NULL
                   AND ST_DWithin(
                       ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)::geography,
                       ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                       :radius_m
                   )
                 ORDER BY end_date DESC NULLS LAST, start_date DESC NULLS LAST
                 LIMIT :limit
                """
            ),
            {"lat": lat, "lon": lon, "radius_m": radius_m, "limit": limit},
        )
        .mappings()
        .all()
    )

    stats = db.execute(
        text(
            """
            SELECT COUNT(*) AS total,
                   MIN(start_date) AS earliest,
                   COALESCE(MAX(end_date), MAX(start_date)) AS latest
              FROM fire_episodes
             WHERE centroid_lat IS NOT NULL
               AND centroid_lon IS NOT NULL
               AND ST_DWithin(
                   ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                   :radius_m
               )
            """
        ),
        {"lat": lat, "lon": lon, "radius_m": radius_m},
    ).mappings().first()

    return [dict(row) for row in rows], dict(stats or {})


def _build_episode_items(rows: list[dict]) -> list[AuditSearchEpisode]:
    items: list[AuditSearchEpisode] = []
    for row in rows:
        items.append(
            AuditSearchEpisode(
                id=row["id"],
                start_date=row["start_date"],
                end_date=row.get("end_date"),
                status=row.get("status"),
                provinces=row.get("provinces"),
                estimated_area_hectares=float(row["estimated_area_hectares"])
                if row.get("estimated_area_hectares") is not None
                else None,
                detection_count=int(row["detection_count"])
                if row.get("detection_count") is not None
                else None,
                frp_max=float(row["frp_max"])
                if row.get("frp_max") is not None
                else None,
            )
        )
    return items


@router.post(
    "/land-use",
    response_model=AuditResponse,
    summary="Legal land-use audit (UC-F06)",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
def audit_land_use(
    payload: AuditRequest,
    request: Request,
    service: AuditService = Depends(get_audit_service),
) -> AuditResponse:
    try:
        user_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        return service.run_audit(
            lat=payload.lat,
            lon=payload.lon,
            radius_meters=payload.radius_meters,
            cadastral_id=payload.cadastral_id,
            user_ip=user_ip,
            user_agent=user_agent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocodificar una ubicaciÃ³n (audit)",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
def geocode_location(
    q: str = Query(
        ..., min_length=3, max_length=120, description="Texto a geocodificar"
    ),
    service: GeocodingService = Depends(get_geocoding_service),
) -> GeocodeResponse:
    result = service.geocode(q.strip())
    if not result:
        raise HTTPException(
            status_code=404, detail="No se encontraron resultados"
        )
    return GeocodeResponse(query=q, result=result)


@router.get(
    "/search",
    response_model=AuditSearchResponse,
    summary="Buscar episodios histÃ³ricos por lugar",
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
def audit_search(
    q: str = Query(..., min_length=2, max_length=120),
    limit: int = Query(20, ge=1, le=100),
    radius_km: float = Query(10, ge=1, le=200),
    db: Session = Depends(deps.get_db),
    geocoding: GeocodingService = Depends(get_geocoding_service),
) -> AuditSearchResponse:
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="q is required")

    normalized = _normalize_text(query)
    province_lookup = _load_province_lookup(db)
    province = province_lookup.get(normalized)

    resolved_place: Optional[AuditSearchResolvedPlace] = None
    rows: list[dict] = []
    stats: dict = {}

    if province:
        rows, stats = _fetch_episodes_by_province(db, province, limit)
        resolved_place = AuditSearchResolvedPlace(
            label=province, type="province"
        )
    else:
        protected_area = (
            db.execute(
                text(
                    """
                    SELECT id,
                           official_name,
                           ST_Y(ST_Centroid(COALESCE(simplified_boundary, boundary))::geometry) AS lat,
                           ST_X(ST_Centroid(COALESCE(simplified_boundary, boundary))::geometry) AS lon,
                           ST_XMin(COALESCE(simplified_boundary, boundary)::geometry) AS minx,
                           ST_YMin(COALESCE(simplified_boundary, boundary)::geometry) AS miny,
                           ST_XMax(COALESCE(simplified_boundary, boundary)::geometry) AS maxx,
                           ST_YMax(COALESCE(simplified_boundary, boundary)::geometry) AS maxy
                      FROM protected_areas
                     WHERE official_name ILIKE :term
                        OR :query = ANY(alternative_names)
                     ORDER BY official_name ASC
                     LIMIT 1
                    """
                ),
                {"term": f"%{query}%", "query": query},
            )
            .mappings()
            .first()
        )

        if protected_area:
            rows, stats = _fetch_episodes_by_protected_area(
                db, str(protected_area["id"]), limit
            )
            resolved_place = AuditSearchResolvedPlace(
                label=protected_area["official_name"],
                type="protected_area",
                bbox=AuditSearchBBox(
                    minx=float(protected_area["minx"]),
                    miny=float(protected_area["miny"]),
                    maxx=float(protected_area["maxx"]),
                    maxy=float(protected_area["maxy"]),
                )
                if protected_area.get("minx") is not None
                else None,
                point={
                    "lat": float(protected_area["lat"]),
                    "lon": float(protected_area["lon"]),
                }
                if protected_area.get("lat") is not None
                else None,
            )
        else:
            geocode_result = geocoding.geocode(query)
            if not geocode_result:
                raise HTTPException(
                    status_code=404, detail="No se encontraron resultados"
                )

            rows, stats = _fetch_episodes_by_point(
                db,
                geocode_result.lat,
                geocode_result.lon,
                radius_km,
                limit,
            )

            bbox = None
            if geocode_result.boundingbox and len(geocode_result.boundingbox) == 4:
                south, north, west, east = geocode_result.boundingbox
                try:
                    bbox = AuditSearchBBox(
                        minx=float(west),
                        miny=float(south),
                        maxx=float(east),
                        maxy=float(north),
                    )
                except (TypeError, ValueError):
                    bbox = None

            resolved_place = AuditSearchResolvedPlace(
                label=geocode_result.display_name,
                type="address",
                bbox=bbox,
                point={"lat": geocode_result.lat, "lon": geocode_result.lon},
            )

    episodes = _build_episode_items(rows)
    date_range = AuditSearchDateRange(
        earliest=stats.get("earliest"), latest=stats.get("latest")
    )

    return AuditSearchResponse(
        resolved_place=resolved_place,
        episodes=episodes,
        total=int(stats.get("total") or 0),
        date_range=date_range,
    )
