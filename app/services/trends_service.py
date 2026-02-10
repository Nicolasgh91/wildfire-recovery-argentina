from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.schemas.analysis import TrendPoint, TrendProjection, TrendsResponse

logger = logging.getLogger(__name__)

PROJECTION_PERIODS = 3
INTERVAL_MARGIN = 0.2


class TrendsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _choose_granularity(date_from: date, date_to: date) -> str:
        if (date_to - date_from).days > 90:
            return "month"
        return "day"

    @staticmethod
    def _trend_from_series(values: List[int]) -> Tuple[str, float]:
        if len(values) < 2:
            return "stable", 0.0

        n = len(values)
        x_values = list(range(n))
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return "stable", 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        avg = sum_y / n if n else 0
        rate_pct = (slope / avg * 100) if avg else 0.0

        if rate_pct > 5:
            direction = "increasing"
        elif rate_pct < -5:
            direction = "decreasing"
        else:
            direction = "stable"

        return direction, round(rate_pct, 2)

    @staticmethod
    def _annualize_rate(rate_pct: float, granularity: str) -> float:
        if granularity == "month":
            return round(rate_pct * 12, 2)
        return round(rate_pct * 365, 2)

    @staticmethod
    def _next_period(current: date, granularity: str) -> date:
        if granularity == "month":
            year = current.year + (1 if current.month == 12 else 0)
            month = 1 if current.month == 12 else current.month + 1
            return date(year, month, 1)
        return current + timedelta(days=1)

    def _query_series(
        self,
        date_from: date,
        date_to: date,
        granularity: str,
        bbox: Optional[Dict[str, float]],
    ) -> List[dict]:
        bbox_filter = ""
        params: Dict[str, object] = {
            "date_from": date_from,
            "date_to": date_to,
        }
        if bbox:
            bbox_filter = (
                "AND ST_X(centroid::geometry) BETWEEN :min_lon AND :max_lon "
                "AND ST_Y(centroid::geometry) BETWEEN :min_lat AND :max_lat "
            )
            params.update(bbox)

        query = text(
            f"""
            SELECT
                date_trunc('{granularity}', start_date)::date AS period,
                COUNT(*) AS fire_count,
                COALESCE(SUM(estimated_area_hectares), 0) AS total_hectares
            FROM fire_events
            WHERE start_date >= :date_from
              AND start_date <= :date_to
              {bbox_filter}
            GROUP BY period
            ORDER BY period
            """
        )
        rows = self.db.execute(query, params).mappings().all()
        return [dict(row) for row in rows]

    def get_trends(
        self,
        date_from: date,
        date_to: date,
        bbox: Optional[Dict[str, float]] = None,
    ) -> TrendsResponse:
        if date_to < date_from:
            raise ValueError("date_to must be >= date_from")

        granularity = self._choose_granularity(date_from, date_to)
        try:
            rows = self._query_series(date_from, date_to, granularity, bbox)
        except SQLAlchemyError as exc:
            logger.warning("trends query failed: %s", exc)
            self.db.rollback()
            rows = []

        series: List[TrendPoint] = []
        counts: List[int] = []
        total_fires = 0
        total_hectares = 0.0

        for row in rows:
            fire_count = int(row.get("fire_count") or 0)
            total = float(row.get("total_hectares") or 0.0)
            series.append(
                TrendPoint(
                    period=row["period"],
                    fire_count=fire_count,
                    total_hectares=total,
                )
            )
            counts.append(fire_count)
            total_fires += fire_count
            total_hectares += total

        trend_direction, period_change_rate = self._trend_from_series(counts)
        annual_rate = self._annualize_rate(period_change_rate, granularity)

        projections: Optional[List[TrendProjection]] = None
        if counts:
            avg_area_per_fire = total_hectares / total_fires if total_fires else 0.0
            projections = []
            last_period = series[-1].period if series else date_to
            last_value = counts[-1]
            slope = (period_change_rate / 100) * (last_value if last_value else 0)

            for _ in range(PROJECTION_PERIODS):
                next_period = self._next_period(last_period, granularity)
                projected = max(last_value + slope, 0.0)
                projected_area = projected * avg_area_per_fire
                projections.append(
                    TrendProjection(
                        period=next_period,
                        projected_fire_count=round(projected, 2),
                        projected_total_hectares=round(projected_area, 2),
                        confidence_interval_low=round(
                            projected * (1 - INTERVAL_MARGIN), 2
                        ),
                        confidence_interval_high=round(
                            projected * (1 + INTERVAL_MARGIN), 2
                        ),
                    )
                )
                last_period = next_period
                last_value = projected

        return TrendsResponse(
            granularity=granularity,
            period={"from": date_from, "to": date_to},
            bbox=bbox,
            series=series,
            trend_direction=trend_direction,
            period_change_rate_pct=period_change_rate,
            annual_change_rate_pct=annual_rate,
            projections=projections,
            total_fires=total_fires,
            total_hectares=round(total_hectares, 2),
        )
