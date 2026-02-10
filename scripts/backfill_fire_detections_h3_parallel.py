#!/usr/bin/env python3
"""
Parallel backfill for fire_detections.h3_index (UC-F08R).

Commands:
  - Dry-run (one batch per worker):
      python scripts/backfill_fire_detections_h3_parallel.py --dry-run
  - Run with 4 workers, batch size 2000:
      python scripts/backfill_fire_detections_h3_parallel.py --workers 4 --batch-size 2000
  - Limit total rows (useful for testing):
      python scripts/backfill_fire_detections_h3_parallel.py --max-rows 10000
  - Throttle between batches (milliseconds):
      python scripts/backfill_fire_detections_h3_parallel.py --sleep-ms 250

Notes:
  - Uses SELECT ... FOR UPDATE SKIP LOCKED to split work safely across workers.
  - Each batch is updated with a single statement (execute_values).
  - Resolution is read from H3_RESOLUTION or system_parameters.h3_resolution; fallback is 8.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from multiprocessing import Event, Lock, Process, Value
from pathlib import Path
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# --- ENV / PATH ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
load_dotenv(dotenv_path=BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

DEFAULT_H3_RESOLUTION = 8

try:
    import h3  # type: ignore

    H3_AVAILABLE = True
except ImportError:
    h3 = None
    H3_AVAILABLE = False


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


def get_connection():
    """Create a psycopg2 connection."""
    params = get_db_params()
    if not params["host"] or not params["password"]:
        raise RuntimeError("Credenciales incompletas. Revisá DB_HOST / DB_PASSWORD.")
    return psycopg2.connect(**params)


def resolve_h3_resolution() -> int:
    """Resolve H3 resolution from env or system_parameters."""
    env_value = os.getenv("H3_RESOLUTION")
    if env_value:
        try:
            return int(env_value)
        except (TypeError, ValueError):
            logger.warning("H3_RESOLUTION invalido: %s", env_value)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT param_value FROM system_parameters WHERE param_key = 'h3_resolution'"
                )
                row = cur.fetchone()
    except Exception as exc:  # pragma: no cover
        logger.warning("No se pudo leer system_parameters: %s", exc)
        return DEFAULT_H3_RESOLUTION

    if not row:
        return DEFAULT_H3_RESOLUTION

    value = row[0]
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return DEFAULT_H3_RESOLUTION
    return DEFAULT_H3_RESOLUTION


def compute_h3_index(lat: float, lon: float, resolution: int) -> int:
    """Compute H3 index for a given lat/lon."""
    if not H3_AVAILABLE:
        raise RuntimeError("h3 library no disponible; instala el paquete 'h3'")
    if hasattr(h3, "latlng_to_cell"):
        h3_str = h3.latlng_to_cell(lat, lon, resolution)
    else:
        h3_str = h3.geo_to_h3(lat, lon, resolution)
    return int(h3_str, 16)


def count_missing() -> int:
    """Count detections without h3_index."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fire_detections WHERE h3_index IS NULL")
            return int(cur.fetchone()[0] or 0)


def worker_loop(
    worker_id: int,
    *,
    batch_size: int,
    resolution: int,
    dry_run: bool,
    max_rows: Optional[int],
    sleep_ms: int,
    total_updated: Value,
    stop_event: Event,
    lock: Lock,
):
    """Worker loop: claim batches with SKIP LOCKED, compute H3, batch update."""
    conn = get_connection()
    try:
        while not stop_event.is_set():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, latitude, longitude
                      FROM fire_detections
                     WHERE h3_index IS NULL
                     ORDER BY detected_at ASC
                     LIMIT %s
                     FOR UPDATE SKIP LOCKED
                    """,
                    (batch_size,),
                )
                rows = cur.fetchall()

                if not rows:
                    conn.commit()
                    logger.info("Worker %s: sin filas pendientes.", worker_id)
                    break

                payload = []
                for row in rows:
                    det_id, lat, lon = row
                    if lat is None or lon is None:
                        continue
                    h3_index = compute_h3_index(float(lat), float(lon), resolution)
                    payload.append((h3_index, str(det_id)))

                if dry_run:
                    conn.rollback()
                    logger.info(
                        "Worker %s: dry-run batch=%s actualizable=%s",
                        worker_id,
                        len(rows),
                        len(payload),
                    )
                    break

                if payload:
                    execute_values(
                        cur,
                        """
                        UPDATE fire_detections AS fd
                           SET h3_index = data.h3_index
                          FROM (VALUES %s) AS data(h3_index, id)
                         WHERE fd.id = data.id::uuid
                        """,
                        payload,
                        template="(%s, %s)",
                    )
                conn.commit()

                with lock:
                    total_updated.value += len(payload)
                    total = total_updated.value
                    if max_rows and total >= max_rows:
                        stop_event.set()

                logger.info(
                    "Worker %s: batch=%s updated=%s total=%s",
                    worker_id,
                    len(rows),
                    len(payload),
                    total_updated.value,
                )

            if sleep_ms:
                time.sleep(sleep_ms / 1000.0)
    finally:
        conn.close()


def main():
    """
    CLI:
      --workers N       Number of parallel workers (default: 4)
      --batch-size N    Rows per batch (default: 2000)
      --max-rows N      Stop after N updates (optional)
      --dry-run         Do not write to DB
      --sleep-ms N      Sleep between batches (ms)
    """
    parser = argparse.ArgumentParser(
        description="Parallel backfill for fire_detections.h3_index."
    )
    parser.add_argument("--workers", type=int, default=4, help="Workers count")
    parser.add_argument("--batch-size", type=int, default=2000, help="Batch size")
    parser.add_argument("--max-rows", type=int, default=None, help="Max rows to update")
    parser.add_argument("--dry-run", action="store_true", help="Do not update DB")
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=0,
        help="Sleep between batches (milliseconds)",
    )
    args = parser.parse_args()

    if not H3_AVAILABLE:
        raise RuntimeError("h3 library no disponible; instala el paquete 'h3'")

    resolution = resolve_h3_resolution()
    missing = count_missing()
    logger.info(
        "Backfill paralelo: missing=%s resolution=%s workers=%s batch=%s dry_run=%s",
        missing,
        resolution,
        args.workers,
        args.batch_size,
        args.dry_run,
    )

    total_updated = Value("i", 0)
    stop_event = Event()
    lock = Lock()

    workers = [
        Process(
            target=worker_loop,
            kwargs={
                "worker_id": idx + 1,
                "batch_size": args.batch_size,
                "resolution": resolution,
                "dry_run": args.dry_run,
                "max_rows": args.max_rows,
                "sleep_ms": args.sleep_ms,
                "total_updated": total_updated,
                "stop_event": stop_event,
                "lock": lock,
            },
        )
        for idx in range(max(1, args.workers))
    ]

    start = datetime.now()
    for proc in workers:
        proc.start()
    for proc in workers:
        proc.join()

    elapsed = datetime.now() - start
    logger.info(
        "Backfill finalizado. updated=%s elapsed=%s",
        total_updated.value,
        elapsed,
    )


if __name__ == "__main__":
    main()
