#!/usr/bin/env python3
"""
Load Argentine departments from local GeoJSON into public.regions.

Usage:
    python database/scripts/load_departments_georef.py
    python database/scripts/load_departments_georef.py --file data/departments/departments.json
    python database/scripts/load_departments_georef.py --batch-size 50

Requirements:
    - DATABASE_URL set in environment or present in project .env.
    - A local GeoJSON FeatureCollection with department geometries.

Safety rules:
    - Abort if regions already has >=500 DEPARTAMENTO rows.
    - Continue only when DEPARTAMENTO count is 0 (full load).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_batch


DEFAULT_FILE = Path("data/departments/departments.json")
DEFAULT_BATCH_SIZE = 50


def load_environment() -> None:
    """
    Load .env from repository root without overriding exported env vars.
    """
    project_root = Path(__file__).resolve().parents[2]
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path=dotenv_path, override=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load department geometries into public.regions"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help="Path to departments GeoJSON (FeatureCollection)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Rows per insert batch (default: 50)",
    )
    return parser.parse_args()


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


def load_geojson(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Expected a GeoJSON FeatureCollection")
    features = payload.get("features")
    if not isinstance(features, list):
        raise ValueError("FeatureCollection missing 'features' array")
    return features


def department_count(cur) -> int:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM public.regions
        WHERE category = 'DEPARTAMENTO'
        """
    )
    return int(cur.fetchone()[0])


def feature_to_row(feature: dict) -> tuple[str, str]:
    props = feature.get("properties") or {}
    geom = feature.get("geometry")
    name = (props.get("nombre") or "").strip()
    if not name:
        raise ValueError("Feature without properties.nombre")
    if not geom:
        raise ValueError(f"Feature '{name}' without geometry")
    return name, json.dumps(geom, ensure_ascii=False)


def iter_batches(rows: list[tuple[str, str]], batch_size: int):
    for idx in range(0, len(rows), batch_size):
        yield rows[idx : idx + batch_size]


def main() -> int:
    args = parse_args()
    if args.batch_size < 1:
        print("ERROR: --batch-size must be >= 1")
        return 1

    load_environment()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    try:
        features = load_geojson(args.file)
    except Exception as exc:
        print(f"ERROR loading GeoJSON: {exc}")
        return 1

    rows: list[tuple[str, str]] = []
    errors = 0
    for feature in features:
        try:
            rows.append(feature_to_row(feature))
        except Exception as exc:
            errors += 1
            print(f"WARN: skipping malformed feature: {exc}")

    print(f"Features read: {len(features)} | valid rows: {len(rows)} | malformed: {errors}")

    inserted = 0
    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                current_count = department_count(cur)
                print(f"Current DEPARTAMENTO count: {current_count}")

                if current_count >= 500:
                    print("ABORT: regions already has >=500 DEPARTAMENTO rows.")
                    return 0
                if current_count != 0:
                    print(
                        "ABORT: expected DEPARTAMENTO count to be 0 for full-load mode. "
                        "Refusing partial/incremental merge."
                    )
                    return 1

                insert_sql = """
                    INSERT INTO public.regions (name, category, geom)
                    VALUES (
                        %s,
                        'DEPARTAMENTO',
                        ST_SetSRID(ST_Multi(ST_GeomFromGeoJSON(%s))::geometry, 4326)
                    )
                """

                for batch in iter_batches(rows, args.batch_size):
                    execute_batch(cur, insert_sql, batch, page_size=len(batch))
                    inserted += len(batch)

            conn.commit()
    except Exception as exc:
        print(f"ERROR during database load: {exc}")
        return 1

    print(f"Inserted rows: {inserted}")
    print("DONE: department load finished")
    return 0


if __name__ == "__main__":
    sys.exit(main())
