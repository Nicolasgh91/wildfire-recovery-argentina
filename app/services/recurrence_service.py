from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.analysis import RecurrenceCell, RecurrenceResponse

logger = logging.getLogger(__name__)

DEFAULT_CELL_LIMIT = 5000


@dataclass(frozen=True)
class BBox:
    """Bounding box parameters for recurrence queries."""
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "min_lon": self.min_lon,
            "min_lat": self.min_lat,
            "max_lon": self.max_lon,
            "max_lat": self.max_lat,
        }


class RecurrenceService:
    """Service for H3 recurrence heatmap queries."""
    def __init__(self, db: Session):
        self.db = db

    def _system_param_value(self, key: str, fallback: int) -> int:
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
            self.db.rollback()
            return fallback

        if not row:
            return fallback

        value = row.get("param_value")
        if isinstance(value, dict):
            if "value" in value:
                try:
                    return int(value["value"])
                except (TypeError, ValueError):
                    return fallback
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback

    def _format_h3_index(self, value: Optional[int]) -> str:
        if value is None:
            return ""
        try:
            return format(int(value), "x")
        except (TypeError, ValueError):
            return str(value)

    def _count_cells(self, bbox: BBox) -> int:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT COUNT(DISTINCT h3_index) AS cell_count
                      FROM fire_events
                     WHERE h3_index IS NOT NULL
                       AND ST_X(centroid::geometry) BETWEEN :min_lon AND :max_lon
                       AND ST_Y(centroid::geometry) BETWEEN :min_lat AND :max_lat
                     LIMIT 1000
                    """
                ),
                bbox.as_dict(),
            )
            .mappings()
            .first()
        )
        return int(row["cell_count"] or 0) if row else 0

    def _query_cells_from_view(self, bbox: BBox) -> List[dict]:
        query = text(
            """
            WITH cells AS (
                SELECT DISTINCT h3_index
                  FROM fire_events
                 WHERE h3_index IS NOT NULL
                   AND ST_X(centroid::geometry) BETWEEN :min_lon AND :max_lon
                   AND ST_Y(centroid::geometry) BETWEEN :min_lat AND :max_lat
            )
            SELECT stats.h3_index,
                   stats.recurrence_score,
                   stats.recurrence_class,
                   stats.total_fires
              FROM h3_recurrence_stats stats
              JOIN cells ON cells.h3_index = stats.h3_index
             ORDER BY stats.recurrence_score DESC
            """
        )
        rows = self.db.execute(query, bbox.as_dict()).mappings().all()
        return [dict(row) for row in rows]

    def _query_cells_fallback(self, bbox: BBox) -> List[dict]:
        query = text(
            """
            SELECT
                h3_index,
                COUNT(*) AS total_fires,
                CASE
                    WHEN COUNT(*) >= 5 THEN 'high'
                    WHEN COUNT(*) >= 2 THEN 'medium'
                    ELSE 'low'
                END AS recurrence_class,
                LEAST(COUNT(*)::NUMERIC / 10.0, 1.0) AS recurrence_score
            FROM fire_events
            WHERE h3_index IS NOT NULL
              AND ST_X(centroid::geometry) BETWEEN :min_lon AND :max_lon
              AND ST_Y(centroid::geometry) BETWEEN :min_lat AND :max_lat
            GROUP BY h3_index
            ORDER BY recurrence_score DESC
            LIMIT 500
            """
        )
        rows = self.db.execute(query, bbox.as_dict()).mappings().all()
        return [dict(row) for row in rows]

    def get_recurrence(self, bbox: BBox) -> RecurrenceResponse:
        cell_limit = self._system_param_value(
            "h3_max_cells_per_query", DEFAULT_CELL_LIMIT
        )
        cell_count = self._count_cells(bbox)
        if cell_count > cell_limit:
            raise ValueError("Reduce zoom level or area")

        # Temporarily force fallback for performance testing
        logger.info("Using fallback query for performance testing")
        rows = self._query_cells_fallback(bbox)
        
        # Original code (commented for testing)
        # try:
        #     rows = self._query_cells_from_view(bbox)
        # except SQLAlchemyError as exc:
        #     logger.warning(
        #         "h3_recurrence_stats view unavailable, using fallback: %s", exc
        #     )
        #     self.db.rollback()
        #     rows = self._query_cells_fallback(bbox)

        cells: List[RecurrenceCell] = []
        max_intensity = 0.0
        for row in rows:
            intensity = float(row.get("recurrence_score") or 0.0)
            if intensity > max_intensity:
                max_intensity = intensity
            cells.append(
                RecurrenceCell(
                    h3=self._format_h3_index(row.get("h3_index")),
                    intensity=intensity,
                    recurrence_class=row.get("recurrence_class"),
                    total_fires=int(row.get("total_fires") or 0),
                )
            )

        return RecurrenceResponse(
            cells=cells,
            cell_count=len(cells),
            max_intensity=max_intensity,
            bbox=bbox.as_dict(),
        )
