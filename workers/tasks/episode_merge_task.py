"""
Episode merge task (UC-F13).
"""

import logging
from typing import Iterable, Optional

from celery import shared_task

from app.db.session import SessionLocal
from app.services.episode_service import EpisodeService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.episode_merge_task.merge_episodes",
    queue="clustering",
    max_retries=3,
)
def merge_episodes(
    self,
    absorbing_episode_id: str,
    absorbed_episode_ids: Iterable[str],
    reason: str = "manual_merge",
    notes: Optional[str] = None,
):
    """
    Merge one or more absorbed episodes into an absorbing episode.
    """
    absorbed_ids = list(absorbed_episode_ids)
    db = SessionLocal()
    try:
        service = EpisodeService(db)
        for absorbed_id in absorbed_ids:
            service.merge_episodes(
                absorbing_episode_id=absorbing_episode_id,
                absorbed_episode_id=absorbed_id,
                reason=reason,
                clustering_version_id=None,
                notes=notes,
            )
        db.commit()
        return {
            "absorbing_episode_id": absorbing_episode_id,
            "absorbed_episode_ids": absorbed_ids,
            "reason": reason,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Episode merge failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


@shared_task(name="workers.tasks.episode_merge_task.merge_two", bind=True)
def merge_two(self, absorbing_episode_id: str, absorbed_episode_id: str):
    return merge_episodes(
        absorbing_episode_id=absorbing_episode_id,
        absorbed_episode_ids=[absorbed_episode_id],
    )
