"""
Cache de escenas GEE basado en la tabla satellite_images.

Antes de llamar a GEE para generar un thumbnail o asset HD, este servicio
verifica si ya existe una imagen con la misma receta reproducible.

Clave de cache: episode_id + gee_system_index + visualization_params
Esto garantiza que la rotacion del evento representativo de un episodio
no invalide innecesariamente el cache (mejora de estabilidad sobre fire_event_id).

Regla: si episode_id + gee_system_index + visualization_params coinciden
y la imagen tiene is_reproducible=true, se reutiliza.
"""

import hashlib
import json
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.evidence import SatelliteImage

logger = logging.getLogger(__name__)


def compute_recipe_hash(
    gee_system_index: str,
    visualization_params: dict,
    episode_id: str,
) -> str:
    """Generate deterministic hash of the GEE recipe for fast lookup."""
    recipe = json.dumps(
        {
            "gee_system_index": gee_system_index,
            "vis_params": visualization_params,
            "episode_id": episode_id,
        },
        sort_keys=True,
    )
    return hashlib.sha256(recipe.encode()).hexdigest()[:16]


def find_cached_scene(
    db: Session,
    gee_system_index: str,
    visualization_params: dict,
    episode_id: str,
    fire_event_id: Optional[str] = None,
) -> Optional[SatelliteImage]:
    """
    Busca una imagen existente con la misma receta GEE.

    Estrategia:
      1. Busca por episode_id (cache estable ante rotacion de evento representativo).
      2. Si episode_id no produce resultado, intenta fallback por fire_event_id
         (compatibilidad con registros pre-T02 sin episode_id).

    Retorna el registro satellite_images si existe y es reproducible.
    Retorna None si no hay match (=> debe generarse via GEE).
    """
    # Busqueda primaria: por episode_id
    if episode_id:
        result = (
            db.query(SatelliteImage)
            .filter(
                SatelliteImage.episode_id == episode_id,
                SatelliteImage.gee_system_index == gee_system_index,
                SatelliteImage.is_reproducible.is_(True),
            )
            .first()
        )

        if result is not None:
            stored_params = result.visualization_params or {}
            if stored_params == visualization_params:
                logger.info(
                    "Cache HIT (by episode_id): reusing satellite_image %s for episode %s",
                    result.id,
                    episode_id,
                )
                return result

            logger.debug(
                "Cache MISS (params differ, episode_id=%s, gee_system_index=%s)",
                episode_id,
                gee_system_index,
            )

    # Fallback: por fire_event_id (registros legacy sin episode_id)
    if fire_event_id:
        result = (
            db.query(SatelliteImage)
            .filter(
                SatelliteImage.fire_event_id == fire_event_id,
                SatelliteImage.episode_id.is_(None),
                SatelliteImage.gee_system_index == gee_system_index,
                SatelliteImage.is_reproducible.is_(True),
            )
            .first()
        )

        if result is not None:
            stored_params = result.visualization_params or {}
            if stored_params == visualization_params:
                logger.info(
                    "Cache HIT (by fire_event_id legacy): reusing satellite_image %s",
                    result.id,
                )
                return result

    return None


def find_all_cached_scenes(
    db: Session,
    gee_system_index: str,
    episode_id: str,
) -> List[SatelliteImage]:
    """
    Retorna todas las imagenes cacheadas para un episodio + escena.
    Util para verificar si los 3 vis_types ya estan generados.
    """
    return (
        db.query(SatelliteImage)
        .filter(
            SatelliteImage.episode_id == episode_id,
            SatelliteImage.gee_system_index == gee_system_index,
            SatelliteImage.is_reproducible.is_(True),
        )
        .all()
    )


def should_regenerate_thumbnail(
    episode_id: str,
    current_gee_image_id: Optional[str],
    last_gee_image_id: Optional[str],
) -> bool:
    """
    Determina si un episodio necesita regenerar thumbnails.

    Retorna False (omitir regeneracion) si last_gee_image_id no cambio.
    Esta es la optimizacion clave documentada en UC-F08R.
    """
    if current_gee_image_id and current_gee_image_id == last_gee_image_id:
        logger.debug(
            "Episode %s: gee_image_id unchanged, skipping regeneration",
            episode_id,
        )
        return False
    return True
