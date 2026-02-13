#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - AGREGACIÓN DE EPISODIOS (UC-17)
=============================================================================

Agrupa 'Fire Events' (micro) en 'Fire Episodes' (macro) para optimizar
el procesamiento en Google Earth Engine y la visualización en frontend.

Funcionalidad:
- Agrupación espacio-temporal configurable
- Cálculo de estado del episodio (active, monitoring, extinct)
- Filtrado de candidatos para GEE (duración, tamaño, intensidad)

Uso:
    # Ejecución estándar (eventos activos)
    python scripts/aggregate_fire_episodes.py

    # Reconstrucción completa (borra episodios existentes)
    python scripts/aggregate_fire_episodes.py --no-rebuild=False
    
    # Dry run (sin cambios en DB)
    python scripts/aggregate_fire_episodes.py --dry-run

    # Parámetros personalizados
    python scripts/aggregate_fire_episodes.py --episode-days-buffer 15

Autor: ForestGuard Team
=============================================================================
"""

import argparse
import logging
import math
import os
import sys
import uuid
from time import perf_counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

LOG = logging.getLogger(__name__)
EPISODE_MONITORING_DAYS = 15


def build_db_url() -> str | URL:
    if os.getenv("DB_HOST") and os.getenv("DB_PASSWORD"):
        return URL.create(
            "postgresql",
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "postgres"),
        )

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url.replace("postgres://", "postgresql://", 1)

    raise ValueError("Database credentials not found")


def get_engine():
    return create_engine(build_db_url(), pool_pre_ping=True)


def normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@dataclass
class EpisodeConfig:
    input_status: str = "active"
    input_start_date: Optional[datetime] = None
    input_end_date: Optional[datetime] = None
    default_lookback_days: int = 90
    max_events: Optional[int] = None
    episode_distance_threshold_meters: float = 7000.0
    episode_days_buffer: int = 12
    admin_mode: str = "soft"
    geometry_mode: str = "buffer_distance"
    buffer_meters_for_geometry: float = 2000.0
    assignment_strategy: str = "closest_distance"
    w_distance: float = 0.6
    w_time: float = 0.4
    w_intensity: float = 0.0
    w_size: float = 0.0
    gee_enable_filter: bool = True
    min_episode_duration_hours: float = 24.0
    min_episode_detections: int = 10
    min_episode_frp_sum: Optional[float] = None
    min_episode_frp_max: Optional[float] = None
    max_episode_count: Optional[int] = None
    priority_sort: str = "frp_sum"
    only_persist_gee_candidates: bool = False
    log_every_events: int = 5000
    statement_timeout_ms: Optional[int] = None


@dataclass
class FireEventRow:
    id: str
    start_date: datetime
    end_date: datetime
    status: Optional[str]
    extinct_at: Optional[datetime]
    lat: float
    lon: float
    bbox_minx: float
    bbox_miny: float
    bbox_maxx: float
    bbox_maxy: float
    province: Optional[str]
    total_detections: int
    frp_sum: float
    frp_max: float
    estimated_area_hectares: float


@dataclass
class FireEpisodeAggregate:
    id: str
    start_date: datetime
    end_date: datetime
    lat_sum: float
    lon_sum: float
    bbox_minx: float
    bbox_miny: float
    bbox_maxx: float
    bbox_maxy: float
    provinces: List[str] = field(default_factory=list)
    event_ids: List[str] = field(default_factory=list)
    event_count: int = 0
    detection_count: int = 0
    frp_sum: float = 0.0
    frp_max: float = 0.0
    estimated_area_hectares: float = 0.0
    gee_candidate: bool = False
    gee_priority: Optional[int] = None
    status: Optional[str] = None

    def centroid(self) -> Tuple[float, float]:
        if self.event_count == 0:
            return (0.0, 0.0)
        return (self.lat_sum / self.event_count, self.lon_sum / self.event_count)

    def add_event(self, event: FireEventRow) -> None:
        self.event_ids.append(event.id)
        self.event_count += 1
        self.lat_sum += event.lat
        self.lon_sum += event.lon
        self.start_date = min(self.start_date, event.start_date)
        self.end_date = max(self.end_date, event.end_date)
        self.bbox_minx = min(self.bbox_minx, event.bbox_minx)
        self.bbox_miny = min(self.bbox_miny, event.bbox_miny)
        self.bbox_maxx = max(self.bbox_maxx, event.bbox_maxx)
        self.bbox_maxy = max(self.bbox_maxy, event.bbox_maxy)
        if event.province and event.province not in self.provinces:
            self.provinces.append(event.province)
        self.detection_count += event.total_detections
        self.frp_sum += event.frp_sum
        self.frp_max = max(self.frp_max, event.frp_max)
        self.estimated_area_hectares += event.estimated_area_hectares


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def meters_to_lat_deg(meters: float) -> float:
    return meters / 111320.0


def meters_to_lon_deg(meters: float, lat: float) -> float:
    return meters / (111320.0 * max(math.cos(math.radians(lat)), 0.1))


def distance_point_to_bbox_m(lat: float, lon: float, bbox: Tuple[float, float, float, float], buffer_m: float) -> float:
    minx, miny, maxx, maxy = bbox
    if buffer_m > 0:
        miny -= meters_to_lat_deg(buffer_m)
        maxy += meters_to_lat_deg(buffer_m)
        minx -= meters_to_lon_deg(buffer_m, lat)
        maxx += meters_to_lon_deg(buffer_m, lat)

    if minx <= lon <= maxx and miny <= lat <= maxy:
        return 0.0

    clamped_lon = min(max(lon, minx), maxx)
    clamped_lat = min(max(lat, miny), maxy)
    return haversine_m(lat, lon, clamped_lat, clamped_lon)


def temporal_overlap_hours(event: FireEventRow, episode: FireEpisodeAggregate) -> float:
    start = max(event.start_date, episode.start_date)
    end = min(event.end_date, episode.end_date)
    if end <= start:
        return 0.0
    return (end - start).total_seconds() / 3600.0


def passes_temporal(event: FireEventRow, episode: FireEpisodeAggregate, buffer_days: int) -> bool:
    buffer = timedelta(days=buffer_days)
    return event.start_date <= episode.end_date + buffer and event.end_date >= episode.start_date - buffer


def passes_admin(event: FireEventRow, episode: FireEpisodeAggregate, admin_mode: str) -> bool:
    if admin_mode == "off":
        return True
    if admin_mode == "soft":
        return True
    if admin_mode == "strict":
        if not event.province or not episode.provinces:
            return True
        return event.province in episode.provinces
    return True


def spatial_distance(event: FireEventRow, episode: FireEpisodeAggregate, config: EpisodeConfig) -> float:
    lat, lon = episode.centroid()
    if config.geometry_mode == "hull_union":
        bbox = (episode.bbox_minx, episode.bbox_miny, episode.bbox_maxx, episode.bbox_maxy)
        return distance_point_to_bbox_m(event.lat, event.lon, bbox, config.buffer_meters_for_geometry)

    distance = haversine_m(event.lat, event.lon, lat, lon)
    if config.geometry_mode == "buffer_distance":
        return max(distance - config.buffer_meters_for_geometry, 0.0)
    return distance


def passes_spatial(event: FireEventRow, episode: FireEpisodeAggregate, config: EpisodeConfig) -> bool:
    distance = spatial_distance(event, episode, config)
    return distance <= config.episode_distance_threshold_meters


def pick_episode(
    candidates: List[Tuple[FireEpisodeAggregate, float, float]],
    event: FireEventRow,
    config: EpisodeConfig,
) -> FireEpisodeAggregate:
    if config.assignment_strategy == "max_overlap_time":
        candidates.sort(key=lambda item: (item[2], -item[1]), reverse=True)
        return candidates[0][0]

    if config.assignment_strategy == "best_score":
        scored: List[Tuple[float, FireEpisodeAggregate]] = []
        for episode, distance, overlap in candidates:
            distance_score = 1.0 - min(distance / config.episode_distance_threshold_meters, 1.0)
            time_score = min(overlap / max(config.episode_days_buffer * 24.0, 1.0), 1.0)
            intensity_score = min((event.frp_max or 0.0) / 100.0, 1.0)
            size_score = min((event.total_detections or 0) / 50.0, 1.0)
            score = (
                config.w_distance * distance_score
                + config.w_time * time_score
                + config.w_intensity * intensity_score
                + config.w_size * size_score
            )
            scored.append((score, episode))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    candidates.sort(key=lambda item: item[1])
    return candidates[0][0]


def build_initial_episode(event: FireEventRow) -> FireEpisodeAggregate:
    provinces = [event.province] if event.province else []
    return FireEpisodeAggregate(
        id=str(uuid.uuid4()),
        start_date=event.start_date,
        end_date=event.end_date,
        lat_sum=event.lat,
        lon_sum=event.lon,
        bbox_minx=event.bbox_minx,
        bbox_miny=event.bbox_miny,
        bbox_maxx=event.bbox_maxx,
        bbox_maxy=event.bbox_maxy,
        provinces=provinces,
        event_ids=[event.id],
        event_count=1,
        detection_count=event.total_detections,
        frp_sum=event.frp_sum,
        frp_max=event.frp_max,
        estimated_area_hectares=event.estimated_area_hectares,
    )


def fetch_fire_events(engine, config: EpisodeConfig) -> List[FireEventRow]:
    status_filter = ""
    params: Dict[str, object] = {}
    date_filters: List[str] = []

    if config.input_status == "active":
        status_filter = "AND status = 'active'"
    elif config.input_status == "active+closed":
        status_filter = "AND (status IN ('active', 'monitoring', 'extinct') OR status IS NULL)"

    if not config.input_start_date and config.default_lookback_days:
        lookback_days = max(config.default_lookback_days, 0)
        if lookback_days:
            lookback_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            date_filters.append("start_date >= :lookback_date")
            params["lookback_date"] = lookback_date

    if config.input_start_date:
        date_filters.append("start_date >= :start_date")
        params["start_date"] = config.input_start_date
    if config.input_end_date:
        date_filters.append("end_date <= :end_date")
        params["end_date"] = config.input_end_date
    date_clause = f"AND {' AND '.join(date_filters)}" if date_filters else ""

    limit_clause = ""
    if config.max_events:
        limit_clause = "LIMIT :max_events"
        params["max_events"] = config.max_events

    sql = text(
        f"""
        SELECT
            id,
            start_date,
            end_date,
            status,
            extinct_at,
            COALESCE(total_detections, 0) AS total_detections,
            COALESCE(sum_frp, 0) AS frp_sum,
            COALESCE(max_frp, 0) AS frp_max,
            COALESCE(estimated_area_hectares, 0) AS estimated_area_hectares,
            province,
            ST_Y(centroid::geometry) AS lat,
            ST_X(centroid::geometry) AS lon,
            ST_XMin(perimeter::geometry) AS bbox_minx,
            ST_YMin(perimeter::geometry) AS bbox_miny,
            ST_XMax(perimeter::geometry) AS bbox_maxx,
            ST_YMax(perimeter::geometry) AS bbox_maxy
        FROM fire_events
        WHERE 1=1
        {status_filter}
        {date_clause}
        ORDER BY start_date ASC
        {limit_clause}
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(sql, params).mappings().all()

    events: List[FireEventRow] = []
    for row in rows:
        lat = float(row["lat"]) if row["lat"] is not None else 0.0
        lon = float(row["lon"]) if row["lon"] is not None else 0.0
        bbox_minx = row["bbox_minx"] if row["bbox_minx"] is not None else lon
        bbox_miny = row["bbox_miny"] if row["bbox_miny"] is not None else lat
        bbox_maxx = row["bbox_maxx"] if row["bbox_maxx"] is not None else lon
        bbox_maxy = row["bbox_maxy"] if row["bbox_maxy"] is not None else lat

        events.append(
            FireEventRow(
                id=str(row["id"]),
                start_date=row["start_date"],
                end_date=row["end_date"],
                status=row["status"],
                extinct_at=row["extinct_at"],
                lat=lat,
                lon=lon,
                bbox_minx=float(bbox_minx),
                bbox_miny=float(bbox_miny),
                bbox_maxx=float(bbox_maxx),
                bbox_maxy=float(bbox_maxy),
                province=row["province"],
                total_detections=int(row["total_detections"] or 0),
                frp_sum=float(row["frp_sum"] or 0),
                frp_max=float(row["frp_max"] or 0),
                estimated_area_hectares=float(row["estimated_area_hectares"] or 0),
            )
        )

    return events


