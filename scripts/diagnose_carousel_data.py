import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_db_url():
    """Builds the DB URL from env vars present in the container."""
    # Check for full URL
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    
    # Check components
    host = os.environ.get("DB_HOST")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    name = os.environ.get("DB_NAME", "postgres")
    port = os.environ.get("DB_PORT", "5432")
    
    if host and user:
        from urllib.parse import quote_plus
        # Handle empty/missing password
        encoded_pwd = quote_plus(password) if password else ""
        return f"postgresql://{user}:{encoded_pwd}@{host}:{port}/{name}"
    
    return None

def main():
    logger.info("Starting diagnosis...")
    
    db_url = get_db_url()
    if not db_url:
        logger.error("Could not construct DATABASE_URL. Check DB_HOST/DB_USER env vars.")
        sys.exit(1)
        
    try:
        # Create engine directly (no pooling options needed for script)
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # 1. Get episodes that have slides
            query = text("""
                SELECT id, status, jsonb_array_length(slides_data) as slide_count
                FROM fire_episodes
                WHERE jsonb_array_length(slides_data) > 0
            """)
            result = conn.execute(query).mappings().all()
            
            total_episodes = len(result)
            logger.info(f"Found {total_episodes} episodes with active carousel slides.")
            
            missing_event_count = 0
            no_linked_but_same_id = 0
            
            logger.info(f"{'EPISODE ID':<38} | {'STATUS':<10} | {'LINKED':<6} | {'SAME ID':<7} | {'RESULT'}")
            logger.info("-" * 85)
            
            for row in result:
                ep_id = str(row['id'])
                
                # Check linked events
                q_linked = text("SELECT count(*) FROM fire_episode_events WHERE episode_id = :eid")
                linked_count = conn.execute(q_linked, {"eid": ep_id}).scalar()
                
                # Check same ID events
                q_same = text("SELECT count(*) FROM fire_events WHERE id = :eid")
                same_id_count = conn.execute(q_same, {"eid": ep_id}).scalar()
                
                has_valid_event = (linked_count > 0) or (same_id_count > 0)
                
                if not has_valid_event:
                    status_res = "MISSING_EVENT"
                    missing_event_count += 1
                elif linked_count == 0 and same_id_count > 0:
                    status_res = "Fallback OK"
                    no_linked_but_same_id += 1
                else:
                    status_res = "OK"

                logger.info(f"{ep_id:<38} | {row['status']:<10} | {linked_count:<6} | {same_id_count:<7} | {status_res}")
                
            logger.info("-" * 85)
            logger.info(f"Summary:")
            logger.info(f"Total with slides: {total_episodes}")
            logger.info(f"Missing any event: {missing_event_count}")
            logger.info(f"Using fallback ID: {no_linked_but_same_id}")

    except Exception as e:
        logger.exception(f"Fatal error during diagnosis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
