"""
=============================================================================
FORESTGUARD - FIRE EPISODE SERVICE
=============================================================================

Service for managing fire episodes (clustered fire events).

Concepts:
    Fire Event: Individual fire detection point from satellite data
    Fire Episode: Cluster of related fire events (temporal + spatial)

Features:
    - Episode creation from initial fire event
    - Event-to-episode assignment with conflict resolution
    - Episode merging when overlapping fires are detected
    - Episode metrics aggregation (FRP, area, detection count)
    - Status management (active → monitoring → extinct → closed)

Episode Lifecycle:
    1. First detection → create episode (status: active)
    2. New detections → assign events, update metrics
    3. Overlapping episodes → merge (absorbing episode wins)
    4. No new detections for N hours → status: extinct
    5. Episode closed for GEE processing

Metrics Updated:
    - event_count: Number of fire events in episode
    - detection_count: Total hot pixel detections
    - frp_sum/frp_max: Fire radiative power aggregates
    - estimated_area_hectares: Total affected area
    - centroid/bbox: Geometric calculations
    - gee_candidate/gee_priority: Eligibility for satellite imagery

Author: ForestGuard Team
Version: 2.0.0
Last Updated: 2026-02-08
=============================================================================
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.episode_flow_parameters import (
    load_canonical_episode_flow_parameters,
)


class EventPayload(Protocol):
    """Protocol describing the minimal fire event payload."""
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


logger = logging.getLogger(__name__)


class EpisodeService:
    """
    Servicio de orquestamiento de Episodios (Clustering de Eventos).
    
    Gestiona el ciclo de vida de los `fire_episodes` (Activo -> Monitoreo -> Extinto -> Cerrado).
    Provee métodos para resolver estados basados en `episode_temporal_window_hours`,
    asignar eventos calculados por DBSCAN a la tabla pivot `fire_episode_events` y
    recalcular los agregados (área, contadores, frp top) del episodio.
    """
    def __init__(self, db: Session):
        self.db = db
        self._episode_flow_params_cache: Optional[dict[str, float | int]] = None

    @staticmethod
    def _ensure_tz(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _episode_flow_params(self) -> dict[str, float | int]:
        if self._episode_flow_params_cache is None:
            self._episode_flow_params_cache = load_canonical_episode_flow_parameters(
                self.db
            )
        return self._episode_flow_params_cache

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

    def _resolve_inactive_grace_hours(self, default: int = 72) -> int:
        value = self._episode_flow_params().get("episode_temporal_window_hours", default)
        try:
            hours = int(value)
        except (TypeError, ValueError):
            return default
        return max(1, hours)

    def _get_episode_window_hours(self) -> int:
        """Lee episode_temporal_window_hours de system_parameters con fallback a 720."""
        try:
            from app.services.episode_flow_parameters import get_parameter
            value = get_parameter("episode_temporal_window_hours")
            return int(value) if value is not None else 720
        except Exception:
            logger.warning("Could not read episode_temporal_window_hours, using default 720")
            return 720

    def _resolve_episode_status(
        self,
        event_statuses: set[str],
        last_seen_at: datetime | None,
        start_date: datetime | None = None,
        window_hours: int | None = None,
    ) -> str:
        """Resuelve el estado de un episodio usando modelo de doble condicion para extinct.

        Reglas canonicas (en orden de prioridad):
            1. Si al menos 1 evento esta 'active'  → 'active'
            2. Si elapsed >= ventana Y todos los eventos estan 'extinct' → 'extinct'
            3. En cualquier otro caso → 'monitoring'

        La regla 2 requiere la conjuncion de ambas condiciones:
          - Condicion temporal: now() - last_seen_at >= episode_temporal_window_hours (720h)
          - Condicion de eventos: no hay eventos en estado distinto a 'extinct'
        Esto protege contra fallas del event_status_task (que dejaria eventos en
        'monitoring' aunque se supero la ventana temporal del episodio).

        Args:
            event_statuses: conjunto de estados de los eventos asociados al episodio.
            last_seen_at: timestamp de la ultima actividad detectada.
            start_date: fallback si last_seen_at es None.
            window_hours: ventana temporal en horas. Si None, lee de system_parameters.

        Returns:
            Estado del episodio: 'active', 'monitoring' o 'extinct'.
        """
        if "active" in event_statuses:
            return "active"

        if window_hours is None:
            window_hours = self._get_episode_window_hours()

        reference_date = last_seen_at or start_date
        if reference_date is None:
            logger.warning("Episode has no last_seen_at nor start_date, defaulting to monitoring")
            return "monitoring"

        now = datetime.now(timezone.utc)
        if reference_date.tzinfo is None:
            reference_date = reference_date.replace(tzinfo=timezone.utc)
        else:
            reference_date = reference_date.astimezone(timezone.utc)

        elapsed = now - reference_date
        window = timedelta(hours=window_hours)

        # Condicion temporal: se supero la ventana de inactividad
        temporal_condition = elapsed >= window
        # Condicion de eventos: todos los eventos estan extintos (no hay monitoring vivos)
        all_events_extinct = bool(event_statuses) and all(
            s == "extinct" for s in event_statuses
        )

        if temporal_condition and all_events_extinct:
            return "extinct"

        return "monitoring"

    def create_episode(self, event: EventPayload, clustering_version_id: UUID) -> UUID:
        provinces = [event.province] if event.province else []

        row = self.db.execute(
            text(
                """
                    INSERT INTO fire_episodes (
                        status,
                        start_date,
                        end_date,
                        last_seen_at,
                        centroid_lat,
                        centroid_lon,
                        bbox_minx,
                        bbox_miny,
                        bbox_maxx,
                        bbox_maxy,
                        provinces,
                        event_count,
                        detection_count,
                        frp_sum,
                        frp_max,
                        estimated_area_hectares,
                        clustering_version_id,
                        requires_recalculation,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        'active',
                        :start_date,
                        NULL,
                        :last_seen_at,
                        :centroid_lat,
                        :centroid_lon,
                        :bbox_minx,
                        :bbox_miny,
                        :bbox_maxx,
                        :bbox_maxy,
                        :provinces,
                        1,
                        :detection_count,
                        :frp_sum,
                        :frp_max,
                        :estimated_area_hectares,
                        :clustering_version_id,
                        false,
                        NOW(),
                        NOW()
                    )
                    RETURNING id
                    """
            ),
            {
                "start_date": event.start_date,
                "last_seen_at": event.end_date,
                "centroid_lat": event.lat,
                "centroid_lon": event.lon,
                "bbox_minx": event.lon,
                "bbox_miny": event.lat,
                "bbox_maxx": event.lon,
                "bbox_maxy": event.lat,
                "provinces": provinces,
                "detection_count": int(event.total_detections or 0),
                "frp_sum": event.sum_frp,
                "frp_max": event.max_frp,
                "estimated_area_hectares": event.estimated_area_hectares,
                "clustering_version_id": str(clustering_version_id),
            },
        ).scalar()
        return row

    def assign_event(self, episode_id: UUID, event_id: UUID) -> list[UUID]:
        old_episode_rows = self.db.execute(
            text(
                """
                SELECT episode_id
                  FROM fire_episode_events
                 WHERE event_id = :event_id
                   AND episode_id != :episode_id
                """
            ),
            {"event_id": str(event_id), "episode_id": str(episode_id)},
        ).fetchall()

        old_episode_ids = [row[0] for row in old_episode_rows]

        self.db.execute(
            text(
                """
                DELETE FROM fire_episode_events
                 WHERE event_id = :event_id
                """
            ),
            {"event_id": str(event_id)},
        )
        self.db.execute(
            text(
                """
                INSERT INTO fire_episode_events (episode_id, event_id, added_at)
                VALUES (:episode_id, :event_id, NOW())
                """
            ),
            {"episode_id": str(episode_id), "event_id": str(event_id)},
        )

        return old_episode_ids

    def merge_episodes(
        self,
        *,
        absorbing_episode_id: UUID,
        absorbed_episode_id: UUID,
        reason: str,
        clustering_version_id: Optional[UUID],
        notes: Optional[str] = None,
    ) -> None:
        self.db.execute(
            text(
                """
                DELETE FROM fire_episode_events
                 WHERE episode_id = :absorbed_episode_id
                   AND event_id IN (
                       SELECT event_id
                         FROM fire_episode_events
                        WHERE episode_id = :absorbing_episode_id
                   )
                """
            ),
            {
                "absorbed_episode_id": str(absorbed_episode_id),
                "absorbing_episode_id": str(absorbing_episode_id),
            },
        )

        self.db.execute(
            text(
                """
                UPDATE fire_episode_events
                   SET episode_id = :absorbing_episode_id
                 WHERE episode_id = :absorbed_episode_id
                """
            ),
            {
                "absorbed_episode_id": str(absorbed_episode_id),
                "absorbing_episode_id": str(absorbing_episode_id),
            },
        )

        self.db.execute(
            text(
                """
                INSERT INTO episode_mergers (
                    absorbed_episode_id,
                    absorbing_episode_id,
                    reason,
                    merged_by_version_id,
                    notes
                )
                VALUES (
                    :absorbed_episode_id,
                    :absorbing_episode_id,
                    :reason,
                    :merged_by_version_id,
                    :notes
                )
                """
            ),
            {
                "absorbed_episode_id": str(absorbed_episode_id),
                "absorbing_episode_id": str(absorbing_episode_id),
                "reason": reason,
                "merged_by_version_id": str(clustering_version_id)
                if clustering_version_id
                else None,
                "notes": notes,
            },
        )

        self.db.execute(
            text(
                """
                UPDATE fire_episodes
                   SET status = 'closed',
                       end_date = COALESCE(end_date, last_seen_at, NOW()),
                       last_seen_at = COALESCE(last_seen_at, end_date, NOW()),
                       requires_recalculation = false,
                       updated_at = NOW()
                 WHERE id = :episode_id
                """
            ),
            {"episode_id": str(absorbed_episode_id)},
        )

    def update_episode_metrics(
        self,
        episode_id: UUID,
        *,
        clustering_version_id: UUID,
        min_points: int,
    ) -> None:
        existing = (
            self.db.execute(
                text(
                    """
                    SELECT status, end_date, last_seen_at, extinct_at
                      FROM fire_episodes
                     WHERE id = :episode_id
                    """
                ),
                {"episode_id": str(episode_id)},
            )
            .mappings()
            .first()
        )

        existing_status = (existing.get("status") if existing else None) or "active"
        existing_end_date = existing.get("end_date") if existing else None
        existing_last_seen = existing.get("last_seen_at") if existing else None
        existing_extinct_at = existing.get("extinct_at") if existing else None

        if isinstance(existing_end_date, datetime):
            existing_end_date = self._ensure_tz(existing_end_date)
        if isinstance(existing_last_seen, datetime):
            existing_last_seen = self._ensure_tz(existing_last_seen)

        row = (
            self.db.execute(
                text(
                    """
                    SELECT
                        MIN(fe.start_date) AS start_date,
                        MAX(fe.end_date) AS last_seen_at,
                        COUNT(*) AS event_count,
                        COALESCE(SUM(fe.total_detections), 0) AS detection_count,
                        COALESCE(SUM(fe.sum_frp), 0) AS frp_sum,
                        MAX(fe.max_frp) AS frp_max,
                        COALESCE(SUM(fe.estimated_area_hectares), 0) AS estimated_area_hectares,
                        array_remove(array_agg(DISTINCT fe.province), NULL) AS provinces,
                        array_remove(array_agg(DISTINCT fe.status), NULL) AS statuses,
                        AVG(ST_Y(fe.centroid::geometry)) AS centroid_lat,
                        AVG(ST_X(fe.centroid::geometry)) AS centroid_lon,
                        MIN(ST_X(fe.centroid::geometry)) AS bbox_minx,
                        MIN(ST_Y(fe.centroid::geometry)) AS bbox_miny,
                        MAX(ST_X(fe.centroid::geometry)) AS bbox_maxx,
                        MAX(ST_Y(fe.centroid::geometry)) AS bbox_maxy
                    FROM fire_episode_events fee
                    JOIN fire_events fe ON fe.id = fee.event_id
                    WHERE fee.episode_id = :episode_id
                    """
                ),
                {"episode_id": str(episode_id)},
            )
            .mappings()
            .first()
        )

        if not row or row["event_count"] == 0:
            if existing_status == "closed":
                self.db.execute(
                    text(
                        """
                        UPDATE fire_episodes
                           SET event_count = 0,
                               detection_count = 0,
                               gee_candidate = false,
                               gee_priority = NULL,
                               requires_recalculation = false,
                               updated_at = NOW()
                         WHERE id = :episode_id
                        """
                    ),
                    {"episode_id": str(episode_id)},
                )
                return

            closed_end = (
                existing_end_date or existing_last_seen or datetime.now(timezone.utc)
            )
            closed_last_seen = existing_last_seen or existing_end_date or closed_end
            self.db.execute(
                text(
                    """
                    UPDATE fire_episodes
                       SET status = 'closed',
                           end_date = :end_date,
                           last_seen_at = :last_seen_at,
                           event_count = 0,
                           detection_count = 0,
                           gee_candidate = false,
                           gee_priority = NULL,
                           requires_recalculation = false,
                           updated_at = NOW()
                     WHERE id = :episode_id
                    """
                ),
                {
                    "episode_id": str(episode_id),
                    "end_date": closed_end,
                    "last_seen_at": closed_last_seen,
                },
            )
            return

        event_count = int(row["event_count"])
        detection_count = int(row["detection_count"] or 0)
        last_seen_at = row.get("last_seen_at") or row.get("start_date")
        if isinstance(last_seen_at, datetime):
            last_seen_at = self._ensure_tz(last_seen_at)
        else:
            last_seen_at = existing_last_seen or existing_end_date

        status_values = {
            str(value).lower()
            for value in (row.get("statuses") or [])
            if value is not None
        }

        if existing_status == "closed":
            status = "closed"
        else:
            grace_hours = self._resolve_inactive_grace_hours()
            status = self._resolve_episode_status(
                event_statuses=status_values,
                last_seen_at=last_seen_at,
                start_date=row["start_date"],
                window_hours=grace_hours,
            )

        gee_candidate = event_count >= min_points
        gee_priority = detection_count if gee_candidate else None
        if status == "closed":
            gee_candidate = False
            gee_priority = None

        end_date_value: Optional[datetime]
        if status == "closed":
            end_date_value = (
                existing_end_date or last_seen_at or datetime.now(timezone.utc)
            )
        else:
            end_date_value = None

        # Seteo automatico de extinct_at (T-04):
        # - Transicion a 'extinct': registrar el timestamp si no estaba ya extinot
        # - Reactivacion a 'active' o 'monitoring': limpiar extinct_at
        # - Ya era 'extinct': preservar el valor original (no sobreescribir)
        if status == "extinct" and existing_status != "extinct":
            extinct_at_value: Optional[datetime] = datetime.now(timezone.utc)
        elif status in ("active", "monitoring"):
            extinct_at_value = None
        else:
            extinct_at_value = existing_extinct_at

        self.db.execute(
            text(
                """
                UPDATE fire_episodes
                   SET start_date = :start_date,
                       end_date = :end_date,
                       last_seen_at = :last_seen_at,
                       centroid_lat = :centroid_lat,
                       centroid_lon = :centroid_lon,
                       bbox_minx = :bbox_minx,
                       bbox_miny = :bbox_miny,
                       bbox_maxx = :bbox_maxx,
                       bbox_maxy = :bbox_maxy,
                       provinces = :provinces,
                       event_count = :event_count,
                       detection_count = :detection_count,
                       frp_sum = :frp_sum,
                       frp_max = :frp_max,
                       estimated_area_hectares = :estimated_area_hectares,
                       status = :status,
                       extinct_at = :extinct_at,
                       gee_candidate = :gee_candidate,
                       gee_priority = :gee_priority,
                       clustering_version_id = :clustering_version_id,
                       requires_recalculation = false,
                       updated_at = NOW()
                 WHERE id = :episode_id
                """
            ),
            {
                "episode_id": str(episode_id),
                "start_date": row["start_date"],
                "end_date": end_date_value,
                "last_seen_at": last_seen_at,
                "centroid_lat": row["centroid_lat"],
                "centroid_lon": row["centroid_lon"],
                "bbox_minx": row["bbox_minx"],
                "bbox_miny": row["bbox_miny"],
                "bbox_maxx": row["bbox_maxx"],
                "bbox_maxy": row["bbox_maxy"],
                "provinces": row["provinces"],
                "event_count": event_count,
                "detection_count": detection_count,
                "frp_sum": row["frp_sum"],
                "frp_max": row["frp_max"],
                "estimated_area_hectares": row["estimated_area_hectares"],
                "status": status,
                "extinct_at": extinct_at_value,
                "gee_candidate": gee_candidate,
                "gee_priority": gee_priority,
                "clustering_version_id": str(clustering_version_id),
            },
        )

        logger.info(
            "Updated episode %s metrics (events=%s, detections=%s)",
            episode_id,
            event_count,
            detection_count,
        )