def build_episodes(events: List[FireEventRow], config: EpisodeConfig) -> List[FireEpisodeAggregate]:
    episodes: List[FireEpisodeAggregate] = []
    total_events = len(events)
    log_every = max(int(config.log_every_events or 0), 0)
    started_at = perf_counter()

    for idx, event in enumerate(events, start=1):
        candidates: List[Tuple[FireEpisodeAggregate, float, float]] = []
        for episode in episodes:
            if not passes_temporal(event, episode, config.episode_days_buffer):
                continue
            if not passes_admin(event, episode, config.admin_mode):
                continue
            if not passes_spatial(event, episode, config):
                continue
            distance = spatial_distance(event, episode, config)
            overlap = temporal_overlap_hours(event, episode)
            candidates.append((episode, distance, overlap))

        if not candidates:
            episodes.append(build_initial_episode(event))
            continue

        selected = pick_episode(candidates, event, config)
        selected.add_event(event)

        if log_every and idx % log_every == 0:
            elapsed = perf_counter() - started_at
            LOG.info(
                "Progress: processed %s/%s events (%.1f%%). Episodes=%s. Elapsed=%.2fs",
                idx,
                total_events,
                (idx / total_events) * 100 if total_events else 100,
                len(episodes),
                elapsed,
            )

    return episodes


