"""
Ingestion tasks for NASA FIRMS data.
"""

import csv
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from celery import chain, shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="workers.tasks.ingestion.download_firms_daily",
    queue="ingestion",
    max_retries=3,
)
def download_firms_daily(self, days: int = 2, dry_run: bool = False):
    """
    Execute real incremental FIRMS ingestion pipeline.

    Returns:
        dict with ingestion metrics and basic traceability fields.
    """
    try:
        logger.info("Starting FIRMS ingestion (days=%s, dry_run=%s)", days, dry_run)

        # Lazy import keeps worker module import-time lightweight.
        from scripts.maintenance.load_firms_incremental import run_incremental_pipeline

        pipeline_result = run_incremental_pipeline(days=days, dry_run=dry_run)
        if not isinstance(pipeline_result, dict):
            raise RuntimeError(
                "run_incremental_pipeline must return a dict with ingestion metrics"
            )

        result = {
            "success": bool(pipeline_result.get("success", True)),
            "records_inserted": int(pipeline_result.get("records_inserted", 0)),
            "duplicates_found": int(pipeline_result.get("duplicates_found", 0)),
            "total_filtered": int(pipeline_result.get("total_filtered", 0)),
            "events_created": int(pipeline_result.get("events_created", 0)),
            "areas_calculated": int(pipeline_result.get("areas_calculated", 0)),
            "intersections": int(pipeline_result.get("intersections", 0)),
            "dry_run": bool(dry_run),
            "source": "scripts.maintenance.load_firms_incremental.run_incremental_pipeline",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"FIRMS ingestion finished: {result}")
        return result

    except Exception as exc:
        logger.error("FIRMS ingestion failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    name="workers.tasks.ingestion.process_firms_batch",
    bind=True,
)
def process_firms_batch(self, csv_data, batch_id):
    """
    Process a FIRMS batch payload.

    This task remains a lightweight placeholder for future per-batch logic.
    """
    try:
        logger.info("Processing FIRMS batch %s", batch_id)

        processed = {
            "batch_id": batch_id,
            "total_records": 0,
            "valid_records": 0,
            "filtered_out": 0,
        }

        return processed

    except Exception as exc:
        logger.error("Failed processing FIRMS batch %s: %s", batch_id, exc)
        raise self.retry(exc=exc, countdown=30)


