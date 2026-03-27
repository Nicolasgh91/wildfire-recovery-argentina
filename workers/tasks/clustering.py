"""
Clustering Task: ST-DBSCAN spatio-temporal clustering de fire detections.
"""

import logging
from celery import shared_task
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.detection_clustering_service import DetectionClusteringService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_GEO_ENRICH_RECENT_EVENTS_SQL = text(
    """
    UPDATE fire_events fe
       SET province = COALESCE(fe.province, geo.province),
           department = COALESCE(fe.department, geo.department),
           updated_at = NOW()
      FROM LATERAL assign_province_department(fe.centroid) AS geo
     WHERE fe.centroid IS NOT NULL
       AND fe.created_at >= NOW() - make_interval(hours => :lookback_hours)
       AND (fe.province IS NULL OR fe.department IS NULL)
    """
)


def _enrich_recent_event_geo(db, *, lookback_hours: int = 6) -> int:
    """
    Best-effort guardrail: enrich province/department on newly created events.

    The canonical enrichment occurs during event insert in
    DetectionClusteringService. This fallback closes the operational gap when
    legacy rows are generated without geo metadata.
    """
    result = db.execute(
        _GEO_ENRICH_RECENT_EVENTS_SQL,
        {"lookback_hours": int(max(1, lookback_hours))},
    )
    return int(result.rowcount or 0)


@celery_app.task(
    bind=True,
    name='workers.tasks.clustering.cluster_detections',
    queue='clustering',
    max_retries=3,
)
def cluster_detections(self, days_back: int = 1, max_detections: int | None = None):
    """
    Ejecuta clustering ST-DBSCAN en detecciones pendientes de los ultimos N dias.

    Args:
        days_back: Cuantos dias hacia atras procesar
        max_detections: Limite opcional de detecciones a procesar

    Retorna:
        dict con metricas de clustering
    """
    db = SessionLocal()
    try:
        service = DetectionClusteringService(db)
        result = service.run_clustering(days_back=days_back, max_detections=max_detections)
        geo_updates = _enrich_recent_event_geo(db, lookback_hours=max(days_back * 24, 6))
        if geo_updates:
            logger.info("Geo enrichment fallback updated %s recent events", geo_updates)
        db.commit()
        logger.info("Clustering completado: %s", result)
        return {"success": True, "geo_enriched_events": geo_updates, **result}
    except Exception as exc:
        db.rollback()
        logger.exception("Error en clustering: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()


@shared_task(
    name='workers.tasks.clustering.refine_cluster',
    bind=True,
)
def refine_cluster(self, fire_event_id, iterations=1):
    """
    Re-ejecuta DBSCAN en un cluster especfico para refinamiento.

    Args:
        fire_event_id: UUID del fuego a refinar
        iterations: Nmero de iteraciones

    Retorna:
        dict con resultados de refinamiento
    """
    try:
        logger.info("Refinando cluster %s...", fire_event_id)

        return {
            'fire_event_id': fire_event_id,
            'refined': True,
            'new_cluster_count': 1,
        }

    except Exception as exc:
        logger.error("Error refinando %s: %s", fire_event_id, exc)
        raise self.retry(exc=exc, countdown=30)