def assign_episode_statuses(
    episodes: List[FireEpisodeAggregate],
    event_meta_map: Dict[str, Dict[str, Optional[datetime]]],
) -> None:
    now = datetime.now(timezone.utc)
    monitoring_window = timedelta(days=EPISODE_MONITORING_DAYS)

    for episode in episodes:
        episode_events = [
            event_meta_map.get(str(eid))
            for eid in episode.event_ids
            if event_meta_map.get(str(eid)) is not None
        ]

        if not episode_events:
            episode.status = "closed"
            continue

        if any(ev.get("status") == "active" for ev in episode_events):
            episode.status = "active"
            continue

        last_extinct = None
        for ev in episode_events:
            ext_at = ev.get("extinct_at") or ev.get("end_date")
            ext_at = normalize_datetime(ext_at)
            if ext_at and (last_extinct is None or ext_at > last_extinct):
                last_extinct = ext_at

        if last_extinct and now - last_extinct < monitoring_window:
            episode.status = "monitoring"
        else:
            episode.status = "extinct"


def apply_gee_filters(episodes: List[FireEpisodeAggregate], config: EpisodeConfig) -> None:
    for episode in episodes:
        if episode.status not in ("active", "monitoring"):
            episode.gee_candidate = False
            continue
        duration_hours = (episode.end_date - episode.start_date).total_seconds() / 3600.0
        candidate = True

        if config.gee_enable_filter:
            if duration_hours < config.min_episode_duration_hours:
                candidate = False
            if episode.detection_count < config.min_episode_detections:
                candidate = False
            if config.min_episode_frp_sum is not None and episode.frp_sum < config.min_episode_frp_sum:
                candidate = False
            if config.min_episode_frp_max is not None and episode.frp_max < config.min_episode_frp_max:
                candidate = False

        episode.gee_candidate = candidate

    priority_map = {
        "frp_sum": lambda ep: ep.frp_sum,
        "frp_max": lambda ep: ep.frp_max,
        "detections": lambda ep: ep.detection_count,
        "area_estimated": lambda ep: ep.estimated_area_hectares,
        "recent": lambda ep: ep.end_date,
    }
    sorter = priority_map.get(config.priority_sort, priority_map["frp_sum"])

    candidates = [ep for ep in episodes if ep.gee_candidate]
    candidates.sort(key=sorter, reverse=True)

    for idx, episode in enumerate(candidates, start=1):
        if config.max_episode_count and idx > config.max_episode_count:
            episode.gee_candidate = False
            episode.gee_priority = None
        else:
            episode.gee_priority = idx


