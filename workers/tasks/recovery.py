"""
Recovery Task: Monitoreo de recuperación de vegetación post-incendio.

F5: bbox desde perimeter, persist pending_reason, cache en fire_events.
1–2 requests GEE por ejecución. Idempotente: ON CONFLICT (fire_event_id, monitoring_date).
"""

import logging
from datetime import date

from sqlalchemy import text

from app.core.recovery_thresholds import classify_recovery_status

from ..celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.analyze_recovery",
    queue="vae",
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=300,
    time_limit=360,
)
def analyze_recovery(self, fire_event_id: str, target_date_str: str | None = None) -> dict:
    """
    Analiza recuperación de vegetación para un evento.
    1. Lee geometría (perimeter o centroid). 2. Baseline desde BD o GEE.
    3. NDVI actual vía GEE. 4. Clasifica. 5. UPSERT vegetation_monitoring.
    6. Actualiza cache fire_events (latest_recovery_status, latest_recovery_pct).
    """
    from app.db.session import SessionLocal
    from app.services.vae_service import VAEService, BaselineNotAvailableError
    from app.services.gee_service import GEEImageNotFoundError, GEEServiceUnavailableError

    db = SessionLocal()
    try:
        # 1. Leer evento (bbox desde perimeter, fallback centroid)
        row = db.execute(
            text("""
                SELECT
                    fe.start_date,
                    ST_X(fe.centroid::geometry) AS lon,
                    ST_Y(fe.centroid::geometry) AS lat,
                    CASE WHEN fe.perimeter IS NOT NULL THEN ST_XMin(fe.perimeter::geometry)
                         ELSE ST_X(fe.centroid::geometry) - 0.01 END AS bbox_west,
                    CASE WHEN fe.perimeter IS NOT NULL THEN ST_YMin(fe.perimeter::geometry)
                         ELSE ST_Y(fe.centroid::geometry) - 0.01 END AS bbox_south,
                    CASE WHEN fe.perimeter IS NOT NULL THEN ST_XMax(fe.perimeter::geometry)
                         ELSE ST_X(fe.centroid::geometry) + 0.01 END AS bbox_east,
                    CASE WHEN fe.perimeter IS NOT NULL THEN ST_YMax(fe.perimeter::geometry)
                         ELSE ST_Y(fe.centroid::geometry) + 0.01 END AS bbox_north
                FROM fire_events fe
                WHERE fe.id = :fid
            """),
            {"fid": fire_event_id},
        ).fetchone()

        if not row:
            logger.error("Fire event %s not found", fire_event_id)
            return {"status": "error", "reason": "event_not_found"}

        fire_date = row.start_date
        if hasattr(fire_date, "date"):
            fire_date = fire_date.date()
        bbox = {
            "west": float(row.bbox_west),
            "south": float(row.bbox_south),
            "east": float(row.bbox_east),
            "north": float(row.bbox_north),
        }

        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str).replace(day=1)
            except ValueError:
                logger.warning(
                    "Invalid target_date_str=%s for fire_event_id=%s, falling back to current month",
                    target_date_str,
                    fire_event_id,
                )
                target_date = date.today().replace(day=1)
        else:
            target_date = date.today().replace(day=1)
        months_after = (target_date.year - fire_date.year) * 12 + (
            target_date.month - fire_date.month
        )

        # 2. Baseline: desde BD o GEE
        existing_baseline = db.execute(
            text("""
                SELECT baseline_ndvi FROM vegetation_monitoring
                WHERE fire_event_id = :fid AND baseline_ndvi IS NOT NULL
                ORDER BY monitoring_date ASC LIMIT 1
            """),
            {"fid": fire_event_id},
        ).fetchone()

        vae = VAEService()
        if existing_baseline and existing_baseline.baseline_ndvi is not None:
            baseline_ndvi = float(existing_baseline.baseline_ndvi)
        else:
            try:
                baseline_ndvi = vae._get_baseline_ndvi(bbox, fire_date)
            except BaselineNotAvailableError:
                logger.warning("No baseline available for %s", fire_event_id)
                db.execute(
                    text("""
                        INSERT INTO vegetation_monitoring (
                            fire_event_id, monitoring_date, months_after_fire,
                            pending_reason, recovery_status, updated_at
                        ) VALUES (:fid, :dt, :months, 'no_baseline_image', 'pending', NOW())
                        ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                            pending_reason = 'no_baseline_image',
                            recovery_status = 'pending',
                            updated_at = NOW()
                    """),
                    {"fid": fire_event_id, "dt": target_date, "months": months_after},
                )
                db.commit()
                return {"status": "pending", "reason": "no_baseline_image"}

        # 3. NDVI actual
        try:
            ndvi_result, cloud_cover = vae._get_current_ndvi_with_cloud(bbox, target_date)
            current_ndvi = ndvi_result.mean
        except GEEImageNotFoundError:
            logger.warning("No current image for %s at %s", fire_event_id, target_date)
            db.execute(
                text("""
                    INSERT INTO vegetation_monitoring (
                        fire_event_id, monitoring_date, months_after_fire,
                        baseline_ndvi, pending_reason, recovery_status, updated_at
                    ) VALUES (:fid, :dt, :months, :baseline, 'no_current_image', 'pending', NOW())
                    ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                        pending_reason = 'no_current_image',
                        recovery_status = 'pending',
                        updated_at = NOW()
                """),
                {
                    "fid": fire_event_id,
                    "dt": target_date,
                    "months": months_after,
                    "baseline": baseline_ndvi,
                },
            )
            db.commit()
            return {"status": "pending", "reason": "no_current_image"}

        # 4. Clasificar y persistir
        recovery_pct = min(100.0, max(0.0, (current_ndvi / baseline_ndvi) * 100))
        recovery_status = classify_recovery_status(recovery_pct)
        
        # Extraer valores adicionales de NDVIResult de forma defensiva
        ndvi_min = getattr(ndvi_result, 'min', None)
        ndvi_max = getattr(ndvi_result, 'max', None)
        ndvi_std_dev = getattr(ndvi_result, 'std_dev', None)

        db.execute(
            text("""
                INSERT INTO vegetation_monitoring (
                    fire_event_id, monitoring_date, months_after_fire,
                    ndvi_mean, ndvi_min, ndvi_max, ndvi_std_dev,
                    baseline_ndvi, recovery_percentage,
                    cloud_cover_pct, recovery_status, pending_reason,
                    human_activity_detected, activity_type, updated_at
                ) VALUES (
                    :fid, :dt, :months,
                    :ndvi, :ndvi_min, :ndvi_max, :ndvi_std_dev,
                    :baseline, :recovery_pct,
                    :cloud, :status, NULL,
                    false, NULL, NOW()
                )
                ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                    ndvi_mean = EXCLUDED.ndvi_mean,
                    ndvi_min = EXCLUDED.ndvi_min,
                    ndvi_max = EXCLUDED.ndvi_max,
                    ndvi_std_dev = EXCLUDED.ndvi_std_dev,
                    baseline_ndvi = EXCLUDED.baseline_ndvi,
                    recovery_percentage = EXCLUDED.recovery_percentage,
                    cloud_cover_pct = EXCLUDED.cloud_cover_pct,
                    recovery_status = EXCLUDED.recovery_status,
                    pending_reason = NULL,
                    human_activity_detected = EXCLUDED.human_activity_detected,
                    activity_type = EXCLUDED.activity_type,
                    updated_at = NOW()
            """),
            {
                "fid": fire_event_id,
                "dt": target_date,
                "months": months_after,
                "ndvi": current_ndvi,
                "ndvi_min": ndvi_min,
                "ndvi_max": ndvi_max,
                "ndvi_std_dev": ndvi_std_dev,
                "baseline": baseline_ndvi,
                "recovery_pct": recovery_pct,
                "cloud": cloud_cover,
                "status": recovery_status,
            },
        )

        # 5. Cache en fire_events para badge en listado
        db.execute(
            text("""
                UPDATE fire_events SET
                    latest_recovery_status = :status,
                    latest_recovery_pct = :pct
                WHERE id = :fid
            """),
            {"fid": fire_event_id, "status": recovery_status, "pct": recovery_pct},
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
            "fire_event_id": fire_event_id,
            "recovery_percentage": round(recovery_pct, 1),
            "recovery_status": recovery_status,
            "baseline_ndvi": baseline_ndvi,
            "current_ndvi": current_ndvi,
        }
    except GEEServiceUnavailableError as e:
        logger.error("GEE circuit breaker open: %s", e)
        db.rollback()
        raise self.retry(exc=e, countdown=300)
    except Exception as exc:
        db.rollback()
        logger.error(
            "analyze_recovery_failed fire_event_id=%s error_type=%s error_msg=%s",
            fire_event_id,
            type(exc).__name__,
            str(exc)[:500],
            exc_info=True,
        )
        raise
    finally:
        db.close()


