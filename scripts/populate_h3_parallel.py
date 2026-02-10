#!/usr/bin/env python3
"""
Parallel H3 population for fire_events - 4 workers, batches of 500
Uploads to Supabase with optimized performance
"""

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple, Optional

import psycopg2
from dotenv import load_dotenv

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

try:
    import h3
    H3_AVAILABLE = True
    print(f"✓ H3 library available: {h3.__version__}")
except ImportError:
    h3 = None
    H3_AVAILABLE = False
    print("❌ H3 library not available")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(threadName)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_H3_RESOLUTION = 7
BATCH_SIZE = 500
NUM_WORKERS = 4


def get_db_params() -> dict:
    """Build psycopg2 connection params from env."""
    return {
        "host": os.getenv("DB_HOST"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "sslmode": os.getenv("DB_SSLMODE", "require"),
    }


def lat_lng_to_h3(lat: float, lon: float, resolution: int) -> Optional[int]:
    """Convert lat/lon to H3 index using Python library and return as integer."""
    try:
        h3_str = h3.latlng_to_cell(lat, lon, resolution)
        return int(h3_str, 16)
    except Exception as exc:
        logger.warning("H3 conversion failed for (%.6f, %.6f): %s", lat, lon, exc)
        return None


def get_batch(worker_id: int, batch_num: int) -> List[Tuple]:
    """Get a batch of fire events to process."""
    conn = psycopg2.connect(**get_db_params())
    conn.autocommit = True
    cur = conn.cursor()
    
    offset = batch_num * BATCH_SIZE
    limit = BATCH_SIZE
    
    try:
        cur.execute("""
            SELECT id, ST_Y(centroid::geometry) as lat, ST_X(centroid::geometry) as lon
            FROM fire_events
            WHERE centroid IS NOT NULL 
              AND h3_index IS NULL
              AND ST_X(centroid::geometry) BETWEEN -180 AND 180
              AND ST_Y(centroid::geometry) BETWEEN -90 AND 90
            ORDER BY id
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        rows = cur.fetchall()
        logger.info(f"Worker {worker_id}: Retrieved {len(rows)} fire events (batch {batch_num})")
        return rows
        
    finally:
        cur.close()
        conn.close()


def process_batch(worker_id: int, batch_data: List[Tuple]) -> int:
    """Process a batch of fire events and update H3 indexes."""
    if not batch_data:
        return 0
    
    conn = psycopg2.connect(**get_db_params())
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        updates = []
        for fire_id, lat, lon in batch_data:
            h3_index = lat_lng_to_h3(lat, lon, DEFAULT_H3_RESOLUTION)
            if h3_index:
                updates.append((h3_index, fire_id))
        
        if updates:
            cur.executemany(
                "UPDATE fire_events SET h3_index = %s WHERE id = %s",
                updates
            )
            logger.info(f"Worker {worker_id}: Updated {len(updates)} fire events")
            return len(updates)
        else:
            logger.warning(f"Worker {worker_id}: No valid H3 conversions in batch")
            return 0
            
    except Exception as exc:
        logger.error(f"Worker {worker_id}: Batch processing failed: {exc}")
        return 0
    finally:
        cur.close()
        conn.close()


def worker_process(worker_id: int, batch_numbers: List[int]) -> int:
    """Worker function to process multiple batches."""
    total_processed = 0
    
    for batch_num in batch_numbers:
        logger.info(f"Worker {worker_id}: Processing batch {batch_num}")
        
        # Get batch data
        batch_data = get_batch(worker_id, batch_num)
        
        if not batch_data:
            logger.info(f"Worker {worker_id}: No more data available")
            break
        
        # Process batch
        processed = process_batch(worker_id, batch_data)
        total_processed += processed
        
        # Small delay to avoid overwhelming database
        time.sleep(0.1)
    
    logger.info(f"Worker {worker_id}: Completed processing {total_processed} fire events")
    return total_processed


def check_progress():
    """Check current H3 population progress."""
    conn = psycopg2.connect(**get_db_params())
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT COUNT(*) FROM fire_events")
        total_fires = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM fire_events WHERE h3_index IS NOT NULL")
        current_h3 = cur.fetchone()[0]
        
        percentage = (current_h3 / total_fires) * 100
        logger.info(f"Progress: {current_h3}/{total_fires} ({percentage:.1f}%)")
        
        return current_h3, total_fires, percentage
        
    finally:
        cur.close()
        conn.close()


def refresh_materialized_view():
    """Refresh the h3_recurrence_stats materialized view."""
    logger.info("Refreshing h3_recurrence_stats materialized view...")
    
    conn = psycopg2.connect(**get_db_params())
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute("REFRESH MATERIALIZED VIEW h3_recurrence_stats")
        logger.info("✓ Materialized view refreshed")
    except Exception as exc:
        logger.warning("Could not refresh materialized view: %s", exc)
    finally:
        cur.close()
        conn.close()


def main():
    """Main execution function with parallel workers."""
    print("=== Parallel H3 Population for fire_events ===")
    print(f"Configuration: {NUM_WORKERS} workers, {BATCH_SIZE} batch size")
    
    if not H3_AVAILABLE:
        print("❌ H3 library not available. Install with: pip install h3")
        return False
    
    try:
        # Check initial progress
        current_h3, total_fires, percentage = check_progress()
        
        if percentage >= 90:
            logger.info("H3 indexes already sufficiently populated")
            return True
        
        # Calculate total batches needed
        remaining = total_fires - current_h3
        total_batches = (remaining // BATCH_SIZE) + 1
        logger.info(f"Need to process approximately {remaining} fire events in {total_batches} batches")
        
        # Distribute batches among workers
        batch_assignments = []
        for i in range(total_batches):
            worker_id = i % NUM_WORKERS
            batch_assignments.append((worker_id, i))
        
        # Group batches by worker
        worker_batches = {i: [] for i in range(NUM_WORKERS)}
        for worker_id, batch_num in batch_assignments:
            worker_batches[worker_id].append(batch_num)
        
        logger.info(f"Batch distribution: {[(wid, len(batches)) for wid, batches in worker_batches.items()]}")
        
        # Start parallel processing
        start_time = time.time()
        total_processed = 0
        
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            # Submit worker tasks
            futures = []
            for worker_id in range(NUM_WORKERS):
                future = executor.submit(worker_process, worker_id, worker_batches[worker_id])
                futures.append((worker_id, future))
            
            # Wait for completion and collect results
            for worker_id, future in futures:
                try:
                    processed = future.result()
                    total_processed += processed
                    logger.info(f"Worker {worker_id} completed: {processed} fire events")
                except Exception as exc:
                    logger.error(f"Worker {worker_id} failed: {exc}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Parallel processing completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total processed: {total_processed} fire events")
        
        # Final progress check
        final_h3, final_total, final_percentage = check_progress()
        
        # Refresh materialized view
        refresh_materialized_view()
        
        print("\n=== H3 Population Complete ===")
        print(f"Final result: {final_h3}/{final_total} ({final_percentage:.1f}%)")
        print(f"Processing rate: {total_processed/elapsed_time:.1f} fire events/second")
        
        return final_percentage >= 90
        
    except Exception as exc:
        logger.error("H3 population failed: %s", exc)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
