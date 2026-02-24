"""
Recovery Task: Monitoreo de recuperación de vegetación post-incendio.

Analyzes vegetation recovery using VAEService + GEE and persists
results to the vegetation_monitoring table with upsert semantics.
"""

import logging
from datetime import datetime, timedelta
from celery import group
from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.analyze_recovery',
    queue='vae',
    max_retries=2,
)
def analyze_recovery(self, fire_event_id, months_after=None):
    """
    Analiza recuperación de vegetación post-incendio usando NDVI.
    Persists results to vegetation_monitoring with upsert.

    Args:
        fire_event_id: UUID del fuego
        months_after: Cuántos meses después analizar (None = auto-detect)
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        logger.info(f"Analyzing recovery for fire {fire_event_id}...")

        # 1. Get fire event geometry
        fire_row = db.execute(
            text("""
                SELECT
                    id,
                    start_date,
                    ST_Y(centroid::geometry) as lat,
                    ST_X(centroid::geometry) as lon,
                    estimated_area_hectares
                FROM fire_events
                WHERE id = :fire_id
            """),
            {"fire_id": str(fire_event_id)},
        ).fetchone()

        if not fire_row:
            logger.warning(f"Fire event {fire_event_id} not found, skipping")
            return {"fire_event_id": str(fire_event_id), "status": "skipped", "reason": "not_found"}

        fire_date = fire_row.start_date
        fire_lat = fire_row.lat
        fire_lon = fire_row.lon

        # Auto-detect months_after from fire date
        if months_after is None:
            days_since = (datetime.utcnow().date() - fire_date.date()
                          if hasattr(fire_date, 'date') else
                          datetime.utcnow().date() - fire_date)
            months_after = max(1, days_since.days // 30)

        # 2. Run VAE analysis
        from app.services.vae_service import VAEService, GEEImageNotFoundError

        vae = VAEService()
        buffer = 0.01  # ~1km
        bbox = {
            "west": fire_lon - buffer,
            "south": fire_lat - buffer,
            "east": fire_lon + buffer,
            "north": fire_lat + buffer,
        }

        fire_date_obj = fire_date.date() if hasattr(fire_date, 'date') else fire_date

        try:
            analysis = vae.analyze_recovery(
                fire_event_id=str(fire_event_id),
                bbox=bbox,
                fire_date=fire_date_obj,
                baseline_ndvi=None,
            )
        except Exception as exc:
            logger.warning(f"GEE analysis failed for {fire_event_id}: {exc}")
            return {
                "fire_event_id": str(fire_event_id),
                "status": "gee_error",
                "error": str(exc),
            }

        # 3. Persist to vegetation_monitoring with upsert
        monitoring_date = analysis.analysis_date
        upsert_query = text("""
            INSERT INTO vegetation_monitoring (
                fire_event_id,
                monitoring_date,
                months_after_fire,
                ndvi_mean,
                ndvi_min,
                ndvi_max,
                baseline_ndvi,
                recovery_percentage,
                human_activity_detected,
                activity_type,
                classification_confidence,
                created_at,
                updated_at
            ) VALUES (
                :fire_event_id,
                :monitoring_date,
                :months_after_fire,
                :ndvi_mean,
                :ndvi_min,
                :ndvi_max,
                :baseline_ndvi,
                :recovery_percentage,
                :human_activity_detected,
                :activity_type,
                :classification_confidence,
                NOW(),
                NOW()
            )
            ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                ndvi_min = EXCLUDED.ndvi_min,
                ndvi_max = EXCLUDED.ndvi_max,
                baseline_ndvi = EXCLUDED.baseline_ndvi,
                recovery_percentage = EXCLUDED.recovery_percentage,
                human_activity_detected = EXCLUDED.human_activity_detected,
                activity_type = EXCLUDED.activity_type,
                classification_confidence = EXCLUDED.classification_confidence,
                updated_at = NOW()
        """)

        db.execute(upsert_query, {
            "fire_event_id": str(fire_event_id),
            "monitoring_date": monitoring_date,
            "months_after_fire": analysis.months_after_fire,
            "ndvi_mean": analysis.current_ndvi,
            "ndvi_min": None,
            "ndvi_max": None,
            "baseline_ndvi": analysis.baseline_ndvi,
            "recovery_percentage": analysis.recovery_percentage,
            "human_activity_detected": analysis.anomaly_detected,
            "activity_type": analysis.anomaly_type.value if analysis.anomaly_detected else None,
            "classification_confidence": analysis.anomaly_confidence if analysis.anomaly_detected else None,
        })
        db.commit()

        logger.info(
            f"Recovery analysis persisted for {fire_event_id}: "
            f"{analysis.recovery_percentage:.1f}% recovered"
        )
        return {
            "fire_event_id": str(fire_event_id),
            "status": "completed",
            "recovery_percentage": analysis.recovery_percentage,
            "ndvi_change": analysis.ndvi_change,
            "recovery_status": analysis.recovery_status.value,
            "months_after_fire": analysis.months_after_fire,
            "analysis_date": monitoring_date.isoformat(),
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"Error analyzing recovery for {fire_event_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name='workers.tasks.recovery.batch_recovery_analysis',
    queue='vae',
    max_retries=2,
)
def batch_recovery_analysis(self, fire_event_ids=None, max_events=50, months_list=None):
    """
    Ejecuta análisis de recuperación para eventos activos.

    Cuando fire_event_ids es None o vacío, consulta la BD para obtener
    los eventos activos más recientes (< 36 meses). Limita a max_events
    por ejecución para proteger la cuota GEE.

    Programada mensualmente vía Celery Beat.

    Args:
        fire_event_ids: Lista de UUIDs (opcional; si vacía, auto-query)
        max_events: Máximo de eventos a procesar por batch
        months_list: Not used (auto-detected per event), kept for compatibility
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    try:
        # If no IDs provided, query DB for active events
        if not fire_event_ids:
            db = SessionLocal()
            try:
                rows = db.execute(text("""
                    SELECT fe.id
                    FROM fire_events fe
                    WHERE fe.start_date > NOW() - INTERVAL '36 months'
                      AND fe.status IN ('active', 'monitoring', 'contained')
                      AND fe.centroid IS NOT NULL
                    ORDER BY fe.start_date DESC
                    LIMIT :max_events
                """), {"max_events": max_events}).fetchall()
                fire_event_ids = [str(row.id) for row in rows]
            finally:
                db.close()

        logger.info(f"Batch recovery analysis: {len(fire_event_ids)} fires...")

        signatures = [
            analyze_recovery.s(fire_id).set(queue='vae')
            for fire_id in fire_event_ids
        ]

        group_result = group(signatures).apply_async() if signatures else None

        return {
            'total_tasks_enqueued': len(signatures),
            'fire_events': len(fire_event_ids),
            'status': 'queued',
            'group_id': group_result.id if group_result else None,
        }

    except Exception as exc:
        logger.error(f"Error in batch recovery analysis: {exc}")
        raise self.retry(exc=exc, countdown=60)
