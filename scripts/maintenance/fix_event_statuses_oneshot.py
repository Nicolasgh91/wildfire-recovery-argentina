"""
EVT-005: Script one-shot para corregir fire_events con status estatico.

Aplica la misma logica que el task EVT-001 (update_event_statuses),
incluyendo el check espacial de 2km para monitoring -> extinct.

Uso:
    python scripts/maintenance/fix_event_statuses_oneshot.py --dry-run
    python scripts/maintenance/fix_event_statuses_oneshot.py

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md (EVT-005)
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.episode_flow_parameters import load_canonical_episode_flow_parameters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def print_distribution(db):
    rows = db.execute(
        text("SELECT status, COUNT(*) AS cnt FROM fire_events GROUP BY status ORDER BY cnt DESC")
    ).fetchall()
    logger.info("Distribucion de fire_events.status:")
    for row in rows:
        logger.info("  %-12s: %d", row[0], row[1])


def count_to_monitoring(db, active_window):
    return db.execute(text("""
        SELECT COUNT(*) FROM fire_events
         WHERE status = 'active'
           AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
           AND COALESCE(last_seen_at, end_date, start_date)
               < NOW() - MAKE_INTERVAL(hours => :active_window)
    """), {"active_window": active_window}).scalar()


def count_to_extinct(db, extinct_window):
    return db.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT fe.id
              FROM fire_events fe
             WHERE fe.status = 'monitoring'
               AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
               AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                   < NOW() - MAKE_INTERVAL(hours => :extinct_window)
               AND NOT EXISTS (
                   SELECT 1 FROM fire_detections fd
                    WHERE ST_DWithin(fd.location::geography, fe.centroid, 2000)
                      AND fd.detected_at
                          > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
               )
        ) sub
    """), {"extinct_window": extinct_window}).scalar()


def main():
    parser = argparse.ArgumentParser(description="Corrige fire_events.status estaticos (EVT-005)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--active-window", type=int, default=None,
                        help="Ventana active->monitoring en horas (default: system_parameters o 168)")
    parser.add_argument("--extinct-window", type=int, default=None,
                        help="Ventana monitoring->extinct en horas (default: system_parameters o 336)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        params = load_canonical_episode_flow_parameters(db)
        active_window = args.active_window or int(params.get("event_monitoring_window_hours", 168))
        extinct_window = args.extinct_window or int(params.get("event_extinction_window_hours", 336))

        logger.info("active_window  = %d h (active -> monitoring)", active_window)
        logger.info("extinct_window = %d h (monitoring -> extinct, + spatial check 2km)", extinct_window)

        print_distribution(db)

        if args.dry_run:
            n_mon = count_to_monitoring(db, active_window)
            n_ext = count_to_extinct(db, extinct_window)
            logger.info("[DRY-RUN] Pasarian a monitoring: %d", n_mon)
            logger.info("[DRY-RUN] Pasarian a extinct:    %d", n_ext)
            logger.info("[DRY-RUN] No se realizaron cambios.")
            return

        db.execute(text("SET statement_timeout = '300s'"))
        t0 = time.monotonic()

        # Paso 1: active -> monitoring
        r1 = db.execute(text("""
            UPDATE fire_events
               SET status = 'monitoring', updated_at = NOW()
             WHERE status = 'active'
               AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
               AND COALESCE(last_seen_at, end_date, start_date)
                   < NOW() - MAKE_INTERVAL(hours => :active_window)
        """), {"active_window": active_window})
        logger.info("Actualizados a monitoring: %d", r1.rowcount)

        # Paso 2: monitoring -> extinct (con spatial check)
        r2 = db.execute(text("""
            UPDATE fire_events
               SET status = 'extinct', updated_at = NOW()
             WHERE id IN (
                 SELECT fe.id
                   FROM fire_events fe
                  WHERE fe.status = 'monitoring'
                    AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
                    AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                        < NOW() - MAKE_INTERVAL(hours => :extinct_window)
                    AND NOT EXISTS (
                        SELECT 1 FROM fire_detections fd
                         WHERE ST_DWithin(fd.location::geography, fe.centroid, 2000)
                           AND fd.detected_at
                               > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                    )
             )
        """), {"extinct_window": extinct_window})
        logger.info("Actualizados a extinct:    %d", r2.rowcount)

        db.commit()
        logger.info("COMMIT exitoso en %d ms.", int((time.monotonic() - t0) * 1000))

        print_distribution(db)

    except Exception:
        db.rollback()
        logger.exception("Error. Se realizo rollback.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