@shared_task(
    bind=True,
    name="workers.tasks.ingestion.ingest_firms_csv",
    queue="ingestion",
    max_retries=1,
)
def ingest_firms_csv(self, csv_path: str, source_label: str = "manual_upload"):
    """
    Ingesta detecciones desde un CSV local de NASA FIRMS.

    Args:
        csv_path: Ruta absoluta al CSV en filesystem del contenedor.
        source_label: Etiqueta para trazabilidad de logs.

    Returns:
        dict con métricas de ingestión.
    """
    try:
        csv_file = Path(csv_path)
        if not csv_file.exists() or not csv_file.is_file():
            raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

        from scripts.maintenance.load_firms_incremental import (
            H3_AVAILABLE,
            build_detected_at,
            build_detection_hash,
            compute_h3_index,
            get_engine,
            get_fire_detection_columns,
            insert_detections,
            normalize_confidence,
            resolve_h3_resolution,
        )

        engine = get_engine()
        columns = get_fire_detection_columns(engine)
        supports_h3 = "h3_index" in columns
        supports_detection_hash = "detection_hash" in columns
        supports_created_at = "created_at" in columns
        h3_resolution = resolve_h3_resolution(engine)

        if supports_h3 and not H3_AVAILABLE:
            raise RuntimeError("h3_index existe pero la librería h3 no está instalada")

        total_rows = 0
        transformed: list[dict] = []
        transform_errors = 0

        with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for raw_row in reader:
                total_rows += 1
                try:
                    lat = float(raw_row.get("latitude", 0) or 0)
                    lon = float(raw_row.get("longitude", 0) or 0)

                    acq_date_raw = str(raw_row.get("acq_date", "") or "").strip()
                    acq_time_raw = raw_row.get("acq_time", "0000")
                    if not acq_date_raw:
                        transform_errors += 1
                        continue

                    acq_date, acq_time, detected_at = build_detected_at(
                        acq_date_raw,
                        acq_time_raw,
                    )

                    satellite = str(raw_row.get("satellite", "") or "").strip().upper()
                    instrument = str(raw_row.get("instrument", "") or "").strip().upper()
                    if not instrument:
                        instrument = "VIIRS" if "VIIRS" in satellite else "UNKNOWN"

                    confidence_raw = str(raw_row.get("confidence", "") or "")
                    confidence = normalize_confidence(confidence_raw, satellite)
                    frp = float(raw_row.get("frp", 0) or 0)

                    detection_hash = build_detection_hash(
                        satellite=satellite,
                        instrument=instrument,
                        detected_at=detected_at,
                        lat=lat,
                        lon=lon,
                        frp=frp,
                        confidence=confidence,
                    )

                    legacy_str = (
                        f"{lat:.5f}|{lon:.5f}|{acq_date.isoformat()}|{acq_time}|{satellite}"
                    )
                    legacy_hash = hashlib.md5(legacy_str.encode()).hexdigest()[:16]

                    payload = {
                        "satellite": satellite,
                        "instrument": instrument,
                        "detected_at": detected_at,
                        "latitude": lat,
                        "longitude": lon,
                        "acquisition_date": acq_date,
                        "acquisition_time": acq_time,
                        "confidence_raw": confidence_raw,
                        "confidence_normalized": confidence,
                        "fire_radiative_power": frp,
                        "bright_ti4": float(
                            raw_row.get("bright_ti4", raw_row.get("brightness", 0)) or 0
                        ),
                        "bright_ti5": float(
                            raw_row.get("bright_ti5", raw_row.get("bright_t31", 0)) or 0
                        ),
                        "daynight": str(raw_row.get("daynight", "D") or "D"),
                        "detection_hash": detection_hash,
                        "legacy_hash": legacy_hash,
                    }

                    if supports_h3:
                        payload["h3_index"] = compute_h3_index(lat, lon, h3_resolution)

                    transformed.append(payload)
                except (TypeError, ValueError):
                    transform_errors += 1
                    continue

        insert_result = insert_detections(
            engine,
            transformed,
            dry_run=False,
            supports_detection_hash=supports_detection_hash,
            supports_h3=supports_h3,
            supports_created_at=supports_created_at,
        )

        result = {
            "success": True,
            "source_label": source_label,
            "csv_path": str(csv_file),
            "total_rows": total_rows,
            "valid_rows": len(transformed),
            "new_detections": int(insert_result.get("inserted", 0)),
            "duplicates": int(insert_result.get("duplicates", 0)),
            "errors": int(transform_errors + insert_result.get("skipped_errors", 0)),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info("Manual CSV ingestion finished: %s", result)
        return result
    except Exception as exc:
        logger.error("Manual CSV ingestion failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@shared_task(
    bind=True,
    name="workers.tasks.ingestion.run_full_ingestion_pipeline",
    queue="ingestion",
)
def run_full_ingestion_pipeline(self, csv_path: str, source_label: str = "manual_upload"):
    """
    Ejecuta la cadena completa: ingesta CSV -> clustering -> episodios.
    """
    from workers.tasks.clustering import cluster_detections
    from workers.tasks.clustering_task import cluster_fire_episodes_pipeline

    workflow = chain(
        ingest_firms_csv.si(csv_path, source_label),
        cluster_detections.si(days_back=30),
        cluster_fire_episodes_pipeline.si(),
    )
    async_result = workflow.apply_async()
    result = {
        "success": True,
        "pipeline_id": async_result.id,
        "source_label": source_label,
        "csv_path": csv_path,
    }
    logger.info("Manual full ingestion pipeline enqueued: %s", result)
    return result
