"""
F11: Backfill histórico de datos VAE en vegetation_monitoring.

- Régimen A: eventos cerrados históricos (start_date < 2025-12-01), puntos semestrales.
- Régimen B: eventos cerrados recientes (start_date >= 2025-12-01), puntos mensuales.
- Solo eventos sin datos de monitoreo (sin filas en vegetation_monitoring).
- Prioriza eventos en áreas protegidas (fire_protected_area_intersections).

El objetivo es poblar la serie NDVI histórica controlando el uso de quota GEE.
"""

import logging
from datetime import date

from sqlalchemy import text

from ..celery_app import celery_app
from app.db.session import SessionLocal
from .recovery import analyze_recovery

logger = logging.getLogger(__name__)

DAILY_GEE_CAP = 5000
REQUESTS_PER_POINT = 2  # baseline + current
CUTOFF_DATE = date(2025, 12, 1)


def _generate_analysis_points(
    fire_date: date,
    today: date,
    interval_months: int,
) -> list[date]:
    """
    Genera fechas de análisis (primer día de mes) desde fire_date hasta today.

    interval_months: 6 para régimen A (semestral), 1 para régimen B (mensual).
    """
    points: list[date] = []

    # Normalizar a primer día del mes de inicio
    start_month = date(fire_date.year, fire_date.month, 1)
    current = start_month

    # Avanzar al primer punto después del incendio
    # (primer múltiplo de interval_months)
    months_offset = interval_months
    while True:
        year = start_month.year + (start_month.month - 1 + months_offset) // 12
        month = (start_month.month - 1 + months_offset) % 12 + 1
        current = date(year, month, 1)
        if current > today:
            break
        points.append(current)
        months_offset += interval_months

    # Asegurar incluir el mes actual si no quedó incluido
    today_month = date(today.year, today.month, 1)
    if points and points[-1] != today_month and today_month > start_month:
        points.append(today_month)
    elif not points and today_month > start_month:
        points.append(today_month)

    return points


def _fetch_events(
    db: SessionLocal,
    batch_size: int,
    before_date: date | None = None,
    from_date: date | None = None,
    prioritize_protected: bool = True,
    target_year: int | None = None,
    magnitude_threshold: float = 0,
):
    """
    Obtiene fire_events cerrados sin datos en vegetation_monitoring.
    
    Args:
        target_year: Filtrar por año específico (ej: 2025)
        magnitude_threshold: Filtrar eventos con área >= threshold hectáreas
    """
    date_filter = ""
    if target_year:
        date_filter = f"AND EXTRACT(YEAR FROM fe.start_date) = {target_year}"
    elif before_date:
        date_filter = f"AND fe.start_date < '{before_date.isoformat()}'"
    elif from_date:
        date_filter = f"AND fe.start_date >= '{from_date.isoformat()}'"

    magnitude_filter = ""
    if magnitude_threshold > 0:
        magnitude_filter = f"AND COALESCE(ST_Area(fe.perimeter::geography) / 10000, 0) >= {magnitude_threshold}"

    order_clause = (
        """
        ORDER BY
            CASE WHEN fpa.protected_area_id IS NOT NULL THEN 0 ELSE 1 END,
            fe.start_date DESC
        """
        if prioritize_protected
        else "ORDER BY fe.start_date DESC"
    )

    rows = db.execute(
        text(
            f"""
            SELECT DISTINCT fe.id, fe.start_date,
                   COALESCE(ST_Area(fe.perimeter::geography) / 10000, 0) as area_ha
            FROM fire_events fe
            LEFT JOIN vegetation_monitoring vm
              ON vm.fire_event_id = fe.id
            LEFT JOIN fire_protected_area_intersections fpa
              ON fpa.fire_event_id = fe.id
            WHERE vm.id IS NULL
              AND fe.status IN ('extinct', 'closed')
              AND fe.start_date >= '2015-01-01'
              {date_filter}
              {magnitude_filter}
            {order_clause}
            LIMIT :batch
            """
        ),
        {"batch": batch_size},
    ).fetchall()

    return rows


def _enqueue_points(event_id: str, points: list[date]) -> int:
    """
    Encola analyze_recovery para cada punto de análisis (mes dado).

    Retorna la cantidad de puntos encolados.
    """
    for point in points:
        analyze_recovery.apply_async(
            args=[str(event_id), point.isoformat()],
            queue="vae",
            priority=9,  # menor prioridad que el scheduling regular
        )

    logger.info(
        "backfill_enqueued fire_event_id=%s points=%d first=%s last=%s",
        event_id,
        len(points),
        points[0] if points else None,
        points[-1] if points else None,
    )
    return len(points)