def persist_episodes(
    engine,
    episodes,
    rebuild,
    dry_run,
    only_gee_candidates=False,
    statement_timeout_ms: Optional[int] = None,
):
    
    if only_gee_candidates:
        episodes = [ep for ep in episodes if ep.gee_candidate]
        LOG.info("Filtered to %s GEE candidates for persistence", len(episodes))
           
    if dry_run:
        return

    with engine.begin() as conn:
        if statement_timeout_ms is not None:
            conn.execute(
                text("SET statement_timeout = :timeout_ms"),
                {"timeout_ms": int(statement_timeout_ms)},
            )
            LOG.info("Set statement_timeout to %sms", statement_timeout_ms)
        if rebuild:
            conn.execute(text("TRUNCATE fire_episode_events, fire_episodes CASCADE"))

        insert_episode_sql = text(
            """
            INSERT INTO fire_episodes (
                id, status, start_date, end_date,
                centroid_lat, centroid_lon,
                bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
                provinces, event_count, detection_count,
                frp_sum, frp_max, estimated_area_hectares,
                gee_candidate, gee_priority,
                created_at, updated_at
            ) VALUES (
                :id, :status, :start_date, :end_date,
                :centroid_lat, :centroid_lon,
                :bbox_minx, :bbox_miny, :bbox_maxx, :bbox_maxy,
                :provinces, :event_count, :detection_count,
                :frp_sum, :frp_max, :estimated_area_hectares,
                :gee_candidate, :gee_priority,
                NOW(), NOW()
            )
            """
        )

        insert_link_sql = text(
            """
            INSERT INTO fire_episode_events (episode_id, event_id, added_at)
            VALUES (:episode_id, :event_id, NOW())
            ON CONFLICT DO NOTHING
            """
        )

        episode_count = 0
        link_count = 0
        last_log_at = perf_counter()
        log_every_episodes = 500
        log_every_links = 5000

        for episode in episodes:
            status = episode.status or "closed"
            centroid_lat, centroid_lon = episode.centroid()
            conn.execute(
                insert_episode_sql,
                {
                    "id": episode.id,
                    "status": status,
                    "start_date": episode.start_date,
                    "end_date": episode.end_date,
                    "centroid_lat": centroid_lat,
                    "centroid_lon": centroid_lon,
                    "bbox_minx": episode.bbox_minx,
                    "bbox_miny": episode.bbox_miny,
                    "bbox_maxx": episode.bbox_maxx,
                    "bbox_maxy": episode.bbox_maxy,
                    "provinces": episode.provinces if episode.provinces else None,
                    "event_count": episode.event_count,
                    "detection_count": episode.detection_count,
                    "frp_sum": episode.frp_sum,
                    "frp_max": episode.frp_max,
                    "estimated_area_hectares": episode.estimated_area_hectares,
                    "gee_candidate": episode.gee_candidate,
                    "gee_priority": episode.gee_priority,
                },
            )
            episode_count += 1
            if episode_count % log_every_episodes == 0:
                elapsed = perf_counter() - last_log_at
                LOG.info("Persisted %s episodes (%.2fs)", episode_count, elapsed)
                last_log_at = perf_counter()

            for event_id in episode.event_ids:
                conn.execute(
                    insert_link_sql,
                    {"episode_id": episode.id, "event_id": event_id},
                )
                link_count += 1
                if link_count % log_every_links == 0:
                    elapsed = perf_counter() - last_log_at
                    LOG.info("Persisted %s episode-event links (%.2fs)", link_count, elapsed)
                    last_log_at = perf_counter()
        LOG.info("Persist complete: %s episodes, %s links", episode_count, link_count)


