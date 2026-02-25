"""
Episode closer task (DT-001 / EVT-006).

Transiciona episodios de 'extinct' a 'closed' cuando ya pasaron 30 dias
desde que se extinguieron (extinct_at + 30d < NOW()).

Al cerrar el episodio:
  - status = 'closed'
  - slides_data = '[]'  (DT-001: limpiar slides stale para evitar URLs rotas)

Schedule: 05:00 UTC diario, despues del carousel (03:00) y cleanup (04:00).
Cola: analysis
"""

import logging
import os

from app.db.session import SessionLocal
from sqlalchemy import text
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

CLOSE_AFTER_DAYS = int(os.environ.get("EPISODE_CLOSE_AFTER_DAYS", "30"))


@celery_app.task(
    bind=True,
    name="workers.tasks.episode_closer_task.close_extinct_episodes",
    queue="analysis",
    max_retries=2,
    retry_backoff=True,
)
def close_extinct_episodes(self):
    """
    Cierra episodios extintos que superaron la ventana de gracia.

    Criterios:
      - status = 'extinct'
      - extinct_at IS NOT NULL
      - extinct_at < NOW() - INTERVAL '{CLOSE_AFTER_DAYS} days'

    Acciones:
      - status = 'closed'
      - slides_data = '[]'   (DT-001: limpiar URLs stale)
      - updated_at = NOW()
    """
    db = SessionLocal()
    try:
        result = db.execute(
            text(f"""
                UPDATE fire_episodes
                   SET status = 'closed',
                       slides_data = '[]'::jsonb,
                       updated_at = NOW()
                 WHERE status = 'extinct'
                   AND extinct_at IS NOT NULL
                   AND extinct_at < NOW() - INTERVAL '{CLOSE_AFTER_DAYS} days'
            """)
        )
        closed_count = result.rowcount
        db.commit()
        logger.info(
            "episode_closer: closed %d episodes (extinct_at > %d days ago)",
            closed_count,
            CLOSE_AFTER_DAYS,
        )
        return {"closed": closed_count, "close_after_days": CLOSE_AFTER_DAYS}
    except Exception as exc:
        db.rollback()
        logger.error("episode_closer failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        db.close()
