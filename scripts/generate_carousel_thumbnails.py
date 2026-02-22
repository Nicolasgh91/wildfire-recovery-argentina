"""
Generate Carousel Thumbnails for Missing Episodes
=================================================

This script generates thumbnails for the 15 episodes currently shown in the carousel
that don't have slides_data yet, complementing the 5 episodes that already exist.

Usage:
    python scripts/generate_carousel_thumbnails.py [--dry-run] [--force]

Dependencies:
- Docker worker infrastructure must be running
- GEE and GCS credentials must be configured
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.db.session import SessionLocal
from app.services.imagery_service import ImageryService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# The 15 episodes that need thumbnails (from carousel query)
EPISODES_NEEDING_THUMBNAILS = [
    "2bda1681-f5fa-4fe4-ab0c-65e76ca291c7",
    "7a13787c-2b58-4cbf-8888-82023072e918", 
    "27748987-9d32-49be-ad82-b067ec69aa14",
    "ceb2fed5-144e-48d6-be36-a49976e76bd4",
    "cea11d48-cedf-44e2-ae2a-9f27bdd39830",
    "733492b5-8639-41b1-a5f0-4130b4f8c7e8",
    "ab63e46d-081f-4adc-95cf-ed269c36256d",
    "d1cfe73e-f2ca-44ef-962b-cff829fce8e9",
    "a2cad079-5aeb-421a-a3c0-921f398afe9c",
    "9f9cffba-8722-482b-a77b-b617ee1ebe8e",
    "92aa64e3-2411-4664-b378-a89843c3473e",
    "7bf8bea3-502e-4fc6-b327-34fd209d87fd",
    "b1009131-1e39-42cd-a5ba-03e832fcd401",
    "f58f9cba-3c59-4a8c-adf7-cdf929d6f383",
    "4714ae26-d222-4d9f-98ca-fab700918740"
]

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

def verify_episodes_exist(db, episode_ids):
    """Verify that all target episodes exist and are gee_candidates."""
    from sqlalchemy import text
    
    placeholders = ','.join([f"'{ep_id}'" for ep_id in episode_ids])
    query = text(f"""
        SELECT id, status, gee_candidate, jsonb_array_length(slides_data) as slide_count
        FROM fire_episodes 
        WHERE id IN ({placeholders})
    """)
    
    result = db.execute(query).mappings().all()
    
    logger.info(f"Found {len(result)} episodes in database:")
    for row in result:
        has_thumbs = "YES" if row.slide_count and row.slide_count > 0 else "NO"
        logger.info(f"  {row.id}: status={row.status}, gee_candidate={row.gee_candidate}, slides={has_thumbs}")
    
    missing_episodes = set(episode_ids) - {str(row['id']) for row in result}
    if missing_episodes:
        logger.warning(f"Episodes not found in database: {missing_episodes}")
    
    return result

def main():
    parser = argparse.ArgumentParser(description="Generate Carousel Thumbnails")
    parser.add_argument("--dry-run", action="store_true", help="Only list episodes, do not generate")
    parser.add_argument("--force", action="store_true", help="Force regeneration even if thumbnails exist")
    args = parser.parse_args()

    ensure_db_url()
    
    logger.info("Starting carousel thumbnail generation...")
    logger.info(f"Target episodes: {len(EPISODES_NEEDING_THUMBNAILS)}")
    
    db = SessionLocal()
    try:
        # Verify episodes exist
        episodes = verify_episodes_exist(db, EPISODES_NEEDING_THUMBNAILS)
        
        if not episodes:
            logger.error("No episodes found to process.")
            return
        
        service = ImageryService(db)
        
        if args.dry_run:
            logger.info("Dry run mode - no thumbnails will be generated.")
            logger.info("Use without --dry-run to actually generate thumbnails.")
            return
        
        # Process each episode
        processed = 0
        errors = 0
        
        logger.info("Starting thumbnail generation...")
        for i, episode_id in enumerate(EPISODES_NEEDING_THUMBNAILS, 1):
            logger.info(f"[{i}/{len(EPISODES_NEEDING_THUMBNAILS)}] Processing episode {episode_id}...")
            
            try:
                # Use refresh_episode to generate thumbnails
                result = service.refresh_episode(episode_id, force_refresh=args.force)
                logger.info(f"Result for {episode_id}: {result}")
                processed += 1
                
            except Exception as e:
                logger.error(f"Failed to process {episode_id}: {e}")
                errors += 1
                # Continue with next episode
        
        logger.info(f"Thumbnail generation completed. Processed: {processed}, Errors: {errors}")
        
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
    finally:
        db.close()
        logger.info("Finished.")

if __name__ == "__main__":
    main()
