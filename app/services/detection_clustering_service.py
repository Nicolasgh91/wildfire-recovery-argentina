from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional
from uuid import UUID

import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

EARTH_RADIUS_METERS = 6371000.0

try:
    import h3  # type: ignore

    H3_AVAILABLE = True
except ImportError:
    h3 = None
    H3_AVAILABLE = False


@dataclass(frozen=True)
class ClusteringVersion:
    """Clustering parameters loaded from the database."""
    id: UUID
    epsilon_km: float
    min_points: int
    temporal_window_hours: int
    algorithm: str


@dataclass(frozen=True)
class DetectionRow:
    """Minimal detection payload for clustering."""
    id: UUID
    detected_at: datetime
    lat: float
    lon: float
    frp: float
    confidence: Optional[float]


def _ensure_tz(value: datetime) -> datetime:
    """Ensure datetime values are timezone-aware (UTC)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute distance between two coordinates in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _compute_h3_index(lat: float, lon: float, resolution: int) -> Optional[int]:
    """Compute H3 index if the library is available."""
    if not H3_AVAILABLE:
        return None
    if hasattr(h3, "latlng_to_cell"):
        cell = h3.latlng_to_cell(lat, lon, resolution)
    else:
        cell = h3.geo_to_h3(lat, lon, resolution)
    return int(cell, 16)


class DetectionClusteringService:
    """Service for clustering detections into fire events."""
    def __init__(self, db: Session):
        self.db = db

    def _get_fire_event_columns(self) -> set[str]:
        rows = self.db.execute(
            text(
                """
                SELECT column_name
                  FROM information_schema.columns
                 WHERE table_schema = 'public'
                   AND table_name = 'fire_events'
                """
            )
        ).fetchall()
        return {row[0] for row in rows}

    def _get_active_version(self) -> ClusteringVersion:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT id, epsilon_km, min_points, temporal_window_hours, algorithm
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
            algorithm=row.get("algorithm") or "",
        )

    def _resolve_h3_resolution(self, default: int = 8) -> int:
        env_value = os.getenv("H3_RESOLUTION")
        if env_value:
            try:
                return int(env_value)
            except (TypeError, ValueError):
                logger.warning("H3_RESOLUTION invalido: %s", env_value)

        row = (
            self.db.execute(
                text(
                    "SELECT param_value FROM system_parameters WHERE param_key = 'h3_resolution'"
                )
            )
            .mappings()
            .first()
        )
        if not row:
            return default
        value = row.get("param_value")
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, (int, float, str)):
            try:
                return int(value)
            except (TypeError, ValueError):
                return default
        return default

    def _fetch_pending_detections(
        self,
        *,
        since: datetime,
        max_detections: Optional[int] = None,
    ) -> List[DetectionRow]:
        limit_clause = ""
        params: dict[str, object] = {"since": since}
        if max_detections:
            limit_clause = "LIMIT :limit"
            params["limit"] = int(max_detections)

        rows = (
            self.db.execute(
                text(
                    f"""
                    SELECT id,
                           detected_at,
                           latitude,
                           longitude,
                           fire_radiative_power,
                           confidence_normalized
                      FROM fire_detections
                     WHERE fire_event_id IS NULL
                       AND (is_processed = false OR is_processed IS NULL)
                       AND detected_at >= :since
                       AND (confidence_normalized IS NULL OR confidence_normalized >= 50)
                  ORDER BY detected_at ASC
                  {limit_clause}
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )

        detections: List[DetectionRow] = []
        for row in rows:
            detected_at = _ensure_tz(row["detected_at"])
            detections.append(
                DetectionRow(
                    id=row["id"],
                    detected_at=detected_at,
                    lat=float(row["latitude"]),
                    lon=float(row["longitude"]),
                    frp=float(row.get("fire_radiative_power") or 0.0),
                    confidence=(
                        float(row["confidence_normalized"])
                        if row.get("confidence_normalized") is not None
                        else None
                    ),
                )
            )

        return detections

    @staticmethod
    def _cluster_labels(
        detections: List[DetectionRow],
        *,
        eps_meters: float,
        temporal_window_hours: int,
        min_points: int,
    ) -> np.ndarray:
        if not detections:
            return np.array([], dtype=int)

        time_window_seconds = max(temporal_window_hours, 1) * 3600.0
        coords = np.array(
            [
                [
                    det.lat,
                    det.lon,
                    det.detected_at.timestamp(),
                ]
                for det in detections
            ],
            dtype=float,
        )

        def st_distance(a: np.ndarray, b: np.ndarray) -> float:
            spatial = _haversine_m(a[0], a[1], b[0], b[1])
            time_diff = abs(a[2] - b[2])
            time_scaled = (time_diff / time_window_seconds) * eps_meters
            return max(spatial, time_scaled)

        clustering = DBSCAN(
            eps=eps_meters,
            min_samples=min_points,
            metric=st_distance,
            n_jobs=1,
        )
        return clustering.fit_predict(coords)

    def _insert_event(
        self,
        *,
        cluster: List[DetectionRow],
        clustering_version_id: UUID,
        supports_h3: bool,
        supports_version: bool,
        h3_resolution: int,
    ) -> UUID:
        lats = [det.lat for det in cluster]
        lons = [det.lon for det in cluster]
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)

        detected_times = [det.detected_at for det in cluster]
        start_date = min(detected_times)
        end_date = max(detected_times)

        frp_values = [det.frp for det in cluster if det.frp is not None]
        avg_frp = sum(frp_values) / len(frp_values) if frp_values else 0.0
        max_frp = max(frp_values) if frp_values else 0.0
        sum_frp = sum(frp_values) if frp_values else 0.0

        conf_values = [det.confidence for det in cluster if det.confidence is not None]
        avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0

        is_significant = (max_frp > 50) or (avg_conf > 80)

        columns = [
            "id",
            "centroid",
            "start_date",
            "end_date",
            "total_detections",
            "avg_frp",
            "max_frp",
            "sum_frp",
            "avg_confidence",
            "is_significant",
            "status",
            "created_at",
            "updated_at",
        ]
        values = [
            "gen_random_uuid()",
            "ST_GeomFromText(:centroid_wkt, 4326)::geography",
            ":start_date",
            ":end_date",
            ":total_detections",
            ":avg_frp",
            ":max_frp",
            ":sum_frp",
            ":avg_confidence",
            ":is_significant",
            "'active'",
            "NOW()",
            "NOW()",
        ]

        payload = {
            "centroid_wkt": f"POINT({centroid_lon} {centroid_lat})",
            "start_date": start_date,
            "end_date": end_date,
            "total_detections": len(cluster),
            "avg_frp": round(avg_frp, 2),
            "max_frp": round(max_frp, 2),
            "sum_frp": round(sum_frp, 2),
            "avg_confidence": round(avg_conf, 2),
            "is_significant": is_significant,
        }

        if supports_h3:
            h3_index = _compute_h3_index(centroid_lat, centroid_lon, h3_resolution)
            columns.append("h3_index")
            values.append(":h3_index")
            payload["h3_index"] = h3_index

        if supports_version:
            columns.append("clustering_version_id")
            values.append(":clustering_version_id")
            payload["clustering_version_id"] = str(clustering_version_id)

        insert_sql = text(
            f"""
            INSERT INTO fire_events (
                {", ".join(columns)}
            ) VALUES (
                {", ".join(values)}
            )
            RETURNING id
            """
        )

        return self.db.execute(insert_sql, payload).scalar()

    def run_clustering(
        self,
        *,
        days_back: int = 1,
        max_detections: Optional[int] = None,
    ) -> dict:
        version = self._get_active_version()
        if version.algorithm and version.algorithm != "ST-DBSCAN":
            logger.warning(
                "Active clustering_version.algorithm=%s, expected ST-DBSCAN. Continuing with ST-DBSCAN rules.",
                version.algorithm,
            )

        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        detections = self._fetch_pending_detections(
            since=since, max_detections=max_detections
        )
        if not detections:
            return {"events_created": 0, "detections_processed": 0, "noise": 0}

        eps_meters = version.epsilon_km * 1000.0
        labels = self._cluster_labels(
            detections,
            eps_meters=eps_meters,
            temporal_window_hours=version.temporal_window_hours,
            min_points=version.min_points,
        )

        columns = self._get_fire_event_columns()
        supports_h3 = "h3_index" in columns
        h3_resolution = self._resolve_h3_resolution() if supports_h3 else 8
        supports_version = "clustering_version_id" in columns

        clusters: dict[int, List[DetectionRow]] = {}
        noise_ids: List[UUID] = []
        for det, label in zip(detections, labels):
            if label == -1:
                noise_ids.append(det.id)
                continue
            clusters.setdefault(int(label), []).append(det)

        events_created = 0
        detections_processed = 0

        for cluster in clusters.values():
            event_id = self._insert_event(
                cluster=cluster,
                clustering_version_id=version.id,
                supports_h3=supports_h3,
                supports_version=supports_version,
                h3_resolution=h3_resolution,
            )

            self.db.execute(
                text(
                    """
                    UPDATE fire_detections
                       SET fire_event_id = :event_id,
                           is_processed = true
                     WHERE id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"event_id": str(event_id), "ids": [str(det.id) for det in cluster]},
            )

            events_created += 1
            detections_processed += len(cluster)

        if noise_ids:
            self.db.execute(
                text(
                    """
                    UPDATE fire_detections
                       SET is_processed = true
                     WHERE id IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": [str(did) for did in noise_ids]},
            )

        return {
            "events_created": events_created,
            "detections_processed": detections_processed,
            "noise": len(noise_ids),
        }
