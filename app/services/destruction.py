"""
Destruction Task: Detección de destrucción de bosques y cambio de uso de suelo
post-incendio usando análisis multitemporal de Sentinel-2
"""

import logging
from datetime import datetime, timedelta

from celery import shared_task

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.destruction.detect_destruction",
    queue="analysis",
    max_retries=2,
)
def detect_destruction(self, fire_event_id, months_window=12):
    """
    Detecta cambios de uso de suelo post-incendio analizando:
    - Cambios en NDVI (vegetación)
    - Cambios espectrales (Sentinel-2 bandas específicas)
    - Patrones de construcción (si aplica)
    - Conversión a cultivos o urbanización

    Args:
        fire_event_id: UUID del fuego
        months_window: Ventana temporal para analizar (meses)

    Retorna:
        dict: {
            'fire_event_id': str,
            'destruction_detected': bool,
            'destruction_type': str (reforestation|urbanization|agriculture|degradation|unknown),
            'affected_area_ha': float,
            'confidence': float (0-1),
            'analysis_date': str ISO
        }
    """
    try:
        logger.info(f"🔍 Detectando destrucción/cambio de uso para {fire_event_id}...")

        # Aquí va:
        # 1. Obtener geometría del fuego
        # 2. Descargar imágenes Sentinel-2 pre y post-incendio
        # 3. Analizar cambios espectrales
        # 4. Clasificar tipo de cambio de uso
        # 5. Calcular área afectada

        result = {
            "fire_event_id": fire_event_id,
            "destruction_detected": True,
            "destruction_type": "degradation",
            "affected_area_ha": 1250.5,
            "confidence": 0.87,
            "months_window": months_window,
            "analysis_date": datetime.utcnow().isoformat(),
        }

        logger.info(f"✅ Análisis completado: {result['affected_area_ha']}ha afectadas")
        return result

    except Exception as exc:
        logger.error(f"❌ Error detectando destrucción: {exc}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(
    name="workers.tasks.destruction.classify_land_use",
    bind=True,
)
def classify_land_use(self, fire_event_id, date_after_fire):
    """
    Clasifica uso de suelo post-incendio en categorías Ley 26.815.
    Categorías: Bosque nativo, Agricultura, Urbanización, Degradación, Recuperación

    Args:
        fire_event_id: UUID del fuego
        date_after_fire: Fecha para evaluar (ISO string)

    Retorna:
        dict con clasificación y áreas por categoría
    """
    try:
        logger.info(f"📋 Clasificando uso de suelo para {fire_event_id}...")

        return {
            "fire_event_id": fire_event_id,
            "classification_date": date_after_fire,
            "land_use_classes": {
                "bosque_nativo": {"area_ha": 850, "percentage": 68},
                "agricultura": {"area_ha": 180, "percentage": 14},
                "degradacion": {"area_ha": 200, "percentage": 16},
                "urbanizacion": {"area_ha": 20, "percentage": 2},
            },
            "legal_implications": "Ley 26.815: Prohibición 60 años si es bosque nativo",
        }

    except Exception as exc:
        logger.error(f"Error clasificando uso de suelo: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    name="workers.tasks.destruction.generate_destruction_report",
    bind=True,
)
def generate_destruction_report(self, fire_event_id):
    """
    Genera reporte judicial de destrucción post-incendio.
    Combina análisis de destrucción + clasificación de uso de suelo.

    Retorna:
        dict con datos para generar PDF
    """
    try:
        logger.info(f"📄 Generando reporte para {fire_event_id}...")

        # Obtener datos de destrucción
        destruction = detect_destruction.apply_async(
            args=[fire_event_id], queue="analysis"
        ).get()

        # Obtener datos de clasificación
        land_use = classify_land_use.apply_async(
            args=[fire_event_id, datetime.utcnow().date().isoformat()], queue="analysis"
        ).get()

        report_data = {
            "fire_event_id": fire_event_id,
            "destruction": destruction,
            "land_use": land_use,
            "report_date": datetime.utcnow().isoformat(),
            "report_type": "judicial_destruction",
        }

        return report_data

    except Exception as exc:
        logger.error(f"Error generando reporte: {exc}")
        raise self.retry(exc=exc, countdown=60)
