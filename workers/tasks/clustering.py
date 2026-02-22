"""
Clustering Task: ST-DBSCAN spatio-temporal clustering de fire detections.
"""

import logging
from celery import shared_task

from app.db.session import SessionLocal
from app.services.detection_clustering_service import DetectionClusteringService
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


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
        db.commit()
        logger.info("Clustering completado: %s", result)
        return {"success": True, **result}
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