@celery_app.task(
    name="workers.tasks.backfill.backfill_historical_recovery",
    queue="vae",
    soft_time_limit=3600,
    time_limit=3900,
)
def backfill_historical_recovery(
    batch_size: int = 50,
    regime: str = "both",  # "A", "B" o "both"
    prioritize_protected: bool = True,
    target_year: int | None = None,
    magnitude_threshold: float = 0,
    optimize_frequency: bool = False,
) -> dict:
    """
    Backfill de recuperación histórica para eventos cerrados sin VAE.

    Args:
        target_year: Procesar solo eventos de un año específico
        magnitude_threshold: Filtrar eventos >= threshold hectáreas
        optimize_frequency: Usar frecuencia anual para 2015-2018, semestral para 2019+
    """
    db = SessionLocal()
    try:
        today = date.today()
        total_enqueued = 0
        events_processed = 0
        results = {"regime_a": 0, "regime_b": 0}

        # Procesamiento por año específico o régimen tradicional
        if target_year:
            # Procesar solo eventos del año específico
            events = _fetch_events(
                db,
                batch_size=batch_size,
                target_year=target_year,
                prioritize_protected=prioritize_protected,
                magnitude_threshold=magnitude_threshold,
            )
            for event in events:
                fire_id = str(event.id)
                fire_start = event.start_date
                if hasattr(fire_start, "date"):
                    fire_start = fire_start.date()
                
                # Determinar frecuencia según optimización
                if optimize_frequency and fire_start.year <= 2018:
                    interval_months = 12  # Anual para 2015-2018
                else:
                    interval_months = 6  # Semestral para 2019+
                
                points = _generate_analysis_points(
                    fire_start,
                    today,
                    interval_months=interval_months,
                )
                cost = len(points) * REQUESTS_PER_POINT
                if total_enqueued + cost > DAILY_GEE_CAP:
                    logger.info(
                        "backfill_cap_reached year=%d enqueued=%d cap=%d",
                        target_year,
                        total_enqueued,
                        DAILY_GEE_CAP,
                    )
                    break
                if points:
                    _enqueue_points(fire_id, points)
                    total_enqueued += cost
                    events_processed += 1
                    results[f"year_{target_year}"] = results.get(f"year_{target_year}", 0) + 1
        else:
            # Régimen A — históricos cerrados pre-dic 2025 (semestral)
            if regime in ("A", "both"):
                events_a = _fetch_events(
                    db,
                    batch_size=batch_size,
                    before_date=CUTOFF_DATE,
                    prioritize_protected=prioritize_protected,
                    magnitude_threshold=magnitude_threshold,
                )
                for event in events_a:
                    fire_id = str(event.id)
                    fire_start = event.start_date
                    if hasattr(fire_start, "date"):
                        fire_start = fire_start.date()
                    
                    interval_months = 12 if (optimize_frequency and fire_start.year <= 2018) else 6
                    points = _generate_analysis_points(
                        fire_start,
                        today,
                        interval_months=interval_months,
                    )
                    cost = len(points) * REQUESTS_PER_POINT
                    if total_enqueued + cost > DAILY_GEE_CAP:
                        logger.info(
                            "backfill_cap_reached regime=A enqueued=%d cap=%d",
                            total_enqueued,
                            DAILY_GEE_CAP,
                        )
                        break
                    if points:
                        _enqueue_points(fire_id, points)
                        total_enqueued += cost
                        events_processed += 1
                        results["regime_a"] += 1

            # Régimen B — recientes cerrados dic 2025+ (mensual)
            if regime in ("B", "both") and total_enqueued < DAILY_GEE_CAP:
                remaining_batch = max(batch_size - events_processed, 0)
                if remaining_batch > 0:
                    events_b = _fetch_events(
                        db,
                        batch_size=remaining_batch,
                        from_date=CUTOFF_DATE,
                        prioritize_protected=prioritize_protected,
                        magnitude_threshold=magnitude_threshold,
                    )
                    for event in events_b:
                        fire_id = str(event.id)
                        fire_start = event.start_date
                        if hasattr(fire_start, "date"):
                            fire_start = fire_start.date()
                        points = _generate_analysis_points(
                            fire_start,
                            today,
                            interval_months=1,
                        )
                        cost = len(points) * REQUESTS_PER_POINT
                        if total_enqueued + cost > DAILY_GEE_CAP:
                            logger.info(
                                "backfill_cap_reached regime=B enqueued=%d cap=%d",
                                total_enqueued,
                                DAILY_GEE_CAP,
                            )
                            break
                        if points:
                            _enqueue_points(fire_id, points)
                            total_enqueued += cost
                            events_processed += 1
                            results["regime_b"] += 1

        logger.info(
            "backfill_completed events_processed=%d total_requests=%d regime_a=%d regime_b=%d",
            events_processed,
            total_enqueued,
            results["regime_a"],
            results["regime_b"],
        )
        return {
            "status": "ok",
            "events_processed": events_processed,
            "total_requests_enqueued": total_enqueued,
            **results,
        }
    except Exception as exc:
        logger.error("backfill_failed error=%s", str(exc)[:500], exc_info=True)
        return {"status": "error", "reason": str(exc)}
    finally:
        db.close()