def log_summary(episodes: List[FireEpisodeAggregate], events_count: int) -> None:
    candidate_count = sum(1 for ep in episodes if ep.gee_candidate)
    status_counts: Dict[str, int] = {}
    for ep in episodes:
        key = ep.status or "unknown"
        status_counts[key] = status_counts.get(key, 0) + 1
    LOG.info("Input events: %s", events_count)
    LOG.info("Episodes created: %s", len(episodes))
    LOG.info("GEE candidates: %s", candidate_count)
    LOG.info("Episode status distribution: %s", status_counts)

    province_counts: Dict[str, int] = {}
    for ep in episodes:
        for prov in ep.provinces:
            province_counts[prov] = province_counts.get(prov, 0) + 1
    if province_counts:
        LOG.info("Episode distribution by province: %s", province_counts)


def parse_args() -> EpisodeConfig:
    parser = argparse.ArgumentParser(description="Aggregate fire_events into fire_episodes (UC-17).")
    parser.add_argument("--input-status", choices=["active", "active+closed"], default="active")
    parser.add_argument("--input-start-date", default=None)
    parser.add_argument("--input-end-date", default=None)
    parser.add_argument("--max-events", type=int, default=None)
    parser.add_argument("--episode-distance-threshold-meters", type=float, default=7000.0)
    parser.add_argument("--episode-days-buffer", type=int, default=12)
    parser.add_argument("--admin-mode", choices=["strict", "soft", "off"], default="soft")
    parser.add_argument("--geometry-mode", choices=["centroid", "buffer_distance", "hull_union"], default="buffer_distance")
    parser.add_argument("--buffer-meters-for-geometry", type=float, default=2000.0)
    parser.add_argument(
        "--assignment-strategy",
        choices=["closest_distance", "max_overlap_time", "best_score"],
        default="closest_distance",
    )
    parser.add_argument("--w-distance", type=float, default=0.6)
    parser.add_argument("--w-time", type=float, default=0.4)
    parser.add_argument("--w-intensity", type=float, default=0.0)
    parser.add_argument("--w-size", type=float, default=0.0)
    parser.add_argument("--gee-disable-filter", action="store_true")
    parser.add_argument("--min-episode-duration-hours", type=float, default=24.0)
    parser.add_argument("--min-episode-detections", type=int, default=10)
    parser.add_argument("--min-episode-frp-sum", type=float, default=None)
    parser.add_argument("--min-episode-frp-max", type=float, default=None)
    parser.add_argument("--max-episode-count", type=int, default=None)
    parser.add_argument(
        "--priority-sort",
        choices=["frp_sum", "frp_max", "detections", "area_estimated", "recent"],
        default="frp_sum",
    )
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=90,
        help="Limit input events to the last N days (0 disables lookback).",
    )
    parser.add_argument(
        "--only-persist-gee-candidates",
        action="store_true",
        help="Persist only GEE candidates (skips non-candidates).",
    )
    parser.add_argument(
        "--log-every-events",
        type=int,
        default=5000,
        help="Log progress every N processed events (0 disables).",
    )
    parser.add_argument(
        "--statement-timeout-ms",
        type=int,
        default=None,
        help="Override Postgres statement_timeout in milliseconds (0 disables).",
    )
    args = parser.parse_args()

    config = EpisodeConfig(
        input_status=args.input_status,
        input_start_date=parse_date(args.input_start_date),
        input_end_date=parse_date(args.input_end_date),
        max_events=args.max_events,
        episode_distance_threshold_meters=args.episode_distance_threshold_meters,
        episode_days_buffer=args.episode_days_buffer,
        admin_mode=args.admin_mode,
        geometry_mode=args.geometry_mode,
        buffer_meters_for_geometry=args.buffer_meters_for_geometry,
        assignment_strategy=args.assignment_strategy,
        w_distance=args.w_distance,
        w_time=args.w_time,
        w_intensity=args.w_intensity,
        w_size=args.w_size,
        gee_enable_filter=not args.gee_disable_filter,
        min_episode_duration_hours=args.min_episode_duration_hours,
        min_episode_detections=args.min_episode_detections,
        min_episode_frp_sum=args.min_episode_frp_sum,
        min_episode_frp_max=args.min_episode_frp_max,
        max_episode_count=args.max_episode_count,
        priority_sort=args.priority_sort,
        default_lookback_days=args.lookback_days,
        only_persist_gee_candidates=args.only_persist_gee_candidates,
        log_every_events=args.log_every_events,
        statement_timeout_ms=args.statement_timeout_ms,
    )

    rebuild = not args.no_rebuild
    return config, rebuild, args.dry_run


