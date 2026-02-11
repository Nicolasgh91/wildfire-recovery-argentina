from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Set
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.episode_service import EpisodeService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClusteringVersion:
    """Clustering parameters snapshot for episode generation."""
    id: UUID
    epsilon_km: float
    min_points: int
    temporal_window_hours: int


@dataclass(frozen=True)
class EventRecord:
    """Normalized fire event row for clustering routines."""
    id: UUID
    start_date: datetime
    end_date: datetime
    lat: float
    lon: float
    province: Optional[str]
    total_detections: int
    sum_frp: Optional[float]
    max_frp: Optional[float]
    estimated_area_hectares: Optional[float]


class ClusteringService:
    """Service for clustering fire events into episodes."""
    def __init__(self, db: Session):
        self.db = db
        self.episodes = EpisodeService(db)

    def _get_active_version(self) -> ClusteringVersion:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT id, epsilon_km, min_points, temporal_window_hours
                      FROM clustering_versions
                     WHERE is_active = true
                  ORDER BY created_at DESC
                     LIMIT 1
                    """
                )
            )
            .mappings()
            .first()
        )
        if not row:
            raise RuntimeError("No active clustering_version found")

        return ClusteringVersion(
            id=row["id"],
            epsilon_km=float(row["epsilon_km"]),
            min_points=int(row["min_points"]),
            temporal_window_hours=int(row["temporal_window_hours"]),
        )

    def _load_recalc_episode_ids(self) -> List[UUID]:
        rows = self.db.execute(
            text("SELECT id FROM fire_episodes WHERE requires_recalculation = true")
        ).fetchall()
        return [row[0] for row in rows]

    def _load_events(
        self,
        *,
        since: datetime,
        extra_event_ids: Optional[Sequence[UUID]] = None,
        max_events: Optional[int] = None,
    ) -> List[EventRecord]:
        query = text(
            """
            SELECT
                fe.id,
                fe.start_date,
                fe.end_date,
                fe.province,
                fe.total_detections,
                fe.sum_frp,
                fe.max_frp,
                fe.estimated_area_hectares,
                ST_Y(fe.centroid::geometry) AS lat,
                ST_X(fe.centroid::geometry) AS lon
            FROM fire_events fe
            WHERE fe.centroid IS NOT NULL
              AND fe.start_date >= :since
            ORDER BY fe.start_date ASC
            """
        )
        if max_events:
            query = text(f"{query.text}\nLIMIT {int(max_events)}")

        rows = self.db.execute(query, {"since": since}).mappings().all()

        events: Dict[UUID, EventRecord] = {}
        for row in rows:
            event = EventRecord(
                id=row["id"],
                start_date=self._ensure_tz(row["start_date"]),
                end_date=self._ensure_tz(row["end_date"]),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                province=row.get("province"),
                total_detections=int(row.get("total_detections") or 0),
                sum_frp=row.get("sum_frp"),
                max_frp=row.get("max_frp"),
                estimated_area_hectares=row.get("estimated_area_hectares"),
            )
            events[event.id] = event

        if extra_event_ids:
            missing_ids = [eid for eid in extra_event_ids if eid not in events]
            if missing_ids:
                extra_rows = (
                    self.db.execute(
                        text(
                            """
                            SELECT
                                fe.id,
                                fe.start_date,
                                fe.end_date,
                                fe.province,
                                fe.total_detections,
                                fe.sum_frp,
                                fe.max_frp,
                                fe.estimated_area_hectares,
                                ST_Y(fe.centroid::geometry) AS lat,
                                ST_X(fe.centroid::geometry) AS lon
                            FROM fire_events fe
                            WHERE fe.id IN :event_ids
                            """
                        ).bindparams(bindparam("event_ids", expanding=True)),
                        {"event_ids": [str(eid) for eid in missing_ids]},
                    )
                    .mappings()
                    .all()
                )
                for row in extra_rows:
                    events[row["id"]] = EventRecord(
                        id=row["id"],
                        start_date=self._ensure_tz(row["start_date"]),
                        end_date=self._ensure_tz(row["end_date"]),
                        lat=float(row["lat"]),
                        lon=float(row["lon"]),
                        province=row.get("province"),
                        total_detections=int(row.get("total_detections") or 0),
                        sum_frp=row.get("sum_frp"),
                        max_frp=row.get("max_frp"),
                        estimated_area_hectares=row.get("estimated_area_hectares"),
                    )

        return list(events.values())

    @staticmethod
    def _ensure_tz(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _load_event_episode_map(self, event_ids: Sequence[UUID]) -> Dict[UUID, UUID]:
        if not event_ids:
            return {}
        rows = self.db.execute(
            text(
                """
                    SELECT event_id, episode_id
                      FROM fire_episode_events
                     WHERE event_id IN :event_ids
                    """
            ).bindparams(bindparam("event_ids", expanding=True)),
            {"event_ids": [str(eid) for eid in event_ids]},
        ).fetchall()
        return {row[0]: row[1] for row in rows}

    def _find_candidate_episodes(
        self,
        event: EventRecord,
        *,
        epsilon_meters: float,
        temporal_window_hours: int,
    ) -> List[dict]:
        rows = (
            self.db.execute(
                text(
                    """
                    SELECT id,
                           start_date,
                           end_date,
                           estimated_area_hectares,
                           event_count,
                           status
                      FROM fire_episodes
                     WHERE status != 'closed'
                       AND ST_DWithin(
                             ST_SetSRID(ST_MakePoint(centroid_lon, centroid_lat), 4326)::geography,
                             ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                             :epsilon
                         )
                       AND start_date <= :event_end + make_interval(hours => :hours)
                       AND COALESCE(last_seen_at, end_date, start_date) >= :event_start - make_interval(hours => :hours)
                    """
                ),
                {
                    "lon": event.lon,
                    "lat": event.lat,
                    "epsilon": epsilon_meters,
                    "event_start": event.start_date,
                    "event_end": event.end_date,
                    "hours": temporal_window_hours,
                },
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    @staticmethod
    def _choose_absorbing(candidates: Sequence[dict]) -> dict:
        def sort_key(item: dict):
            start_date = item.get("start_date") or datetime.now(timezone.utc)
            if isinstance(start_date, datetime) and start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            area = item.get("estimated_area_hectares") or 0
            return (start_date, -float(area))

        return sorted(candidates, key=sort_key)[0]

    def run_clustering(
        self,
        *,
        days_back: int = 90,
        max_events: int = 5000,
        dry_run: bool = False,
    ) -> dict:
        version = self._get_active_version()
        since = datetime.now(timezone.utc) - timedelta(days=days_back)

        recalc_episode_ids = self._load_recalc_episode_ids()
        extra_event_ids: List[UUID] = []
        if recalc_episode_ids:
            extra_event_rows = self.db.execute(
                text(
                    """
                        SELECT event_id
                          FROM fire_episode_events
                         WHERE episode_id IN :episode_ids
                        """
                ).bindparams(bindparam("episode_ids", expanding=True)),
                {"episode_ids": [str(eid) for eid in recalc_episode_ids]},
            ).fetchall()
            extra_event_ids = [row[0] for row in extra_event_rows]

        events = self._load_events(
            since=since,
            extra_event_ids=extra_event_ids,
            max_events=max_events,
        )

        if not events:
            logger.info("No fire events found for clustering")
            return {
                "events_processed": 0,
                "episodes_created": 0,
                "episodes_updated": 0,
                "episodes_merged": 0,
                "candidate_metrics": {
                    "total_events": 0,
                    "min": 0,
                    "avg": 0,
                    "p95": 0,
                    "max": 0,
                    "over_3_count": 0,
                    "over_3_pct": 0,
                },
            }

        event_ids = [event.id for event in events]
        event_episode_map = self._load_event_episode_map(event_ids)

        to_process = [
            event
            for event in events
            if event.id not in event_episode_map
            or event_episode_map.get(event.id) in recalc_episode_ids
        ]

        touched: Set[UUID] = set()
        episodes_created = 0
        episodes_updated = 0
        episodes_merged = 0
        candidate_counts: List[int] = []

        epsilon_meters = version.epsilon_km * 1000.0

        for event in to_process:
            candidates = self._find_candidate_episodes(
                event,
                epsilon_meters=epsilon_meters,
                temporal_window_hours=version.temporal_window_hours,
            )
            candidate_counts.append(len(candidates))

            if not candidates:
                episode_id = self.episodes.create_episode(event, version.id)
                self.episodes.assign_event(episode_id, event.id)
                touched.add(episode_id)
                episodes_created += 1
                continue

            absorbing = self._choose_absorbing(candidates)
            absorbing_id = absorbing["id"]

            if len(candidates) > 1:
                for candidate in candidates:
                    if candidate["id"] == absorbing_id:
                        continue
                    self.episodes.merge_episodes(
                        absorbing_episode_id=absorbing_id,
                        absorbed_episode_id=candidate["id"],
                        reason="spatial_overlap",
                        clustering_version_id=version.id,
                    )
                    episodes_merged += 1

            old_episode_ids = self.episodes.assign_event(absorbing_id, event.id)
            touched.add(absorbing_id)
            touched.update(old_episode_ids)
            episodes_updated += 1

        for episode_id in touched:
            self.episodes.update_episode_metrics(
                episode_id,
                clustering_version_id=version.id,
                min_points=version.min_points,
            )

        candidate_metrics = self._build_candidate_metrics(candidate_counts)

        if dry_run:
            self.db.rollback()
        else:
            self.db.commit()

        logger.info(
            "Clustering complete: events=%s created=%s updated=%s merged=%s",
            len(to_process),
            episodes_created,
            episodes_updated,
            episodes_merged,
        )
        logger.info(f"Clustering candidate metrics: {candidate_metrics}")

        return {
            "events_processed": len(to_process),
            "episodes_created": episodes_created,
            "episodes_updated": episodes_updated,
            "episodes_merged": episodes_merged,
            "candidate_metrics": candidate_metrics,
        }

    @staticmethod
    def _build_candidate_metrics(candidate_counts: Sequence[int]) -> Dict[str, float]:
        if not candidate_counts:
            return {
                "total_events": 0,
                "min": 0,
                "avg": 0,
                "p95": 0,
                "max": 0,
                "over_3_count": 0,
                "over_3_pct": 0,
            }

        values = sorted(candidate_counts)
        total = len(values)
        avg = sum(values) / total
        over_3 = sum(1 for value in values if value > 3)

        def percentile(pct: float) -> float:
            if total == 1:
                return float(values[0])
            k = (total - 1) * pct
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return float(values[int(k)])
            d0 = values[f] * (c - k)
            d1 = values[c] * (k - f)
            return float(d0 + d1)

        return {
            "total_events": total,
            "min": float(values[0]),
            "avg": round(avg, 2),
            "p95": round(percentile(0.95), 2),
            "max": float(values[-1]),
            "over_3_count": over_3,
            "over_3_pct": round((over_3 / total) * 100, 2),
        }
