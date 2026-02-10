import math
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, text
from sqlalchemy.orm import Session

from app.api import deps
from app.models.episode import FireEpisode, FireEpisodeEvent
from app.models.fire import FireEvent
from app.schemas.episode import (
    EpisodeBBox,
    FireEpisodeDetail,
    FireEpisodeEventItem,
    FireEpisodeListItem,
    FireEpisodeListResponse,
)

router = APIRouter()


def build_bbox(episode: FireEpisode) -> Optional[EpisodeBBox]:
    if (
        episode.bbox_minx is None
        or episode.bbox_miny is None
        or episode.bbox_maxx is None
        or episode.bbox_maxy is None
    ):
        return None
    return EpisodeBBox(
        minx=float(episode.bbox_minx),
        miny=float(episode.bbox_miny),
        maxx=float(episode.bbox_maxx),
        maxy=float(episode.bbox_maxy),
    )


def build_bbox_from_row(row) -> Optional[EpisodeBBox]:
    if (
        row.get("bbox_minx") is None
        or row.get("bbox_miny") is None
        or row.get("bbox_maxx") is None
        or row.get("bbox_maxy") is None
    ):
        return None
    return EpisodeBBox(
        minx=float(row["bbox_minx"]),
        miny=float(row["bbox_miny"]),
        maxx=float(row["bbox_maxx"]),
        maxy=float(row["bbox_maxy"]),
    )


def resolve_representative_event_id(events: List[FireEvent]) -> Optional[UUID]:
    if not events:
        return None

    def sort_key(event: FireEvent):
        status = (event.status or "").lower()
        priority = 0 if status in ("active", "monitoring") else 1
        end_date = event.end_date or event.start_date
        return (priority, end_date or event.start_date)

    return sorted(events, key=sort_key, reverse=True)[0].id


@router.get(
    "/",
    response_model=FireEpisodeListResponse,
    summary="Listar episodios de incendios (UC-17)",
)
def list_fire_episodes(
    gee_candidate: Optional[bool] = Query(
        None, description="Filtrar candidatos para GEE"
    ),
    status: Optional[str] = Query(
        None,
        description="Filtrar por estado (active/monitoring/extinct/closed)",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("gee_priority"),
    sort_desc: bool = Query(True),
    db: Session = Depends(deps.get_db),
) -> FireEpisodeListResponse:
    query = db.query(FireEpisode)

    if gee_candidate is not None:
        query = query.filter(FireEpisode.gee_candidate == gee_candidate)
    if status:
        query = query.filter(FireEpisode.status == status)

    total = query.count()

    sort_map = {
        "gee_priority": FireEpisode.gee_priority,
        "start_date": FireEpisode.start_date,
        "end_date": FireEpisode.end_date,
        "frp_sum": FireEpisode.frp_sum,
        "frp_max": FireEpisode.frp_max,
        "detections": FireEpisode.detection_count,
        "events": FireEpisode.event_count,
    }
    sort_field = sort_map.get(sort_by, FireEpisode.gee_priority)
    query = query.order_by(desc(sort_field) if sort_desc else asc(sort_field))

    episodes = query.offset((page - 1) * page_size).limit(page_size).all()

    items: List[FireEpisodeListItem] = []
    for episode in episodes:
        items.append(
            FireEpisodeListItem(
                id=episode.id,
                status=episode.status or "active",
                start_date=episode.start_date,
                end_date=episode.end_date,
                last_seen_at=episode.last_seen_at,
                bbox=build_bbox(episode),
                provinces=episode.provinces,
                event_count=episode.event_count or 0,
                detection_count=episode.detection_count or 0,
                frp_sum=float(episode.frp_sum)
                if episode.frp_sum is not None
                else None,
                frp_max=float(episode.frp_max)
                if episode.frp_max is not None
                else None,
                estimated_area_hectares=float(episode.estimated_area_hectares)
                if episode.estimated_area_hectares is not None
                else None,
                gee_candidate=bool(episode.gee_candidate),
                gee_priority=episode.gee_priority,
                slides_data=episode.slides_data,
                representative_event_id=None,
            )
        )

    total_pages = math.ceil(total / page_size) if page_size else 1

    return FireEpisodeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        episodes=items,
    )


