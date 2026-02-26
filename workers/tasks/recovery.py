"""
Recovery Task: Monitoreo de recuperación de vegetación post-incendio.

Fase 2 (GEE incremental): 1–2 requests GEE por ejecución.
- Si ya existe baseline en BD: 1 req (mes actual).
- Si no existe baseline: 2 req (baseline + mes actual).
Persiste en vegetation_monitoring con UPSERT idempotente.
"""

import logging
from datetime import date, datetime, timedelta

from sqlalchemy import text

from ..celery_app import celery_app

logger = logging.getLogger(__name__)


def _classify_recovery(pct: float, current: float, baseline: float) -> str:
    """Clasifica el estado de recuperación (string para BD/API)."""
    if baseline and current >= baseline * 0.95:
        return "full_recovery"
    if pct >= 80:
        return "advanced_recovery"
    if pct >= 50:
        return "moderate_recovery"
    if pct >= 20:
        return "early_recovery"
    if pct >= 0:
        return "stalled"
    return "not_started"


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.analyze_recovery",
    queue="gee",
    max_retries=2,
)
def analyze_recovery(self, fire_event_id: str) -> dict:
    """
    Analiza recuperación vegetal para un evento. Máximo 2 requests GEE por ejecución.

    1. Lee baseline desde vegetation_monitoring si ya existe.
    2. Si no existe, llama vae._get_baseline_ndvi (1 req GEE); propaga BaselineNotAvailableError.
    3. Llama vae._get_current_ndvi_with_cloud para mes actual (1 req GEE).
    4. Calcula recovery_pct y recovery_status; UPSERT en vegetation_monitoring.
    """
    from app.db.session import SessionLocal
    from app.services.vae_service import (
        BaselineNotAvailableError,
        get_vae_service,
    )
    from app.services.gee_service import GEEImageNotFoundError

    db = SessionLocal()
    try:
        # 1. Fire event + bbox
        fire_row = db.execute(
            text("""
                SELECT id, start_date,
                       ST_Y(centroid::geometry) AS lat,
                       ST_X(centroid::geometry) AS lon
                FROM fire_events
                WHERE id = :fire_id
            """),
            {"fire_id": str(fire_event_id)},
        ).fetchone()

        if not fire_row:
            logger.warning("analyze_recovery: fire event not found, fire_event_id=%s", fire_event_id)
            return {"status": "skipped", "reason": "not_found"}

        fire_date = fire_row.start_date
        if hasattr(fire_date, "date"):
            fire_date = fire_date.date()
        lat, lon = float(fire_row.lat), float(fire_row.lon)
        bbox = {
            "min_lon": lon - 0.01,
            "max_lon": lon + 0.01,
            "min_lat": lat - 0.01,
            "max_lat": lat + 0.01,
        }

        # 2. Baseline: desde BD o 1 req GEE
        baseline_row = db.execute(
            text("""
                SELECT baseline_ndvi FROM vegetation_monitoring
                WHERE fire_event_id = :fid AND baseline_ndvi IS NOT NULL
                LIMIT 1
            """),
            {"fid": str(fire_event_id)},
        ).fetchone()

        vae = get_vae_service()
        if baseline_row and baseline_row.baseline_ndvi is not None:
            baseline_ndvi = float(baseline_row.baseline_ndvi)
        else:
            try:
                baseline_ndvi = vae._get_baseline_ndvi(bbox, fire_date)
            except BaselineNotAvailableError:
                logger.warning(
                    "analyze_recovery: no_baseline_image fire_event_id=%s",
                    fire_event_id,
                )
                return {"status": "pending", "reason": "no_baseline_image"}

        # 3. Mes actual: 1 req GEE (ndvi + cloud)
        today = date.today()
        target_month = today.replace(day=1)
        try:
            current_ndvi, cloud_cover_pct = vae._get_current_ndvi_with_cloud(
                bbox, target_month
            )
        except GEEImageNotFoundError:
            logger.warning(
                "analyze_recovery: no_image_this_month fire_event_id=%s month=%s",
                fire_event_id,
                target_month.isoformat(),
            )
            return {"status": "pending", "reason": "no_image_this_month"}

        # 4. recovery_pct = (current / baseline) * 100 — porcentaje del baseline alcanzado (gee_spec §1.3)
        recovery_pct = min(100.0, max(0.0, (current_ndvi / baseline_ndvi) * 100))
        recovery_status = _classify_recovery(recovery_pct, current_ndvi, baseline_ndvi)

        # months_after_fire
        months_after = (target_month.year - fire_date.year) * 12 + (
            target_month.month - fire_date.month
        )

        # 5. UPSERT (idempotente); cloud_cover_pct y recovery_status desde migración 2026_02_26
        db.execute(
            text("""
                INSERT INTO vegetation_monitoring (
                    fire_event_id, monitoring_date, months_after_fire,
                    ndvi_mean, baseline_ndvi, recovery_percentage,
                    cloud_cover_pct, recovery_status,
                    human_activity_detected, activity_type, updated_at
                ) VALUES (
                    :fire_event_id, :monitoring_date, :months_after_fire,
                    :ndvi_mean, :baseline_ndvi, :recovery_percentage,
                    :cloud_cover_pct, :recovery_status,
                    :human_activity_detected, :activity_type, NOW()
                )
                ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                    months_after_fire = EXCLUDED.months_after_fire,
                    ndvi_mean = EXCLUDED.ndvi_mean,
                    baseline_ndvi = EXCLUDED.baseline_ndvi,
                    recovery_percentage = EXCLUDED.recovery_percentage,
                    cloud_cover_pct = EXCLUDED.cloud_cover_pct,
                    recovery_status = EXCLUDED.recovery_status,
                    human_activity_detected = EXCLUDED.human_activity_detected,
                    activity_type = EXCLUDED.activity_type,
                    updated_at = NOW()
            """),
            {
                "fire_event_id": str(fire_event_id),
                "monitoring_date": target_month,
                "months_after_fire": months_after,
                "ndvi_mean": current_ndvi,
                "baseline_ndvi": baseline_ndvi,
                "recovery_percentage": recovery_pct,
                "cloud_cover_pct": cloud_cover_pct,
                "recovery_status": recovery_status,
                "human_activity_detected": False,
                "activity_type": None,
            },
        )
        db.commit()

        logger.info(
            "recovery_analyzed fire_event_id=%s recovery_pct=%.1f status=%s",
            fire_event_id,
            recovery_pct,
            recovery_status,
        )
        return {
            "status": "ok",
            "recovery_percentage": recovery_pct,
            "recovery_status": recovery_status,
        }
    except BaselineNotAvailableError:
        db.rollback()
        logger.warning(
            "analyze_recovery: baseline_not_available fire_event_id=%s",
            fire_event_id,
        )
        return {"status": "pending", "reason": "no_baseline_image"}
    except Exception as exc:
        db.rollback()
        logger.error(
            "analyze_recovery_failed fire_event_id=%s error_type=%s error_msg=%s",
            fire_event_id,
            type(exc).__name__,
            str(exc)[:500],
        )
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