# Countdown entre tasks para no saturar GEE (VAE cola vae)
GEE_DELAY_BETWEEN_TASKS = 3
MAX_EVENTS_MONTHLY = 900


@celery_app.task(
    name="workers.tasks.recovery.batch_recovery_monthly",
    queue="vae",
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
            queue="vae",
            countdown=i * GEE_DELAY_BETWEEN_TASKS,
        )
        enqueued += 1
    logger.info("batch_recovery_monthly enqueued=%d", enqueued)
    return {"enqueued": enqueued, "status": "queued"}


@celery_app.task(
    name="workers.tasks.recovery.batch_recovery_recent",
    queue="vae",
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
            queue="vae",
            countdown=i * GEE_DELAY_BETWEEN_TASKS,
        )
        enqueued += 1
    logger.info("batch_recovery_recent enqueued=%d", enqueued)
    return {"enqueued": enqueued, "status": "queued"}


@celery_app.task(
    bind=True,
    name="workers.tasks.recovery.batch_recovery_analysis",
    queue="vae",
    max_retries=2,
)
def batch_recovery_analysis(self, fire_event_ids=None, max_events=50, months_list=None):
    """
    Compatibilidad: encola analyze_recovery para una lista de IDs o eventos activos.
    Usa cola vae y countdown escalonado.
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
            queue="vae",
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
    queue="vae",
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
        result = analyze_recovery.apply_async(args=[rep_id], queue="vae")
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
    queue="vae",
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
        gr = group(sigs).apply_async(queue="vae")
        return {
            "total_episodes": len(episode_ids),
            "total_tasks_enqueued": len(sigs),
            "episode_ids": episode_ids,
            "status": "queued",
            "group_id": gr.id,
        }
    finally:
        db.close()
