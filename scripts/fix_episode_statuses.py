"""
Fix episode statuses using direct SQL (batch approach).

Applies the corrected _resolve_episode_status logic:
  1. If any linked event has status='active' → episode = 'active'
  2. If last_seen_at is within window (720h/30d) → episode = 'monitoring'
  3. Otherwise → episode = 'extinct'
  
Episodes with status='closed' are skipped.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fix_episode_statuses")

from sqlalchemy import text
from app.db.session import SessionLocal

WINDOW_HOURS = 720

db = SessionLocal()

try:
    db.execute(text("SET statement_timeout = '300s'"))
    logger.info("Step 1: Episodes with at least one active event → status='active'")
    r1 = db.execute(text("""
        UPDATE fire_episodes ep
        SET status = 'active',
            end_date = NULL,
            updated_at = NOW()
        WHERE ep.status != 'closed'
          AND ep.status != 'active'
          AND EXISTS (
              SELECT 1 FROM fire_episode_events fee
              JOIN fire_events fe ON fe.id = fee.event_id
              WHERE fee.episode_id = ep.id
                AND fe.status = 'active'
          )
    """))
    logger.info("  → %d episodes updated to 'active'", r1.rowcount)

    logger.info("Step 2: Remaining non-closed, non-active episodes within window → 'monitoring'")
    r2 = db.execute(text("""
        UPDATE fire_episodes ep
        SET status = 'monitoring',
            end_date = NULL,
            updated_at = NOW()
        WHERE ep.status NOT IN ('closed', 'active')
          AND NOT EXISTS (
              SELECT 1 FROM fire_episode_events fee
              JOIN fire_events fe ON fe.id = fee.event_id
              WHERE fee.episode_id = ep.id
                AND fe.status = 'active'
          )
          AND COALESCE(ep.last_seen_at, ep.start_date) IS NOT NULL
          AND NOW() - COALESCE(ep.last_seen_at, ep.start_date) < INTERVAL ':window hours'
    """.replace(":window", str(WINDOW_HOURS))))
    logger.info("  → %d episodes updated to 'monitoring'", r2.rowcount)

    logger.info("Step 3: Everything else (non-closed, beyond window) → 'extinct'")
    r3 = db.execute(text("""
        UPDATE fire_episodes ep
        SET status = 'extinct',
            updated_at = NOW()
        WHERE ep.status NOT IN ('closed', 'active', 'monitoring')
          AND (
              COALESCE(ep.last_seen_at, ep.start_date) IS NULL
              OR NOW() - COALESCE(ep.last_seen_at, ep.start_date) >= INTERVAL ':window hours'
          )
    """.replace(":window", str(WINDOW_HOURS))))
    logger.info("  → %d episodes remain 'extinct'", r3.rowcount)

    db.commit()
    logger.info("Committed!")

    logger.info("\nFinal state:")
    r4 = db.execute(text("""
        SELECT status, COUNT(*) AS cnt FROM fire_episodes GROUP BY status ORDER BY status
    """)).mappings().all()
    for row in r4:
        logger.info("  %-12s: %s", row['status'], row['cnt'])

    logger.info("\nValidation - Active episodes with active events:")
    r5 = db.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM fire_episodes ep
        WHERE ep.status = 'active'
          AND EXISTS (
              SELECT 1 FROM fire_episode_events fee
              JOIN fire_events fe ON fe.id = fee.event_id
              WHERE fee.episode_id = ep.id AND fe.status = 'active'
          )
    """)).scalar()
    logger.info("  Episodes with active events that are now 'active': %d", r5)

    r6 = db.execute(text("""
        SELECT COUNT(*) AS cnt
        FROM fire_episodes ep
        WHERE ep.status != 'active'
          AND ep.status != 'closed'
          AND EXISTS (
              SELECT 1 FROM fire_episode_events fee
              JOIN fire_events fe ON fe.id = fee.event_id
              WHERE fee.episode_id = ep.id AND fe.status = 'active'
          )
    """)).scalar()
    logger.info("  Non-active non-closed episodes still with active events: %d (should be 0)", r6)

except Exception as e:
    logger.error("Error: %s", e)
    db.rollback()
    sys.exit(1)
finally:
    db.close()
