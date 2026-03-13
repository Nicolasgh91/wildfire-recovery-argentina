"""
Destruction Task: Detección de destrucción de bosques y cambio de uso de suelo
post-incendio usando análisis multitemporal.

Persists results to land_use_changes table with upsert semantics.
"""

import logging
from datetime import datetime, timedelta
from celery import chord, group, shared_task
from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='workers.tasks.destruction.detect_destruction',
    queue='vae',
    max_retries=2,
)
def detect_destruction(self, fire_event_id, months_window=12):
    """
    Detecta cambios de uso de suelo post-incendio y persiste en land_use_changes.

    Args:
        fire_event_id: UUID del fuego
        months_window: Ventana temporal para analizar (meses)
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        logger.info(f"Detecting land use change for fire {fire_event_id}...")

        # 1. Get fire event geometry (bbox from perimeter, fallback centroid — F5-04)
        fire_row = db.execute(
            text("""
                SELECT
                    id,
                    start_date,
                    estimated_area_hectares,
                    CASE WHEN perimeter IS NOT NULL THEN ST_XMin(perimeter) ELSE ST_X(centroid) - 0.01 END AS bbox_west,
                    CASE WHEN perimeter IS NOT NULL THEN ST_YMin(perimeter) ELSE ST_Y(centroid) - 0.01 END AS bbox_south,
                    CASE WHEN perimeter IS NOT NULL THEN ST_XMax(perimeter) ELSE ST_X(centroid) + 0.01 END AS bbox_east,
                    CASE WHEN perimeter IS NOT NULL THEN ST_YMax(perimeter) ELSE ST_Y(centroid) + 0.01 END AS bbox_north
                FROM fire_events
                WHERE id = :fire_id
            """),
            {"fire_id": str(fire_event_id)},
        ).fetchone()

        if not fire_row:
            logger.warning("Fire event %s not found, skipping", fire_event_id)
            return {"fire_event_id": str(fire_event_id), "status": "skipped", "reason": "not_found"}

        fire_date = fire_row.start_date
        area_ha = fire_row.estimated_area_hectares or 0
        bbox = {
            "west": float(fire_row.bbox_west),
            "south": float(fire_row.bbox_south),
            "east": float(fire_row.bbox_east),
            "north": float(fire_row.bbox_north),
        }

        # 2. Run VAE land use change detection
        from app.services.vae_service import VAEService

        vae = VAEService()

        fire_date_obj = fire_date.date() if hasattr(fire_date, 'date') else fire_date

        try:
            analysis = vae.detect_land_use_change(
                fire_event_id=str(fire_event_id),
                bbox=bbox,
                fire_date=fire_date_obj,
                area_hectares=float(area_ha) if area_ha else 0,
            )
        except Exception as exc:
            logger.warning(f"GEE land use analysis failed for {fire_event_id}: {exc}")
            return {
                "fire_event_id": str(fire_event_id),
                "status": "gee_error",
                "error": str(exc),
            }

        # 3. Persist to land_use_changes with upsert (F5-04: confidence_score)
        change_date = analysis.analysis_date
        notes = "Alerta de detección remota — requiere verificación presencial"
        upsert_query = text("""
            INSERT INTO land_use_changes (
                fire_event_id,
                change_detected_at,
                months_after_fire,
                change_type,
                change_severity,
                affected_area_hectares,
                is_potential_violation,
                violation_confidence,
                confidence_score,
                status,
                notes,
                created_at,
                updated_at
            ) VALUES (
                :fire_event_id,
                :change_detected_at,
                :months_after_fire,
                :change_type,
                :change_severity,
                :affected_area_hectares,
                :is_potential_violation,
                :violation_confidence,
                :confidence_score,
                :status,
                :notes,
                NOW(),
                NOW()
            )
            ON CONFLICT (fire_event_id, change_detected_at) DO UPDATE SET
                change_type = EXCLUDED.change_type,
                change_severity = EXCLUDED.change_severity,
                affected_area_hectares = EXCLUDED.affected_area_hectares,
                is_potential_violation = EXCLUDED.is_potential_violation,
                violation_confidence = EXCLUDED.violation_confidence,
                confidence_score = EXCLUDED.confidence_score,
                status = EXCLUDED.status,
                notes = EXCLUDED.notes,
                updated_at = NOW()
        """)

        db.execute(upsert_query, {
            "fire_event_id": str(fire_event_id),
            "change_detected_at": change_date,
            "months_after_fire": analysis.months_after_fire,
            "change_type": analysis.change_type.value,
            "change_severity": analysis.violation_severity.value,
            "affected_area_hectares": analysis.affected_area_hectares,
            "is_potential_violation": analysis.is_potential_violation,
            "violation_confidence": str(analysis.change_confidence),
            "confidence_score": float(analysis.change_confidence),
            "status": "pending_review" if analysis.is_potential_violation else "reviewed",
            "notes": notes,
        })
        db.commit()

        logger.info(
            f"Land use change persisted for {fire_event_id}: "
            f"type={analysis.change_type.value}, violation={analysis.is_potential_violation}"
        )
        return {
            "fire_event_id": str(fire_event_id),
            "status": "completed",
            "destruction_detected": analysis.change_detected,
            "destruction_type": analysis.change_type.value,
            "affected_area_ha": analysis.affected_area_hectares,
            "is_potential_violation": analysis.is_potential_violation,
            "confidence": analysis.change_confidence,
            "analysis_date": change_date.isoformat(),
        }

    except Exception as exc:
        db.rollback()
        logger.error(f"Error detecting destruction for {fire_event_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


@shared_task(
    name='workers.tasks.destruction.classify_land_use',
    bind=True,
)
def classify_land_use(self, fire_event_id, date_after_fire):
    """
    Clasifica uso de suelo post-incendio en categorías Ley 26.815.
    Uses VAEService for classification.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        logger.info(f"Classifying land use for {fire_event_id}...")

        fire_row = db.execute(
            text("""
                SELECT
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
            return {"fire_event_id": str(fire_event_id), "status": "not_found"}

        from app.services.vae_service import VAEService
        from datetime import date as date_type

        vae = VAEService()
        fire_lat, fire_lon = fire_row.lat, fire_row.lon
        buffer = 0.01
        bbox = {
            "west": fire_lon - buffer,
            "south": fire_lat - buffer,
            "east": fire_lon + buffer,
            "north": fire_lat + buffer,
        }

        fire_date_obj = fire_row.start_date.date() if hasattr(fire_row.start_date, 'date') else fire_row.start_date
        analysis_date = date_type.fromisoformat(date_after_fire) if isinstance(date_after_fire, str) else date_after_fire

        result = vae.detect_land_use_change(
            fire_event_id=str(fire_event_id),
            bbox=bbox,
            fire_date=fire_date_obj,
            analysis_date=analysis_date,
            area_hectares=float(fire_row.estimated_area_hectares or 0),
        )

        return {
            'fire_event_id': str(fire_event_id),
            'classification_date': date_after_fire,
            'change_type': result.change_type.value,
            'is_potential_violation': result.is_potential_violation,
            'confidence': result.change_confidence,
            'recommended_action': result.recommended_action,
        }

    except Exception as exc:
        logger.error(f"Error classifying land use: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@shared_task(
    name='workers.tasks.destruction.generate_destruction_report',
    bind=True,
)
def generate_destruction_report(self, fire_event_id):
    """
    Genera reporte judicial de destrucción post-incendio.
    Combines destruction detection + land use classification.
    """
    try:
        logger.info(f"Generating destruction report for {fire_event_id}...")

        report_date = datetime.utcnow().isoformat()
        workflow = chord(
            group(
                detect_destruction.s(fire_event_id).set(queue='vae'),
                classify_land_use.s(
                    fire_event_id, datetime.utcnow().date().isoformat()
                ).set(queue='vae'),
            ),
            compose_destruction_report.s(
                fire_event_id=fire_event_id,
                report_date=report_date,
            ).set(queue='vae'),
        )
        async_result = workflow.apply_async()

        return {
            'fire_event_id': fire_event_id,
            'status': 'queued',
            'workflow_id': async_result.id,
            'report_date': report_date,
            'report_type': 'judicial_destruction',
        }

    except Exception as exc:
        logger.error(f"Error generating report: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(
    name='workers.tasks.destruction.compose_destruction_report',
    bind=True,
)
def compose_destruction_report(self, analysis_results, fire_event_id, report_date):
    """Compose final report payload from chord/group subtask outputs."""
    destruction = {}
    land_use = {}
    for item in analysis_results or []:
        if not isinstance(item, dict):
            continue
        if "destruction_detected" in item:
            destruction = item
        elif "change_type" in item:
            land_use = item

    return {
        'fire_event_id': fire_event_id,
        'destruction': destruction,
        'land_use': land_use,
        'report_date': report_date,
        'report_type': 'judicial_destruction',
    }


@celery_app.task(
    bind=True,
    name='workers.tasks.destruction.batch_destruction_detection',
    queue='vae',
    max_retries=2,
)
def batch_destruction_detection(self, fire_event_ids=None, max_events=50):
    """
    Ejecuta detección de cambios de uso para eventos activos.

    Cuando fire_event_ids es None o vacío, consulta la BD para obtener
    los eventos activos más recientes (< 36 meses). Limita a max_events
    por ejecución para proteger la cuota GEE.

    Programada mensualmente vía Celery Beat.

    Args:
        fire_event_ids: Lista de UUIDs (opcional; si vacía, auto-query)
        max_events: Máximo de eventos a procesar por batch
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    try:
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

        logger.info(f"Batch destruction detection: {len(fire_event_ids)} fires...")

        from celery import group as celery_group
        signatures = [
            detect_destruction.s(fire_id).set(queue='vae')
            for fire_id in fire_event_ids
        ]

        group_result = celery_group(signatures).apply_async() if signatures else None

        return {
            'total_tasks_enqueued': len(signatures),
            'fire_events': len(fire_event_ids),
            'status': 'queued',
            'group_id': group_result.id if group_result else None,
        }

    except Exception as exc:
        logger.error(f"Error in batch destruction detection: {exc}")
        raise self.retry(exc=exc, countdown=60)
