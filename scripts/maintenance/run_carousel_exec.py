"""
Ejecucion manual del carousel de thumbnails.

Genera thumbnails para los primeros N episodios del carrusel (default 20,
igual que DEFAULT_CAROUSEL_HOME_LIMIT en imagery_service.py).

Usa _fetch_priority_episodes() del ImageryService para respetar exactamente
el mismo orden y filtros que usa el worker automatico (gee_priority DESC,
status active/monitoring/extinct reciente, gee_candidate=true).

Uso:
    python scripts/maintenance/run_carousel_exec.py [--dry-run] [--force] [--limit 20]
"""
import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# SessionLocal construye la URL via app.core.config.Settings.assemble_db_connection()
# que lee DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME con URL-encoding correcto.
from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService, DEFAULT_CAROUSEL_HOME_LIMIT
import contextlib
import app.core.gee_semaphore as _gee_sem_module

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Carousel thumbnail generation (manual)")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar candidatos, sin procesar")
    parser.add_argument("--force", action="store_true", help="Forzar regeneracion aunque ya exista imagen")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_CAROUSEL_HOME_LIMIT,
        help=f"Maximo de episodios a procesar (default: {DEFAULT_CAROUSEL_HOME_LIMIT}, igual al carrusel)",
    )
    parser.add_argument(
        "--no-semaphore",
        action="store_true",
        help="Deshabilitar el semaforo Redis de GEE (usar en ejecucion local sin Redis)",
    )
    args = parser.parse_args()

    if args.no_semaphore:
        @contextlib.contextmanager
        def _noop_acquire_sync(timeout=60):
            yield
        _gee_sem_module.gee_semaphore.acquire_sync = _noop_acquire_sync
        logger.info("GEE semaphore deshabilitado (--no-semaphore).")

    db = SessionLocal()
    try:
        service = ImageryService(db)

        # Usa el mismo metodo que el worker automatico: mismos filtros, mismo orden
        candidates = service._fetch_priority_episodes(limit=args.limit)
        logger.info(
            "Candidatos del carousel: %d (limite=%d, misma logica que el worker)",
            len(candidates), args.limit,
        )

        for ep in candidates:
            logger.info("  Episode %s | gee_priority=%s | start=%s", ep.id, ep.gee_priority, ep.start_date)

        if args.dry_run:
            logger.info("--- Dry-run finalizado. No se generaron imagenes. ---")
            return

        logger.info("Iniciando generacion de thumbnails...")
        total = 0
        updated = 0
        errors = []

        for ep in candidates:
            try:
                result = service.refresh_episode(ep.id, force_refresh=args.force)
                status_result = result.get("status", "unknown")
                logger.info("Episode %s → %s", ep.id, status_result)
                if status_result == "updated":
                    updated += 1
                total += 1
            except Exception as exc:
                logger.error("Episode %s → ERROR: %s", ep.id, exc)
                errors.append({"episode_id": ep.id, "error": str(exc)})
                db.rollback()

        logger.info(
            "=== RESULTADO: processed=%d updated=%d skipped=%d errors=%d ===",
            total, updated, total - updated - len(errors), len(errors),
        )
        if errors:
            logger.warning("Episodios con error: %s", [e["episode_id"] for e in errors])

    except Exception:
        logger.exception("Error fatal en carousel exec")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
