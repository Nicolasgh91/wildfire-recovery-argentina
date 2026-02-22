"""
Incremental geo-enrichment tasks for fire events.

Updates:
- province assignment from `regions` (category PROVINCIA)
- protected area intersections and legal-analysis markers
"""

from __future__ import annotations

import logging

from celery import shared_task
from sqlalchemy import bindparam, text

from app.db.session import SessionLocal
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _table_exists(db, table_name: str) -> bool:
    query = text(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = :table_name
        )
        """
    )
    return bool(db.execute(query, {"table_name": table_name}).scalar())


def _select_candidate_event_ids(db, lookback_hours: int, max_events: int) -> list[str]:
    query = text(
        """
        SELECT fe.id::text
        FROM fire_events fe
        WHERE fe.province IS NULL
           OR fe.has_legal_analysis = FALSE
           OR fe.has_legal_analysis IS NULL
           OR COALESCE(fe.last_seen_at, fe.updated_at, fe.start_date)
              >= NOW() AT TIME ZONE 'utc' - (:lookback_hours * INTERVAL '1 hour')
        ORDER BY COALESCE(fe.last_seen_at, fe.updated_at, fe.start_date) DESC NULLS LAST
        LIMIT :max_events
        """
    )
    rows = db.execute(
        query,
        {"lookback_hours": int(lookback_hours), "max_events": int(max_events)},
    ).fetchall()
    return [str(row[0]) for row in rows if row and row[0]]


def _update_missing_provinces(db, event_ids: list[str]) -> int:
    query = text(
        """
        UPDATE fire_events fe
        SET province = regions.name,
            updated_at = NOW()
        FROM regions
        WHERE fe.id::text IN :event_ids
          AND fe.province IS NULL
          AND regions.category = 'PROVINCIA'
          AND ST_Intersects(regions.geom, fe.centroid)
        """
    ).bindparams(bindparam("event_ids", expanding=True))
    result = db.execute(query, {"event_ids": event_ids})
    return int(result.rowcount or 0)


def _upsert_protected_area_intersections(db, event_ids: list[str]) -> int:
    query = text(
        """
        INSERT INTO fire_protected_area_intersections (
            id,
            fire_event_id,
            protected_area_id,
            fire_date,
            prohibition_until,
            overlap_percentage,
            created_at,
            updated_at
        )
        SELECT
            gen_random_uuid(),
            fe.id,
            pa.id,
            COALESCE(fe.start_date::date, CURRENT_DATE),
            (
                COALESCE(fe.start_date::date, CURRENT_DATE)
                + (pa.prohibition_years * INTERVAL '1 year')
            )::date,
            CASE
                WHEN ST_Intersects(pa.boundary::geometry, fe.centroid::geometry)
                THEN 100.0
                ELSE 50.0
            END,
            NOW(),
            NOW()
        FROM fire_events fe
        JOIN protected_areas pa
          ON ST_DWithin(pa.boundary::geography, fe.centroid::geography, 5000)
        WHERE fe.id::text IN :event_ids
          AND ST_Intersects(pa.boundary::geometry, fe.centroid::geometry)
        ON CONFLICT (fire_event_id, protected_area_id) DO UPDATE
          SET prohibition_until = EXCLUDED.prohibition_until,
              overlap_percentage = EXCLUDED.overlap_percentage,
              updated_at = NOW()
        RETURNING fire_event_id
        """
    ).bindparams(bindparam("event_ids", expanding=True))
    rows = db.execute(query, {"event_ids": event_ids}).fetchall()
    return len(rows)


def _mark_events_as_legally_analyzed(db, event_ids: list[str]) -> int:
    query = text(
        """
        UPDATE fire_events
        SET has_legal_analysis = TRUE,
            updated_at = NOW()
        WHERE id::text IN :event_ids
          AND COALESCE(has_legal_analysis, FALSE) = FALSE
        """
    ).bindparams(bindparam("event_ids", expanding=True))
    result = db.execute(query, {"event_ids": event_ids})
    return int(result.rowcount or 0)


@celery_app.task(
    bind=True,
    name="workers.tasks.geo_enrichment.enrich_recent_fire_events",
    queue="analysis",
    max_retries=3,
)
def enrich_recent_fire_events(
    self,
    lookback_hours: int = 72,
    max_events: int = 5000,
):
    """
    Incrementally enrich recent fire events with province and legal intersections.
    """
    db = SessionLocal()
    try:
        lookback_hours = max(1, int(lookback_hours))
        max_events = max(1, int(max_events))

        if not _table_exists(db, "fire_events"):
            return {
                "success": True,
                "skipped": True,
                "reason": "fire_events table missing",
                "candidate_events": 0,
                "province_updated": 0,
                "intersections_upserted": 0,
                "legal_analysis_marked": 0,
            }

        event_ids = _select_candidate_event_ids(db, lookback_hours, max_events)
        if not event_ids:
            return {
                "success": True,
                "skipped": False,
                "candidate_events": 0,
                "province_updated": 0,
                "intersections_upserted": 0,
                "legal_analysis_marked": 0,
            }

        province_updated = 0
        if _table_exists(db, "regions"):
            province_updated = _update_missing_provinces(db, event_ids)

        intersections_upserted = 0
        has_protected_tables = _table_exists(db, "protected_areas") and _table_exists(
            db, "fire_protected_area_intersections"
        )
        if has_protected_tables:
            intersections_upserted = _upsert_protected_area_intersections(db, event_ids)

        legal_analysis_marked = _mark_events_as_legally_analyzed(db, event_ids)
        db.commit()

        result = {
            "success": True,
            "skipped": False,
            "candidate_events": len(event_ids),
            "province_updated": province_updated,
            "intersections_upserted": intersections_upserted,
            "legal_analysis_marked": legal_analysis_marked,
            "lookback_hours": lookback_hours,
            "max_events": max_events,
        }
        logger.info(f"Geo enrichment completed: {result}")
        return result
    except Exception as exc:
        db.rollback()
        logger.exception("Geo enrichment failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


@shared_task(name="workers.tasks.geo_enrichment.ping", bind=True)
def ping(self):
    return {"ok": True}
