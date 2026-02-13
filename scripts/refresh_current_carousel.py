"""
Refresh Current Carousel Images
===============================

This script identifies episodes that are currently displaying images in the carousel
(i.e., have `slides_data` populated) and manually refreshes their thumbnails.
It works by retrieving their IDs and invoking the worker logic directly.

Usage:
    python scripts/refresh_current_carousel.py [--dry-run]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

# Patch ALLOWED_ORIGINS to avoid Pydantic error in Docker
os.environ["ALLOWED_ORIGINS"] = '["*"]'
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "dummy_secret_key_for_script_execution"

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_episodes_with_slides(db):
    """
    Retrieve IDs of episodes that currently have slides data.
    """
    query = text("""
        SELECT id
        FROM fire_episodes
        WHERE jsonb_array_length(slides_data) > 0
    """)
    result = db.execute(query).mappings().all()
    return result

def ensure_db_url():
    """Ensure DATABASE_URL is set, assembling from components if necessary."""
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
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Refresh Current Carousel Images")
    parser.add_argument("--dry-run", action="store_true", help="Only list episodes, do not regenerate")
    args = parser.parse_args()

    ensure_db_url()
    
    db = SessionLocal()
    try:
        service = ImageryService(db)
        
        episodes = get_episodes_with_slides(db)
        count = len(episodes)
        logger.info(f"Found {count} episodes currently showing in the carousel.")

        if count == 0:
            logger.info("No episodes to process.")
            db.close()
            return
            
        for ep in episodes:
             logger.info(f"Candidate Episode ID: {ep['id']}")

        if args.dry_run:
            logger.info("Dry run finished. No images generated.")
            db.close()
            return
        
        processed = 0
        errors = 0
        
        logger.info("Starting regeneration...")
        for i, ep in enumerate(episodes, 1):
            episode_id = str(ep['id'])
            logger.info(f"[{i}/{count}] Processing episode {episode_id}...")
            try:
                # Force refresh to ensure new thumbnails are generated and uploaded
                result = service.refresh_episode(episode_id, force_refresh=True)
                logger.info(f"Result for {episode_id}: {result}")
                processed += 1
            except Exception as e:
                logger.error(f"Failed to process {episode_id}: {e}")
                errors += 1
                # We attempt to continue with the next one
        
        logger.info(f"Finished. Processed: {processed}, Errors: {errors}")

    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
