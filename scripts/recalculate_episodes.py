#!/usr/bin/env python
"""
Recalculate episode metrics and trigger imagery carousel recreation.
Usage:
    export PYTHONPATH=.
    python scripts/recalculate_episodes.py
"""
import logging
import sys
from uuid import uuid4

from app.db.session import SessionLocal
from app.services.episode_service import EpisodeService
from app.services.imagery_service import ImageryService
from app.models.episode import FireEpisode
from sqlalchemy.orm import Session
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("recalculate_episodes")

def main():
    """
    Script de mantenimiento: Recalculo forzado de métricas de Episodios de Fuego.
    
    Este script itera sobre todos los episodios de la base de datos (activos,
    en monitoreo, extintos o cerrados) y fuerza una reevaluación completa de sus
    métricas (área, FRP, cantidad de detecciones, estado actual, geometría)
    basado en las detecciones térmicas subyacentes.

    Manejo de Transacciones (Savepoints):
        Utiliza `db.begin_nested()` bloque a bloque. Si el recalculo de un
        episodio específico explota por consistencias de BD (ej. tratar de mediar
        un EPSG geometry inválido o sumar NULLs), se aisla la excepcion, se
        escribe el traceback en Logger, y la transacción general continua viva
        para procesar los N miles de episodios restantes.

    Acciones Finales:
        Si logra recalcular al menos 1 episodio, encola una tarea síncrona de
        actualización del Carrusel (ImageryService.run_carousel) para que
        Google Earth Engine exporte nuevas miniaturas para el frontend.
    """
    db = SessionLocal()
    try:
        episode_svc = EpisodeService(db)
        imagery_svc = ImageryService(db)
        
        # Obtener la version activa de clustering para evitar ForeignKeyViolation
        active_version_id = db.execute(
            text("SELECT id FROM clustering_versions WHERE is_active = true ORDER BY created_at DESC LIMIT 1")
        ).scalar()
        
        if not active_version_id:
            logger.error("No active clustering_version found. Cannot recalculate metrics.")
            sys.exit(1)
            
        episodes = db.query(FireEpisode).filter(
            FireEpisode.status.in_(["active", "monitoring", "extinct", "closed"])
        ).all()
        
        logger.info(f"Found {len(episodes)} episodes to process.")
        
        processed = 0
        failed = 0
        for ep in episodes:
            try:
                # Need to use a nested transaction (savepoint) so we don't abort the whole loop
                with db.begin_nested():
                    # Limitamos los log statements para no saturar la terminal (2300 logs son demasiados)
                    if processed % 100 == 0:
                        logger.info("Recalculating episodes... %s / %s", processed, len(episodes))
                        
                    episode_svc.update_episode_metrics(
                        episode_id=ep.id,
                        clustering_version_id=active_version_id,
                        min_points=3 # Default min_points
                    )
                processed += 1
            except Exception as e:
                failed += 1
                logger.error("Failed to recalculate metrics for %s: %s", ep.id, str(e), exc_info=True)
                # The nested transaction is automatically rolled back, so the session is still valid!
        
        db.commit()
        logger.info(f"Processing finished. Success: {processed}, Failed: {failed}")
        
        if processed > 0 and "--skip-carousel" not in sys.argv:
            logger.info("Triggering carousel refresh...")
            result = imagery_svc.run_carousel(force_refresh=True)
            logger.info(f"Carousel refresh result: {result}")
            db.commit()
            
    except Exception as e:
        logger.error(f"Fatal Error during recalculation: {str(e)}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
