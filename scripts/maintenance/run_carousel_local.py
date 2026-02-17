"""
Local Carousel Generation Script
================================

This script allows for the manual execution of the carousel generation logic
without the need for the full Celery/Redis stack. It is primarily used for:
1.  **Debugging**: Testing the `ImageryService` logic locally.
2.  **Backfilling/Force Refresh**: Manually regenerating thumbnails for specific episodes.
3.  **Verification**: Confirming that GCS credentials and GEE connectivity are working.

Key Features:
-   **Environment Setup**: Automatically assemblies `DATABASE_URL` from individual `DB_*` env vars if needed.
-   **Targeted Selection**: Implements specific logic to select episodes:
    -   Status is 'active' or 'monitoring'.
    -   OR `end_date` is within the last N days (default 60).
    -   AND `gee_candidate` is True (to ensure data availability).
-   **Dry Run**: Supports a `--dry-run` flag to preview which episodes would be processed.
-   **Force Refresh**: Supports a `--force` flag to regenerate images even if they already exist.

Usage:
    python scripts/run_carousel_local.py [--days 60] [--dry-run] [--force]

Dependencies:
-   `earthengine-api` must be installed and authenticated.
-   `.env` file with DB and GCS credentials must be present.
"""

import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from datetime import datetime, timedelta

# Add project root to path to allow importing app modules
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService
from app.models.episode import FireEpisode
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_episodes_from_logic(db, days_back=60):
    """
    Retrieve episodes based on the documentation logic:
    1.  **Status**: Active or Monitoring (always included).
    2.  **Recency**: Ended within the last `days_back` days (default 60).
    3.  **Constraint**: Must be a `gee_candidate` (Likely to have satellite data).

    Args:
        db (Session): SQLAlchemy session.
        days_back (int): Number of days to look back for closed episodes.

    Returns:
        List[Row]: List of episode rows with id, status, end_date, and gee_candidate.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    query = text("""
        SELECT id, status, end_date, gee_candidate
        FROM fire_episodes
        WHERE (status IN ('active', 'monitoring') OR (end_date >= :cutoff AND end_date IS NOT NULL))
          AND gee_candidate = true
        ORDER BY 
            CASE WHEN status IN ('active', 'monitoring') THEN 0 ELSE 1 END,
            end_date DESC NULLS LAST
    """)
    
    result = db.execute(query, {"cutoff": cutoff_date}).mappings().all()
    return result

def main():
    parser = argparse.ArgumentParser(description="Manual Carousel Generation")
    parser.add_argument("--days", type=int, default=60, help="Days back for recent episodes")
    parser.add_argument("--dry-run", action="store_true", help="Only list episodes, do not generate")
    parser.add_argument("--force", action="store_true", help="Force regeneration of images")
    args = parser.parse_args()

    logger.info("Starting manual carousel generation...")

    # Check environment variables
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "postgres")
        
        if host and user:
            from urllib.parse import quote_plus
            encoded_password = quote_plus(password) if password else ""
            db_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"
            os.environ["DATABASE_URL"] = db_url
            logger.info("Assembled DATABASE_URL from generic DB_* env vars.")
        else:
            logger.error("DATABASE_URL is not set and DB_* variables are incomplete.")
            return

    db = SessionLocal()
    try:
        service = ImageryService(db)
        
        # 1. Identify target episodes
        episodes = get_episodes_from_logic(db, args.days)
        logger.info(f"Found {len(episodes)} candidate episodes (Active + Recent {args.days}d)")
        
        if not episodes:
            logger.warning("No episodes found matching criteria.")
            return

        for ep in episodes:
            logger.info(f"Episode: {ep.id} | Status: {ep.status} | End: {ep.end_date} | GEE: {ep.gee_candidate}")

        if args.dry_run:
            logger.info("Dry run finished. No images generated.")
            return

        # 2. Process each episode
        count = 0
        for ep in episodes:
            try:
                logger.info(f"Processing episode {ep.id}...")
                # We use refresh_episode to target specific IDs regardless of 'active' filter in run_carousel
                res = service.refresh_episode(str(ep.id), force_refresh=args.force)
                logger.info(f"Result for {ep.id}: {res}")
                count += 1
            except Exception as e:
                logger.error(f"Failed to process {ep.id}: {e}")
        
        logger.info(f"Processed {count} episodes.")

    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        db.close()
        logger.info("Finished.")

if __name__ == "__main__":
    main()
