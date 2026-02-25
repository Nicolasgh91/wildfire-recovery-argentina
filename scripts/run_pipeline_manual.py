"""
Manual pipeline execution: simulates the daily workers sequence.
Steps:
  1. Download FIRMS data (ingestion)
  2. Cluster detections -> fire_events
  3. Update event statuses (EVT-001)
  4. Geo-enrichment: provincia + areas protegidas (ENR-001)
  5. Cluster events -> fire_episodes

Uso:
    python scripts/run_pipeline_manual.py [--days-back N]
    (default: 115 para cubrir desde 01/11/25)
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("manual_pipeline")

from sqlalchemy import text
from app.db.session import SessionLocal

SEP = "=" * 80

def show_state(db, label: str):
    print()
    print(SEP)
    print(label)
    print(SEP)
    
    r1 = db.execute(text("""
        SELECT 
            COUNT(*) AS total_detections,
            COUNT(*) FILTER (WHERE is_processed = false) AS pending,
            COUNT(*) FILTER (WHERE fire_event_id IS NOT NULL) AS assigned
        FROM fire_detections
    """)).mappings().first()
    print("Detecciones: total=%s pending=%s assigned=%s" % (r1['total_detections'], r1['pending'], r1['assigned']))
    
    r2 = db.execute(text("SELECT status, COUNT(*) AS cnt FROM fire_events GROUP BY status ORDER BY status")).mappings().all()
    print("Eventos: %s" % ", ".join("%s=%s" % (r['status'], r['cnt']) for r in r2))
    
    r3 = db.execute(text("SELECT status, COUNT(*) AS cnt FROM fire_episodes GROUP BY status ORDER BY status")).mappings().all()
    print("Episodios: %s" % ", ".join("%s=%s" % (r['status'], r['cnt']) for r in r3))


def step1_ingestion():
    print()
    print(SEP)
    print("PASO 1: Ingesta de datos FIRMS")
    print(SEP)
    
    try:
        from scripts.maintenance.load_firms_incremental import run_incremental_pipeline
        result = run_incremental_pipeline()
        logger.info("Ingesta completada: %s", result)
        return result
    except Exception as e:
        logger.error("Error en ingesta: %s", e, exc_info=True)
        return {"error": str(e)}


def step2_clustering(days_back: int):
    print()
    print(SEP)
    print("PASO 2: Clustering de detecciones -> eventos (days_back=%d)" % days_back)
    print(SEP)
    
    db = SessionLocal()
    try:
        from app.services.detection_clustering_service import DetectionClusteringService
        service = DetectionClusteringService(db)
        result = service.run_clustering(days_back=days_back)
        db.commit()
        logger.info("Clustering completado: %s", result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error en clustering: %s", e, exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


def step3_event_statuses():
    print()
    print(SEP)
    print("PASO 3: Actualizacion de estados de eventos (EVT-001)")
    print(SEP)
    
    db = SessionLocal()
    try:
        from app.services.episode_flow_parameters import load_canonical_episode_flow_parameters
        from sqlalchemy import text

        params = load_canonical_episode_flow_parameters(db)
        active_window = int(params.get("event_monitoring_window_hours", 168))
        extinct_window = int(params.get("event_extinction_window_hours", 336))

        r1 = db.execute(text("""
            UPDATE fire_events
               SET status = 'monitoring', updated_at = NOW()
             WHERE status = 'active'
               AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
               AND COALESCE(last_seen_at, end_date, start_date)
                   < NOW() - MAKE_INTERVAL(hours => :w)
        """), {"w": active_window})

        r2 = db.execute(text("""
            UPDATE fire_events SET status = 'extinct', updated_at = NOW()
             WHERE id IN (
                 SELECT fe.id FROM fire_events fe
                  WHERE fe.status = 'monitoring'
                    AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
                    AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                        < NOW() - MAKE_INTERVAL(hours => :w)
                    AND NOT EXISTS (
                        SELECT 1 FROM fire_detections fd
                         WHERE ST_DWithin(fd.location::geography, fe.centroid, 2000)
                           AND fd.detected_at > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                    )
             )
        """), {"w": extinct_window})

        db.commit()
        result = {"to_monitoring": r1.rowcount, "to_extinct": r2.rowcount}
        logger.info("Event statuses actualizados: %s", result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error en event statuses: %s", e, exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


def step4_geo_enrichment(lookback_hours: int = 168):
    print()
    print(SEP)
    print("PASO 4: Geo-enrichment (provincia + areas protegidas, lookback=%dh)" % lookback_hours)
    print(SEP)
    
    try:
        from workers.tasks.geo_enrichment import enrich_recent_fire_events
        # .apply() ejecuta el task sincrónicamente sin necesitar broker
        result = enrich_recent_fire_events.apply(kwargs={"lookback_hours": lookback_hours, "max_events": 10000}).get()
        logger.info("Geo-enrichment completado: %s", result)
        return result
    except Exception as e:
        logger.error("Error en geo-enrichment: %s", e, exc_info=True)
        return {"error": str(e)}


def step5_episodes(days_back: int):
    print()
    print(SEP)
    print("PASO 5: Agrupacion de eventos -> episodios (days_back=%d)" % days_back)
    print(SEP)
    
    db = SessionLocal()
    try:
        from app.services.clustering_service import ClusteringService
        service = ClusteringService(db)
        result = service.run_clustering(days_back=days_back, max_events=10000)
        logger.info("Episodios completado: %s", result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error en episodios: %s", e, exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days-back", type=int, default=115,
                        help="Dias hacia atras para clustering/episodios (default: 115 = desde 01/11/25)")
    args = parser.parse_args()
    days_back = args.days_back

    db = SessionLocal()
    show_state(db, "ESTADO ANTES DEL PIPELINE")
    db.close()
    
    print("\n" + ">" * 80)
    print("EJECUTANDO PIPELINE MANUAL (days_back=%d)" % days_back)
    print(">" * 80)
    
    r1 = step1_ingestion()
    
    db = SessionLocal()
    show_state(db, "ESTADO POST-INGESTA")
    db.close()
    
    r2 = step2_clustering(days_back=days_back)
    
    db = SessionLocal()
    show_state(db, "ESTADO POST-CLUSTERING DE DETECCIONES")
    db.close()

    r3 = step3_event_statuses()

    r4 = step4_geo_enrichment(lookback_hours=days_back * 24)
    
    db = SessionLocal()
    show_state(db, "ESTADO POST-GEO-ENRICHMENT")
    db.close()
    
    r5 = step5_episodes(days_back=days_back)
    
    db = SessionLocal()
    show_state(db, "ESTADO FINAL POST-EPISODIOS")
    db.close()
    
    print()
    print(SEP)
    print("RESUMEN PIPELINE (days_back=%d, desde ~01/11/25)" % days_back)
    print(SEP)
    print("1. Ingesta:         %s" % r1)
    print("2. Clustering:      %s" % r2)
    print("3. Event statuses:  %s" % r3)
    print("4. Geo-enrichment:  %s" % r4)
    print("5. Episodios:       %s" % r5)
