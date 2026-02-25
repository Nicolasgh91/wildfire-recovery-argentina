"""
Manual pipeline execution: simulates the daily workers sequence.
Steps:
  1. Download FIRMS data (ingestion)
  2. Cluster detections → fire_events
  3. Cluster events → fire_episodes
"""

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


def step2_clustering():
    print()
    print(SEP)
    print("PASO 2: Clustering de detecciones -> eventos")
    print(SEP)
    
    db = SessionLocal()
    try:
        from app.services.detection_clustering_service import DetectionClusteringService
        service = DetectionClusteringService(db)
        result = service.run_clustering(days_back=7)
        db.commit()
        logger.info("Clustering completado: %s", result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error en clustering: %s", e, exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


def step3_episodes():
    print()
    print(SEP)
    print("PASO 3: Agrupacion de eventos -> episodios")
    print(SEP)
    
    db = SessionLocal()
    try:
        from app.services.clustering_service import ClusteringService
        service = ClusteringService(db)
        result = service.run_clustering(days_back=90, max_events=5000)
        logger.info("Episodios completado: %s", result)
        return result
    except Exception as e:
        db.rollback()
        logger.error("Error en episodios: %s", e, exc_info=True)
        return {"error": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    db = SessionLocal()
    show_state(db, "ESTADO ANTES DEL PIPELINE")
    db.close()
    
    print("\n" + ">" * 80)
    print("EJECUTANDO PIPELINE MANUAL")
    print(">" * 80)
    
    r1 = step1_ingestion()
    
    db = SessionLocal()
    show_state(db, "ESTADO POST-INGESTA")
    db.close()
    
    r2 = step2_clustering()
    
    db = SessionLocal()
    show_state(db, "ESTADO POST-CLUSTERING")
    db.close()
    
    r3 = step3_episodes()
    
    db = SessionLocal()
    show_state(db, "ESTADO FINAL POST-EPISODIOS")
    db.close()
    
    print()
    print(SEP)
    print("RESUMEN")
    print(SEP)
    print("Ingesta:    %s" % r1)
    print("Clustering: %s" % r2)
    print("Episodios:  %s" % r3)
