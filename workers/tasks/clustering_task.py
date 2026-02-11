"""
Episode clustering task (UC-F13).
"""

import argparse
import json
import logging
from celery import shared_task

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.clustering_service import ClusteringService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


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
        logger.info("Episode clustering completed: %s", result)
        return {"success": True, **result}
    except Exception as exc:
        logger.exception("Episode clustering failed: %s", exc)
        db.rollback()
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


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
