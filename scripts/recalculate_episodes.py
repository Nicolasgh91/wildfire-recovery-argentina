#!/usr/bin/env python
"""
Recalculate episode metrics and trigger imagery carousel recreation.
Usage:
    export PYTHONPATH=.
    python scripts/recalculate_episodes.py
"""
import logging
from uuid import uuid4
import sys

from app.db.session import SessionLocal
from app.services.episode_service import EpisodeService
from app.services.imagery_service import ImageryService
from app.models.episode import FireEpisode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("recalculate_episodes")

def main():
    db = SessionLocal()
    try:
        episode_svc = EpisodeService(db)
        imagery_svc = ImageryService(db)
        
        episodes = db.query(FireEpisode).filter(
            FireEpisode.status.in_(["active", "monitoring", "extinct", "closed"])
        ).all()
        
        logger.info(f"Found {len(episodes)} episodes to recalculate.")
        
        dummy_clustering_id = uuid4()
        updated_count = 0
        
        for ep in episodes:
            logger.info(f"Recalculating episode {ep.id}...")
            try:
                episode_svc.update_episode_metrics(
                    ep.id,
                    clustering_version_id=dummy_clustering_id,
                    min_points=1,
                )
                updated_count += 1
            except Exception as ev_exc:
                logger.error(f"Failed to recalculate metrics for {ep.id}: {ev_exc}")
            
        db.commit()
        logger.info(f"Successfully recalculated metrics for {updated_count} episodes. Triggering carousel refresh...")
        
        result = imagery_svc.run_carousel(force_refresh=True)
        logger.info(f"Carousel refresh result: {result}")
        
    except Exception as exc:
        logger.error(f"Error during recalculation: {exc}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
