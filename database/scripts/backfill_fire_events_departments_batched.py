#!/usr/bin/env python3
"""
Batched backfill of province/department for existing fire_events.

Uses public.assign_province_department(fe.centroid) and updates only missing fields
via COALESCE, in small batches to avoid timeouts.

Connection resolution (no .env edits required):
  - Prefer DATABASE_URL if present.
  - Else build from DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.

Usage:
  python database/scripts/backfill_fire_events_departments_batched.py
  python database/scripts/backfill_fire_events_departments_batched.py --batch-size 100
  python database/scripts/backfill_fire_events_departments_batched.py --max-batches 10
  python database/scripts/backfill_fire_events_departments_batched.py --sleep-seconds 0.5
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
from dotenv import load_dotenv


DEFAULT_BATCH_SIZE = 100


def load_environment() -> None:
    """
    Load .env from repository root without overriding exported env vars.
    """
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=project_root / ".env", override=False)


def resolve_database_url() -> str:
    """
    Resolve database connection URL with explicit priority:
    1) DATABASE_URL if present.
    2) Build from DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
    """
    direct_url = os.getenv("DATABASE_URL")
    if direct_url:
        return direct_url

    required = ["DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(
            f"Missing DB connection variables: {missing_str}. "
            "Set DATABASE_URL or provide all DB_* variables in .env."
        )

    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "")
    user = os.getenv("DB_USER", "")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    db_name = os.getenv("DB_NAME", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}?sslmode=require"


COUNT_PENDING_SQL = """
SELECT COUNT(*)
FROM public.fire_events
WHERE centroid IS NOT NULL
  AND (province IS NULL OR department IS NULL);
"""


UPDATE_BATCH_SQL = """
UPDATE public.fire_events fe
SET
  province = COALESCE(fe.province, geo.province),
  department = COALESCE(fe.department, geo.department),
  updated_at = NOW()
FROM (
  SELECT fe2.id, apd.province, apd.department
  FROM public.fire_events fe2
  CROSS JOIN LATERAL public.assign_province_department(fe2.centroid) apd
  WHERE fe2.centroid IS NOT NULL
    AND (fe2.province IS NULL OR fe2.department IS NULL)
  LIMIT %(batch_size)s
) geo
WHERE fe.id = geo.id;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batched backfill of fire_events province/department"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Rows per batch update (default: 100)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=0,
        help="Stop after N batches (0 = no limit)",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.0,
        help="Optional pause between batches",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        print("ERROR: --batch-size must be >= 1", file=sys.stderr)
        return 1
    if args.max_batches < 0:
        print("ERROR: --max-batches must be >= 0", file=sys.stderr)
        return 1
    if args.sleep_seconds < 0:
        print("ERROR: --sleep-seconds must be >= 0", file=sys.stderr)
        return 1

    load_environment()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        with psycopg2.connect(database_url) as conn:
            conn.autocommit = False
            with conn.cursor() as cur:
                cur.execute(COUNT_PENDING_SQL)
                pending = int(cur.fetchone()[0])
                print(f"Initial pending: {pending}")

                processed = 0
                batch_idx = 0
                while pending > 0:
                    batch_idx += 1
                    if args.max_batches and batch_idx > args.max_batches:
                        print(f"STOP: reached max-batches={args.max_batches}")
                        break

                    t0 = time.time()
                    cur.execute(UPDATE_BATCH_SQL, {"batch_size": args.batch_size})
                    updated = int(cur.rowcount or 0)
                    conn.commit()
                    elapsed = time.time() - t0

                    processed += updated

                    cur.execute(COUNT_PENDING_SQL)
                    pending = int(cur.fetchone()[0])

                    print(
                        f"Batch {batch_idx}: updated={updated} "
                        f"elapsed_s={elapsed:.2f} processed={processed} pending={pending}"
                    )

                    if updated == 0:
                        print(
                            "STOP: batch updated 0 rows (no progress). "
                            "Check centroid coverage or assign_province_department results."
                        )
                        break

                    if args.sleep_seconds:
                        time.sleep(args.sleep_seconds)

                print(f"Done. processed={processed} pending={pending}")
        return 0
    except Exception as exc:
        print(f"ERROR during backfill: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

