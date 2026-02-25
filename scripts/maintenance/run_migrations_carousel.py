"""
Migrations para el flujo de thumbnails del carrusel.

T-01: Indice parcial en fire_episodes.extinct_at
T-02: episode_id FK nullable en satellite_images + backfill + indice
T-09: system_parameters carousel_extinct_grace_days=30

Uso:
    python scripts/maintenance/run_migrations_carousel.py [--dry-run]
"""
import os, sys, argparse, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv; load_dotenv()
from app.db.session import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MIGRATIONS = [
    # T-01: indice parcial extinct_at (columna ya existe)
    (
        "T-01a",
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_fire_episodes_extinct_at
          ON fire_episodes (extinct_at)
          WHERE status = 'extinct'
        """
    ),
    # T-02: episode_id en satellite_images
    (
        "T-02a",
        """
        ALTER TABLE satellite_images
          ADD COLUMN IF NOT EXISTS episode_id UUID
          REFERENCES fire_episodes(id) ON DELETE SET NULL
        """
    ),
    (
        "T-02b-backfill",
        """
        UPDATE satellite_images si
           SET episode_id = fee.episode_id
          FROM fire_episode_events fee
         WHERE si.fire_event_id = fee.event_id
           AND si.episode_id IS NULL
        """
    ),
    (
        "T-02c-index",
        """
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_satellite_images_episode_id
          ON satellite_images (episode_id)
          WHERE episode_id IS NOT NULL
        """
    ),
    # T-09: system_parameters
    (
        "T-09",
        """
        INSERT INTO system_parameters (param_key, param_value)
        VALUES ('carousel_extinct_grace_days', '{"unit": "days", "value": 30}')
        ON CONFLICT (param_key) DO UPDATE
          SET param_value = EXCLUDED.param_value
        """
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        for name, sql in MIGRATIONS:
            logger.info("[%s] Ejecutando...", name)
            if args.dry_run:
                logger.info("[%s] DRY-RUN: omitido", name)
                continue
            # CONCURRENTLY no puede correr dentro de una transaction explicita
            if "CONCURRENTLY" in sql:
                db.execute(text("COMMIT"))
                db.execute(text(sql.strip()))
                logger.info("[%s] OK (CONCURRENTLY)", name)
            else:
                r = db.execute(text(sql.strip()))
                rowcount = getattr(r, "rowcount", None)
                if rowcount is not None and rowcount >= 0:
                    logger.info("[%s] OK — %d filas afectadas", name, rowcount)
                else:
                    logger.info("[%s] OK", name)
                db.commit()

        # Verificacion final
        logger.info("--- Verificacion ---")
        idx1 = db.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_fire_episodes_extinct_at'"
        )).fetchone()
        logger.info("idx_fire_episodes_extinct_at: %s", "OK" if idx1 else "FALTA")

        col = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='satellite_images' AND column_name='episode_id'"
        )).fetchone()
        logger.info("satellite_images.episode_id: %s", "OK" if col else "FALTA")

        idx2 = db.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname = 'idx_satellite_images_episode_id'"
        )).fetchone()
        logger.info("idx_satellite_images_episode_id: %s", "OK" if idx2 else "FALTA")

        sp = db.execute(text(
            "SELECT param_value FROM system_parameters "
            "WHERE param_key = 'carousel_extinct_grace_days'"
        )).fetchone()
        logger.info("carousel_extinct_grace_days: %s", sp[0] if sp else "FALTA")

        backfill = db.execute(text(
            "SELECT COUNT(*) FROM satellite_images WHERE episode_id IS NOT NULL"
        )).scalar()
        total = db.execute(text("SELECT COUNT(*) FROM satellite_images")).scalar()
        logger.info("satellite_images con episode_id: %d / %d", backfill, total)

    except Exception:
        db.rollback()
        logger.exception("Error en migration")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
