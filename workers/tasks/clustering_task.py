"""
Episode clustering task (UC-F13).
"""

import argparse
import json
import logging
from celery import chain, shared_task

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.clustering_service import ClusteringService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_PROPAGATE_EPISODE_PROVINCES_SQL = text(
    """
    UPDATE fire_episodes ep
       SET provinces = sub.province_list,
           updated_at = NOW()
      FROM (
        SELECT
            fee.episode_id,
            ARRAY_AGG(DISTINCT fe.province)
                FILTER (WHERE fe.province IS NOT NULL) AS province_list
        FROM fire_episode_events fee
        JOIN fire_events fe ON fe.id = fee.event_id
        GROUP BY fee.episode_id
      ) sub
     WHERE ep.id = sub.episode_id
       AND (
            ep.provinces IS NULL
            OR ep.provinces = '{}'
            OR ep.provinces <> sub.province_list
       )
    """
)


def _propagate_episode_provinces(db) -> int:
    """Ensure fire_episodes.provinces reflects linked fire_events.province."""
    result = db.execute(_PROPAGATE_EPISODE_PROVINCES_SQL)
    return int(result.rowcount or 0)


@celery_app.task(
    bind=True,
    name="workers.tasks.clustering_task.cluster_fire_episodes",
    queue="clustering",
    max_retries=3,
)
def cluster_fire_episodes(self, days_back: int = 90, max_events: int = 5000):
    """
    Cluster fire_events into fire_episodes using spatio-temporal rules.
    """
    db = SessionLocal()
    try:
        service = ClusteringService(db)
        result = service.run_clustering(days_back=days_back, max_events=max_events)
        provinces_synced = _propagate_episode_provinces(db)
        if provinces_synced:
            logger.info("Synced provinces array for %s episodes", provinces_synced)
        logger.info("Episode clustering completed: %s", result)

        # DT-002: si se crearon episodios nuevos, encolar carousel inmediatamente
        # en vez de esperar al beat diario de las 03:00 UTC (hasta 25h de delay).
        if result.get("episodes_created", 0) > 0:
            from workers.tasks.carousel_task import generate_carousel

            generate_carousel.apply_async(queue="analysis")
            logger.info(
                "DT-002: %d new episodes created, enqueued carousel immediately.",
                result["episodes_created"],
            )

        return {"success": True, "provinces_synced": provinces_synced, **result}
    except Exception as exc:
        logger.exception("Episode clustering failed: %s", exc)
        db.rollback()
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="workers.tasks.clustering_task.cluster_fire_episodes_pipeline",
    queue="clustering",
    max_retries=3,
)
def cluster_fire_episodes_pipeline(
    self,
    days_back: int = 90,
    max_events: int = 5000,
):
    """
    Enqueue episode clustering pipeline using Celery canvas.

    Chain:
      1) cluster_fire_episodes

    Nota: el geo-enrichment (province + áreas protegidas) fue movido a un
    beat entry independiente a las 01:45 UTC (enrich-events-daily), que corre
    antes que este pipeline (02:00 UTC). Así los episodios leen eventos ya
    enriquecidos desde el primer momento.
    """
    workflow = chain(
        cluster_fire_episodes.s(days_back=days_back, max_events=max_events),
    )
    async_result = workflow.apply_async()
    return {
        "success": True,
        "workflow_id": async_result.id,
        "days_back": days_back,
        "max_events": max_events,
    }


@shared_task(name="workers.tasks.clustering_task.recluster_episode", bind=True)
def recluster_episode(self, episode_id: str):
    """
    Force re-clustering for a specific episode by flagging it for recalculation.
    """
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE fire_episodes SET requires_recalculation = true WHERE id = :id"),
            {"id": episode_id},
        )
        db.commit()
        return {"episode_id": episode_id, "flagged": True}
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to flag episode %s: %s", episode_id, exc)
        raise
    finally:
        db.close()


def _run_cli() -> int:
    parser = argparse.ArgumentParser(description="Cluster fire episodes (dry-run supported).")
    parser.add_argument("--dry-run", action="store_true", help="Run without committing changes.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--days-back", type=int, default=90, help="Days back window.")
    parser.add_argument("--max-events", type=int, default=5000, help="Max events to process.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    db = SessionLocal()
    try:
        service = ClusteringService(db)
        result = service.run_clustering(
            days_back=args.days_back,
            max_events=args.max_events,
            dry_run=args.dry_run,
        )
        logger.info("Clustering CLI result: %s", result)
        print(json.dumps(result, default=str, ensure_ascii=True))
        return 0
    except Exception as exc:
        logger.exception("Clustering CLI failed: %s", exc)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(_run_cli())
