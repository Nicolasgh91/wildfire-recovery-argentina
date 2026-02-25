"""
Validacion SQL de las migrations del flujo de thumbnails.
Verifica estado de la DB tras T-01, T-02, T-03, T-04, T-05, T-09.

Uso:
    python scripts/maintenance/validate_carousel_migrations.py
"""
import os, sys, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from dotenv import load_dotenv; load_dotenv()
from app.db.session import SessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PASS = "PASS"
FAIL = "FAIL"

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    logger.info("[%s] %s%s", status, label, f" — {detail}" if detail else "")
    return condition


def main():
    db = SessionLocal()
    results = []
    try:
        # Q1: extinct_at columna existe en fire_episodes
        col = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='fire_episodes' AND column_name='extinct_at'"
        )).fetchone()
        results.append(check("Q1 fire_episodes.extinct_at existe", col is not None))

        # Q2: indice parcial en fire_episodes.extinct_at
        idx1 = db.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname='idx_fire_episodes_extinct_at'"
        )).fetchone()
        results.append(check("Q2 idx_fire_episodes_extinct_at existe", idx1 is not None))

        # Q3: episode_id columna en satellite_images
        col2 = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='satellite_images' AND column_name='episode_id'"
        )).fetchone()
        results.append(check("Q3 satellite_images.episode_id existe", col2 is not None))

        # Q4: indice en satellite_images.episode_id
        idx2 = db.execute(text(
            "SELECT indexname FROM pg_indexes WHERE indexname='idx_satellite_images_episode_id'"
        )).fetchone()
        results.append(check("Q4 idx_satellite_images_episode_id existe", idx2 is not None))

        # Q5: backfill satellite_images.episode_id
        total = db.execute(text("SELECT COUNT(*) FROM satellite_images")).scalar()
        backfilled = db.execute(text("SELECT COUNT(*) FROM satellite_images WHERE episode_id IS NOT NULL")).scalar()
        results.append(check(
            "Q5 satellite_images episode_id backfilled",
            total == 0 or backfilled > 0,
            f"{backfilled}/{total}"
        ))

        # Q6: carousel_extinct_grace_days en system_parameters
        sp = db.execute(text(
            "SELECT param_value FROM system_parameters WHERE param_key='carousel_extinct_grace_days'"
        )).fetchone()
        results.append(check("Q6 carousel_extinct_grace_days en system_parameters", sp is not None, str(sp[0] if sp else None)))

        # Q7: episodios extinct con extinct_at NULL (deben ser 0 tras backfill)
        null_extinct = db.execute(text(
            "SELECT COUNT(*) FROM fire_episodes WHERE status='extinct' AND extinct_at IS NULL"
        )).scalar()
        results.append(check("Q7 no episodios extinct sin extinct_at", null_extinct == 0, f"{null_extinct} sin fecha"))

        # Q8: distribucion de estados actual
        rows = db.execute(text(
            "SELECT status, COUNT(*) FROM fire_episodes GROUP BY status ORDER BY 2 DESC"
        )).fetchall()
        logger.info("Q8 Distribucion fire_episodes: %s", dict(rows))

        # Q9: episodios que el carousel procesaria con nueva logica
        extinct_recent = db.execute(text(
            "SELECT COUNT(*) FROM fire_episodes "
            "WHERE status='extinct' AND extinct_at IS NOT NULL "
            "AND extinct_at > NOW() - INTERVAL '30 days' AND gee_candidate = true"
        )).scalar()
        active_mon = db.execute(text(
            "SELECT COUNT(*) FROM fire_episodes "
            "WHERE status IN ('active','monitoring') AND gee_candidate = true"
        )).scalar()
        logger.info("Q9 Candidatos carousel — active/monitoring: %d, extinct recientes: %d, total: %d",
                    active_mon, extinct_recent, active_mon + extinct_recent)

        # Q10: FK constraint en satellite_images.episode_id apunta a fire_episodes
        fk = db.execute(text("""
            SELECT tc.constraint_name
              FROM information_schema.table_constraints tc
              JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
             WHERE tc.table_name = 'satellite_images'
               AND kcu.column_name = 'episode_id'
               AND tc.constraint_type = 'FOREIGN KEY'
        """)).fetchone()
        results.append(check("Q10 FK satellite_images.episode_id -> fire_episodes", fk is not None))

        # Resumen
        passed = sum(1 for r in results if r)
        total_checks = len(results)
        logger.info("--- RESULTADO: %d/%d checks pasaron ---", passed, total_checks)
        if passed < total_checks:
            sys.exit(1)

    except Exception:
        logger.exception("Error en validacion")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