def main():
    config, rebuild, dry_run = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    engine = get_engine()
    t0 = perf_counter()
    events = fetch_fire_events(engine, config)
    LOG.info("Fetched %s events in %.2fs", len(events), perf_counter() - t0)

    if not events:
        LOG.info("No fire events found for the given filters.")
        return

    LOG.info("Rebuild mode: %s | Dry run: %s", rebuild, dry_run)
    LOG.info(
        "Input status: %s | Lookback days: %s | Only persist GEE candidates: %s",
        config.input_status,
        config.default_lookback_days,
        config.only_persist_gee_candidates,
    )
    t1 = perf_counter()
    episodes = build_episodes(events, config)
    LOG.info("Built episodes in %.2fs", perf_counter() - t1)
    event_meta_map = {
        event.id: {
            "status": event.status,
            "extinct_at": event.extinct_at,
            "end_date": event.end_date,
        }
        for event in events
    }
    t2 = perf_counter()
    assign_episode_statuses(episodes, event_meta_map)
    LOG.info("Assigned episode statuses in %.2fs", perf_counter() - t2)
    t3 = perf_counter()
    apply_gee_filters(episodes, config)
    LOG.info("Applied GEE filters in %.2fs", perf_counter() - t3)

    log_summary(episodes, len(events))
    t4 = perf_counter()
    persist_episodes(
        engine,
        episodes,
        rebuild=rebuild,
        dry_run=dry_run,
        only_gee_candidates=config.only_persist_gee_candidates,
        statement_timeout_ms=config.statement_timeout_ms,
    )

    LOG.info("Persisted episodes in %.2fs", perf_counter() - t4)

    if dry_run:
        LOG.info("Dry run complete. No database changes were applied.")


if __name__ == "__main__":
    main()
