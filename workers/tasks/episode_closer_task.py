"""
Episode closer task (EVT-006).

Promueve fire_episodes de 'extinct' a 'closed' cuando extinct_at + 30d < NOW().
Los episodios 'closed' dejan de mostrarse en el carrusel/mapa y solo
aparecen en la grilla de historicos.

Schedule: 05:00 UTC diario (despues de cleanup 04:00, antes de reports 08:00).
Cola: analysis (worker-analysis).

Prerequisitos:
  - fire_episodes.extinct_at (EVT-007 migration)
  - FireStatus.CLOSED en app/schemas/fire.py (EVT-007)

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md (EVT-006)
"""

import logging
import time

from sqlalchemy import text

from app.db.session import SessionLocal
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

CLOSE_AFTER_DAYS = 30


@celery_app.task(
    bind=True,
    name="workers.tasks.episode_closer_task.close_extinct_episodes",
    queue="analysis",
    max_retries=3,
)
def close_extinct_episodes(self):
    """
    Promueve episodios extinct -> closed cuando extinct_at + 30d < NOW().

    Solo actua sobre episodios con extinct_at NOT NULL (seteado por
    update_episode_metrics cuando el episodio transiciona a 'extinct').
    """
    t0 = time.monotonic()
    db = SessionLocal()
    try:
        result = db.execute(
            text(f"""
                UPDATE fire_episodes
                   SET status = 'closed',
                       updated_at = NOW()
                 WHERE status = 'extinct'
                   AND extinct_at IS NOT NULL
                   AND extinct_at < NOW() - INTERVAL '{CLOSE_AFTER_DAYS} days'
            """),
        )

        db.commit()

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        outcome = {
            "success": True,
            "episodes_closed": result.rowcount,
            "close_after_days": CLOSE_AFTER_DAYS,
            "elapsed_ms": elapsed_ms,
        }
        logger.info("Episode closer complete: %s", outcome)
        return outcome

    except Exception as exc:
        db.rollback()
        logger.exception("Episode closer failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