# Countdown entre tasks para no saturar GEE (gee_spec §3.3)
GEE_DELAY_BETWEEN_TASKS = 3
MAX_EVENTS_MONTHLY = 900


@celery_app.task(
    name="workers.tasks.recovery.batch_recovery_monthly",
    queue="gee",
)
def batch_recovery_monthly() -> dict:
    """
    Encola analyze_recovery para eventos active/monitoring (LIMIT 900).
    Día 2 de cada mes 02:00 UTC. 900 × 2 ≈ 1.800 req GEE (~4% cuota diaria).
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT id FROM fire_events
                WHERE status IN ('active', 'monitoring')
                  AND centroid IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT :limit
            """),
            {"limit": MAX_EVENTS_MONTHLY},
        ).fetchall()
        event_ids = [str(r.id) for r in rows]
    finally:
        db.close()

    enqueued = 0
    for i, eid in enumerate(event_ids):
        analyze_recovery.apply_async(
            args=[eid],
            queue="gee",
            countdown=i * GEE_DELAY_BETWEEN_TASKS,
        )
        enqueued += 1
    logger.info("batch_recovery_monthly enqueued=%d", enqueued)
    return {"enqueued": enqueued, "status": "queued"}


@celery_app.task(
    name="workers.tasks.recovery.batch_recovery_recent",
    queue="gee",
)
def batch_recovery_recent() -> dict:
    """
    Encola analyze_recovery para eventos creados en los últimos 30 días
    que no tengan análisis del mes actual (LEFT JOIN por ausencia).
    Lunes 03:00 UTC.
    """
    from app.db.session import SessionLocal

    today = date.today()
    first_of_month = today.replace(day=1)
    db = SessionLocal()
    try:
        rows = db.execute(
            text("""
                SELECT fe.id
                FROM fire_events fe
                LEFT JOIN vegetation_monitoring vm
                  ON vm.fire_event_id = fe.id
                  AND vm.monitoring_date = :first_of_month
                WHERE fe.centroid IS NOT NULL
                  AND fe.created_at >= NOW() - INTERVAL '30 days'
                  AND vm.fire_event_id IS NULL
                ORDER BY fe.created_at DESC
                LIMIT 500
            """),
            {"first_of_month": first_of_month},
        ).fetchall()
        event_ids = [str(r.id) for r in rows]
    finally:
        db.close()

    enqueued = 0
    for i, eid in enumerate(event_ids):
        analyze_recovery.apply_async(
            args=[eid],
            queue="gee",
            countdown=i * GEE_DELAY_BETWEEN_TASKS,
        )
        enqueued += 1
    logger.info("batch_recovery_recent enqueued=%d", enqueued)
    return {"enqueued": enqueued, "status": "queued"}


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.batch_recovery_analysis",
    queue="gee",
    max_retries=2,
)
def batch_recovery_analysis(self, fire_event_ids=None, max_events=50, months_list=None):
    """
    Compatibilidad: encola analyze_recovery para una lista de IDs o eventos activos.
    Usa cola gee y countdown escalonado.
    """
    from app.db.session import SessionLocal

    if not fire_event_ids:
        db = SessionLocal()
        try:
            rows = db.execute(
                text("""
                    SELECT fe.id FROM fire_events fe
                    WHERE fe.start_date > NOW() - INTERVAL '36 months'
                      AND fe.status IN ('active', 'monitoring', 'contained')
                      AND fe.centroid IS NOT NULL
                    ORDER BY fe.start_date DESC
                    LIMIT :max_events
                """),
                {"max_events": max_events},
            ).fetchall()
            fire_event_ids = [str(r.id) for r in rows]
        finally:
            db.close()

    for i, eid in enumerate(fire_event_ids):
        analyze_recovery.apply_async(
            args=[eid],
            queue="gee",
            countdown=i * GEE_DELAY_BETWEEN_TASKS,
        )
    return {
        "total_tasks_enqueued": len(fire_event_ids),
        "fire_events": len(fire_event_ids),
        "status": "queued",
    }


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.analyze_episode_recovery",
    queue="gee",
    max_retries=2,
)
def analyze_episode_recovery(self, episode_id, months_after=None):
    """Encola analyze_recovery para el evento representativo del episodio."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        event_row = db.execute(
            text("""
                SELECT fe.id FROM fire_events fe
                JOIN fire_episode_events fee ON fe.id = fee.event_id
                WHERE fee.episode_id = :eid AND fe.centroid IS NOT NULL
                ORDER BY fe.max_frp DESC NULLS LAST, fe.start_date DESC
                LIMIT 1
            """),
            {"eid": str(episode_id)},
        ).fetchone()
        if not event_row:
            return {"episode_id": str(episode_id), "status": "skipped", "reason": "no_representative_event"}
        rep_id = str(event_row.id)
        result = analyze_recovery.apply_async(args=[rep_id], queue="gee")
        return {
            "episode_id": str(episode_id),
            "representative_event_id": rep_id,
            "recovery_task_id": result.id,
            "status": "queued",
        }
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.batch_episode_recovery_analysis",
    queue="gee",
    max_retries=2,
)
def batch_episode_recovery_analysis(
    self, max_episodes=50, recent_only=False, carousel_only=False
):
    """Encola analyze_episode_recovery para múltiples episodios."""
    from app.db.session import SessionLocal
    from celery import group

    db = SessionLocal()
    try:
        where = ["fe.centroid IS NOT NULL"]
        if recent_only:
            where.append("fe.start_date >= NOW() - INTERVAL '12 months'")
        if carousel_only:
            where.append("ep.status IN ('active', 'monitoring')")
        where_sql = " AND ".join(where)
        rows = db.execute(
            text(f"""
                SELECT ep.id FROM fire_episodes ep
                JOIN fire_episode_events fee ON fee.episode_id = ep.id
                JOIN fire_events fe ON fe.id = fee.event_id
                WHERE {where_sql}
                GROUP BY ep.id
                ORDER BY ep.created_at DESC
                LIMIT :lim
            """),
            {"lim": max_episodes},
        ).fetchall()
        episode_ids = [str(r.id) for r in rows]
        if not episode_ids:
            return {"total_episodes": 0, "status": "completed", "message": "no_episodes_found"}
        sigs = [analyze_episode_recovery.s(eid) for eid in episode_ids]
        gr = group(sigs).apply_async(queue="gee")
        return {
            "total_episodes": len(episode_ids),
            "total_tasks_enqueued": len(sigs),
            "episode_ids": episode_ids,
            "status": "queued",
            "group_id": gr.id,
        }
    finally:
        db.close()
