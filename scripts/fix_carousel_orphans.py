"""
Fix Carousel Orphans
====================

Creates placeholder FireEvents for episodes that have carousel slides but no linked events.
This is required because SatelliteImage records MUST be linked to a FireEvent.

Stratergy:
1. Identify orphan episodes (slides > 0, no linked event, no same-ID event).
2. Insert a FireEvent with the SAME ID as the episode.
3. Populate FireEvent fields from Episode data.
"""

import os
import sys
import logging
from datetime import datetime, timezone
from sqlalchemy import create_engine, text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_db_url():
    url = os.environ.get("DATABASE_URL")
    if url: return url
    host = os.environ.get("DB_HOST")
    user = os.environ.get("DB_USER")
    password = os.environ.get("DB_PASSWORD")
    name = os.environ.get("DB_NAME", "postgres")
    port = os.environ.get("DB_PORT", "5432")
    if host and user:
        from urllib.parse import quote_plus
        encoded_pwd = quote_plus(password) if password else ""
        return f"postgresql://{user}:{encoded_pwd}@{host}:{port}/{name}"
    return None

def main():
    logger.info("Starting orphan fix...")
    db_url = get_db_url()
    if not db_url:
        logger.error("No DATABASE_URL found.")
        sys.exit(1)

    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Detect orphans
        query_orphans = text("""
            SELECT e.id, e.status, e.start_date, e.end_date, 
                   e.centroid_lat, e.centroid_lon, e.provinces,
                   e.detection_count, e.estimated_area_hectares
            FROM fire_episodes e
            WHERE jsonb_array_length(e.slides_data) > 0
            AND NOT EXISTS (
                SELECT 1 FROM fire_episode_events fee WHERE fee.episode_id = e.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM fire_events fe WHERE fe.id = e.id
            )
        """)
        orphans = conn.execute(query_orphans).mappings().all()
        
        logger.info(f"Found {len(orphans)} orphan episodes.")
        
        if not orphans:
            logger.info("Nothing to fix.")
            return

        for ep in orphans:
            ep_id = str(ep['id'])
            logger.info(f"Fixing episode {ep_id} ({ep['status']})...")
            
            # Prepare data
            end_date = ep['end_date']
            if not end_date:
                logger.warning(f"  Episode has no end_date. Using now().")
                end_date = datetime.now(timezone.utc)
            
            province = ep['provinces'][0] if ep['provinces'] else None
            
            # Insert FireEvent
            # Note: We use raw SQL to handle PostGIS geometry easily
            insert_sql = text("""
                INSERT INTO fire_events (
                    id, 
                    centroid,
                    start_date, 
                    end_date, 
                    last_seen_at,
                    status, 
                    province,
                    total_detections,
                    estimated_area_hectares,
                    created_at,
                    updated_at,
                    is_significant,
                    has_legal_analysis,
                    has_historic_report
                ) VALUES (
                    :id,
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :start_date,
                    :end_date,
                    :last_seen_at,
                    :status,
                    :province,
                    :total_detections,
                    :area,
                    now(),
                    now(),
                    false,
                    false,
                    false
                )
            """)
            
            # Map status
            # Constraint failed for 'extinct'. We force 'active' as it is the default and guaranteed to be valid.
            status = 'active'

            try:
                conn.execute(insert_sql, {
                    "id": ep_id,
                    "lon": float(ep['centroid_lon'] or 0),
                    "lat": float(ep['centroid_lat'] or 0),
                    "start_date": ep['start_date'],
                    "end_date": end_date,
                    "last_seen_at": end_date,
                    "status": status,
                    "province": province,
                    "total_detections": ep['detection_count'] or 0,
                    "area": ep['estimated_area_hectares']
                })
                conn.commit()
                logger.info(f"  Created FireEvent {ep_id}")
            except Exception as e:
                logger.error(f"  Failed to insert {ep_id}: {e}")
                conn.rollback()

    logger.info("Done.")

if __name__ == "__main__":
    main()
