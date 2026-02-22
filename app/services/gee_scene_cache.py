"""
Cache de escenas GEE basado en la tabla satellite_images.

Antes de llamar a GEE para generar un thumbnail o asset HD, este servicio
verifica si ya existe una imagen con la misma receta reproducible.

Regla: si gee_system_index + visualization_params + fire_event_id coinciden
y la imagen tiene is_reproducible=true, se reutiliza.
"""

import hashlib
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.evidence import SatelliteImage

logger = logging.getLogger(__name__)


def compute_recipe_hash(
    gee_system_index: str,
    visualization_params: dict,
    fire_event_id: str,
) -> str:
    """Generate deterministic hash of the GEE recipe for fast lookup."""
    recipe = json.dumps(
        {
            "gee_system_index": gee_system_index,
            "vis_params": visualization_params,
            "fire_event_id": fire_event_id,
        },
        sort_keys=True,
    )
    return hashlib.sha256(recipe.encode()).hexdigest()[:16]


def find_cached_scene(
    db: Session,
    gee_system_index: str,
    visualization_params: dict,
    fire_event_id: str,
) -> Optional[SatelliteImage]:
    """
    Look for an existing image with the same GEE recipe.

    Returns the satellite_images record if it exists and is reproducible.
    Returns None if no match (=> must generate via GEE).
    """
    result = (
        db.query(SatelliteImage)
        .filter(
            SatelliteImage.fire_event_id == fire_event_id,
            SatelliteImage.gee_system_index == gee_system_index,
            SatelliteImage.is_reproducible.is_(True),
        )
        .first()
    )

    if result is None:
        return None

    # Compare visualization_params (exact recipe match)
    stored_params = result.visualization_params or {}
    if stored_params == visualization_params:
        logger.info(
            "Cache HIT: reusing satellite_image %s for fire_event %s",
            result.id,
            fire_event_id,
        )
        return result

    logger.debug(
        "Cache MISS (params differ): fire_event %s, gee_system_index=%s",
        fire_event_id,
        gee_system_index,
    )
    return None


def should_regenerate_thumbnail(
    episode_id: str,
    current_gee_image_id: Optional[str],
    last_gee_image_id: Optional[str],
) -> bool:
    """
    Determine if an episode needs to regenerate thumbnails.

    Returns False (skip regeneration) if last_gee_image_id has not changed.
    This is the key optimization documented in UC-F08R.
    """
    if current_gee_image_id and current_gee_image_id == last_gee_image_id:
        logger.debug(
            "Episode %s: gee_image_id unchanged, skipping regeneration",
            episode_id,
        )
        return False
    return True