@router.get(
    "/active",
    response_model=FireEpisodeListResponse,
    summary="Episodios para Home con thumbnails",
)
def list_active_episodes_for_home(
    limit: int = Query(
        20, ge=1, le=50, description="Maximo de episodios para Home"
    ),
    db: Session = Depends(deps.get_db),
) -> FireEpisodeListResponse:
    rows = (
        db.execute(
            text(
                """
                SELECT fe.id,
                       fe.status,
                       fe.start_date,
                       fe.end_date,
                       fe.last_seen_at,
                       fe.bbox_minx,
                       fe.bbox_miny,
                       fe.bbox_maxx,
                       fe.bbox_maxy,
                       fe.provinces,
                       fe.event_count,
                       fe.detection_count,
                       fe.frp_sum,
                       fe.frp_max,
                       fe.estimated_area_hectares,
                       fe.gee_candidate,
                       fe.gee_priority,
                       fe.slides_data,
                       rep.event_id AS representative_event_id
                  FROM fire_episodes fe
                  LEFT JOIN LATERAL (
                        SELECT ev.id AS event_id
                          FROM fire_episode_events fee
                          JOIN fire_events ev ON ev.id = fee.event_id
                         WHERE fee.episode_id = fe.id
                         ORDER BY CASE WHEN ev.status IN ('active', 'monitoring') THEN 0 ELSE 1 END,
                                  ev.end_date DESC NULLS LAST,
                                  ev.start_date DESC NULLS LAST
                         LIMIT 1
                  ) rep ON TRUE
                 WHERE fe.status IN ('active', 'monitoring')
                   AND fe.gee_candidate = true
                   AND fe.slides_data IS NOT NULL
                   AND jsonb_array_length(fe.slides_data) > 0
                 ORDER BY fe.gee_priority DESC NULLS LAST, fe.start_date DESC NULLS LAST
                 LIMIT :limit
                """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    items: List[FireEpisodeListItem] = []
    for row in rows:
        items.append(
            FireEpisodeListItem(
                id=row["id"],
                status=row.get("status") or "active",
                start_date=row.get("start_date"),
                end_date=row.get("end_date"),
                last_seen_at=row.get("last_seen_at"),
                bbox=build_bbox_from_row(row),
                provinces=row.get("provinces"),
                event_count=int(row.get("event_count") or 0),
                detection_count=int(row.get("detection_count") or 0),
                frp_sum=float(row["frp_sum"])
                if row.get("frp_sum") is not None
                else None,
                frp_max=float(row["frp_max"])
                if row.get("frp_max") is not None
                else None,
                estimated_area_hectares=float(row["estimated_area_hectares"])
                if row.get("estimated_area_hectares") is not None
                else None,
                gee_candidate=bool(row.get("gee_candidate")),
                gee_priority=row.get("gee_priority"),
                slides_data=row.get("slides_data"),
                representative_event_id=row.get("representative_event_id"),
            )
        )

    total = len(items)
    page = 1
    page_size = limit
    total_pages = 1

    return FireEpisodeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        episodes=items,
    )


@router.get(
    "/{episode_id}",
    response_model=FireEpisodeDetail,
    summary="Detalle de episodio de incendios",
)
def get_fire_episode(
    episode_id: UUID,
    db: Session = Depends(deps.get_db),
) -> FireEpisodeDetail:
    episode = (
        db.query(FireEpisode).filter(FireEpisode.id == episode_id).first()
    )
    if not episode:
        raise HTTPException(status_code=404, detail="Episodio no encontrado")

    event_rows = (
        db.query(FireEvent)
        .join(FireEpisodeEvent, FireEpisodeEvent.event_id == FireEvent.id)
        .filter(FireEpisodeEvent.episode_id == episode_id)
        .all()
    )

    events = [
        FireEpisodeEventItem(
            id=event.id,
            start_date=event.start_date,
            end_date=event.end_date,
            province=event.province,
            total_detections=event.total_detections,
            max_frp=float(event.max_frp)
            if event.max_frp is not None
            else None,
            estimated_area_hectares=float(event.estimated_area_hectares)
            if event.estimated_area_hectares is not None
            else None,
        )
        for event in event_rows
    ]

    return FireEpisodeDetail(
        id=episode.id,
        status=episode.status or "active",
        start_date=episode.start_date,
        end_date=episode.end_date,
        last_seen_at=episode.last_seen_at,
        bbox=build_bbox(episode),
        provinces=episode.provinces,
        event_count=episode.event_count or 0,
        detection_count=episode.detection_count or 0,
        frp_sum=float(episode.frp_sum)
        if episode.frp_sum is not None
        else None,
        frp_max=float(episode.frp_max)
        if episode.frp_max is not None
        else None,
        estimated_area_hectares=float(episode.estimated_area_hectares)
        if episode.estimated_area_hectares is not None
        else None,
        gee_candidate=bool(episode.gee_candidate),
        gee_priority=episode.gee_priority,
        slides_data=episode.slides_data,
        representative_event_id=resolve_representative_event_id(event_rows),
        events=events,
    )
