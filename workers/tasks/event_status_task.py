"""
Event status lifecycle task (EVT-001).

Persiste las transiciones de estado de fire_events:
  active    (dias 0-7 desde last_seen_at)
  monitoring (dias 7-14, ventana de evaluacion espacial)
  extinct   (sin deteccion en <=2km durante la ventana 7-14d)

Debe ejecutarse a las 01:30 UTC, despues de cluster_detections (01:00)
y antes de enrich_recent_fire_events (01:45) y cluster_fire_episodes (02:00).

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md (EVT-001)
"""

import logging
import time

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.episode_flow_parameters import load_canonical_episode_flow_parameters
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.event_status_task.update_event_statuses",
    queue="clustering",
    max_retries=3,
)
def update_event_statuses(self):
    """
    Persiste las transiciones de estado de fire_events.

    Reglas (en orden de ejecucion):
      1. active -> monitoring  si last_seen_at + 7d < NOW  (temporal)
      2. monitoring -> extinct si last_seen_at + 14d < NOW  (temporal)
                              Y no hay detecciones en <=2km tras last_seen_at (espacial)

    reference_time = COALESCE(last_seen_at, end_date, start_date)
    Parametros:
      event_monitoring_window_hours  = 168  (7d: umbral active->monitoring)
      event_extinction_window_hours  = 336  (14d: umbral monitoring->extinct)
    """
    t0 = time.monotonic()
    db = SessionLocal()
    try:
        params = load_canonical_episode_flow_parameters(db)
        active_window = int(params.get("event_monitoring_window_hours", 168))
        extinct_window = int(params.get("event_extinction_window_hours", 336))

        # Paso 1: active -> monitoring (criterio temporal puro, 7 dias)
        r_monitoring = db.execute(
            text("""
                UPDATE fire_events
                   SET status = 'monitoring',
                       updated_at = NOW()
                 WHERE status = 'active'
                   AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
                   AND COALESCE(last_seen_at, end_date, start_date)
                       < NOW() - MAKE_INTERVAL(hours => :active_window)
            """),
            {"active_window": active_window},
        )

        # Paso 2: monitoring -> extinct (criterio temporal + espacial, 14 dias)
        # NOT EXISTS verifica ausencia de cualquier fire_detection en <=2km
        # aparecida DESPUES de last_seen_at. Si existe alguna, el evento fue
        # reactivado por cluster_detections y no debe marcarse extinct.
        r_extinct = db.execute(
            text("""
                UPDATE fire_events
                   SET status = 'extinct',
                       updated_at = NOW()
                 WHERE id IN (
                     SELECT fe.id
                       FROM fire_events fe
                      WHERE fe.status = 'monitoring'
                        AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
                        AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                            < NOW() - MAKE_INTERVAL(hours => :extinct_window)
                        AND NOT EXISTS (
                            SELECT 1
                              FROM fire_detections fd
                             WHERE ST_DWithin(
                                       fd.location::geography,
                                       fe.centroid,
                                       2000
                                   )
                               AND fd.detected_at
                                   > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                        )
                 )
            """),
            {"extinct_window": extinct_window},
        )

        db.commit()

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        result = {
            "success": True,
            "to_monitoring": r_monitoring.rowcount,
            "to_extinct": r_extinct.rowcount,
            "active_window_hours": active_window,
            "extinct_window_hours": extinct_window,
            "elapsed_ms": elapsed_ms,
        }
        logger.info("Event status update complete: %s", result)
        return result

    except Exception as exc:
        db.rollback()
        logger.exception("Event status update failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
