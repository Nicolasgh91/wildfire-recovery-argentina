from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from uuid import uuid4

from scripts.load_firms_incremental import get_fire_detection_columns, insert_detections


def _sample_detection(supports_detection_hash: bool, supports_h3: bool) -> dict:
    satellite_tag = f"TEST-VIIRS-{uuid4().hex[:8]}"
    detected_at = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "satellite": satellite_tag,
        "instrument": "VIIRS",
        "detected_at": detected_at,
        "latitude": -34.60001,
        "longitude": -58.40001,
        "acquisition_date": date.today(),
        "acquisition_time": "12:34:00",
        "confidence_raw": "95",
        "confidence_normalized": 95,
        "fire_radiative_power": 12.5,
        "bright_ti4": 330.0,
        "bright_ti5": 290.0,
        "daynight": "D",
    }
    legacy_payload = (
        f"{payload['latitude']:.5f}|"
        f"{payload['longitude']:.5f}|"
        f"{payload['acquisition_date'].isoformat()}|"
        f"{payload['acquisition_time']}|"
        f"{payload['satellite']}"
    )
    payload["legacy_hash"] = hashlib.md5(legacy_payload.encode("utf-8")).hexdigest()[:16]
    if supports_detection_hash:
        payload["detection_hash"] = f"sha-{uuid4().hex}"
    if supports_h3:
        payload["h3_index"] = 617733123456789
    return payload


def test_incremental_insert_is_idempotent_for_same_detection(db_session):
    engine = db_session.get_bind().engine
    columns = get_fire_detection_columns(engine)

    supports_detection_hash = "detection_hash" in columns
    supports_h3 = "h3_index" in columns
    supports_created_at = "created_at" in columns

    detection = _sample_detection(supports_detection_hash, supports_h3)

    first = insert_detections(
        engine,
        [detection],
        dry_run=False,
        supports_detection_hash=supports_detection_hash,
        supports_h3=supports_h3,
        supports_created_at=supports_created_at,
    )
    second = insert_detections(
        engine,
        [detection],
        dry_run=False,
        supports_detection_hash=supports_detection_hash,
        supports_h3=supports_h3,
        supports_created_at=supports_created_at,
    )

    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["duplicates"] >= 1
