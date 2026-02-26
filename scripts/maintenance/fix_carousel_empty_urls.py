"""
Repara episodios con slides_data donde thumbnail_url está vacío.

Dos modos:

  patch -- Intenta rellenar thumbnail_url desde la tabla satellite_images
           (solo sirve si el objeto sí se subió y la URL está en la fila).
  clear -- Limpia slides_data y borra filas carousel en satellite_images
           para que el próximo run del carousel regenere las imágenes.

Uso:
  # Ver episodios afectados
  python scripts/maintenance/fix_carousel_empty_urls.py --dry-run

  # Parchear URLs desde satellite_images (si existen)
  python scripts/maintenance/fix_carousel_empty_urls.py --mode patch [--dry-run]

  # Limpiar y dejar que el carousel regenere
  python scripts/maintenance/fix_carousel_empty_urls.py --mode clear [--dry-run]
"""

import argparse
import logging
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.episode import FireEpisode
from app.models.evidence import SatelliteImage

CAROUSEL_IMAGE_TYPE = "carousel"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _is_valid_url(url: str | None) -> bool:
    if not url or not url.strip():
        return False
    u = url.strip()
    return u.startswith("http://") or u.startswith("https://")


def _slide_has_no_url(slide: dict) -> bool:
    thumb = (slide.get("thumbnail_url") or "").strip()
    url = (slide.get("url") or "").strip()
    return not _is_valid_url(thumb) and not _is_valid_url(url)


def find_episodes_with_empty_slides(db):
    """Episodios con slides_data que tienen al menos un slide con thumbnail_url vacío."""
    rows = db.execute(
        text("""
            SELECT id, slides_data
            FROM fire_episodes
            WHERE slides_data IS NOT NULL
              AND jsonb_array_length(slides_data) > 0
        """)
    ).fetchall()
    out = []
    for row in rows:
        slides = row.slides_data or []
        if any(_slide_has_no_url(s) for s in slides):
            out.append({"id": str(row.id), "slides_data": slides})
    return out


def patch_episode_from_satellite_images(db, episode_id: str, slides_data: list) -> list | None:
    """
    Construye un nuevo slides_data con thumbnail_url rellenado desde satellite_images.
    Retorna la nueva lista si al menos un slide pudo rellenarse; None si no hay cambios.
    """
    updated = []
    changed = False
    for slide in slides_data:
        sid = slide.get("satellite_image_id")
        new_slide = dict(slide)
        if _slide_has_no_url(slide) and sid:
            try:
                uid = UUID(sid) if isinstance(sid, str) else sid
            except (TypeError, ValueError):
                updated.append(new_slide)
                continue
            img = db.query(SatelliteImage).filter(SatelliteImage.id == uid).first()
            if img:
                url = (img.thumbnail_url or img.r2_url or "").strip()
                if _is_valid_url(url):
                    new_slide["thumbnail_url"] = url
                    changed = True
        updated.append(new_slide)
    return updated if changed else None


def clear_episode_for_regeneration(db, episode_id: str):
    """Limpia slides_data y borra filas carousel de satellite_images para este episodio."""
    ep = db.query(FireEpisode).filter(FireEpisode.id == episode_id).first()
    if not ep:
        return
    ep.slides_data = []
    deleted = (
        db.query(SatelliteImage)
        .filter(
            SatelliteImage.episode_id == episode_id,
            SatelliteImage.image_type == CAROUSEL_IMAGE_TYPE,
        )
        .delete(synchronize_session=False)
    )
    logger.info("Episodio %s: slides_data vaciado, %d filas satellite_images carousel borradas", episode_id, deleted)


def main():
    parser = argparse.ArgumentParser(description="Repara slides_data con thumbnail_url vacío")
    parser.add_argument("--dry-run", action="store_true", help="Solo listar / simular, no escribir")
    parser.add_argument(
        "--mode",
        choices=("patch", "clear"),
        default="patch",
        help="patch = rellenar desde satellite_images; clear = limpiar y permitir regenerar",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        episodes = find_episodes_with_empty_slides(db)
        if not episodes:
            logger.info("No hay episodios con slides_data con thumbnail_url vacío.")
            return

        logger.info("Episodios con al menos un slide sin URL: %d", len(episodes))
        for e in episodes:
            logger.info("  %s", e["id"])

        if args.mode == "patch":
            patched = 0
            for e in episodes:
                new_slides = patch_episode_from_satellite_images(db, e["id"], e["slides_data"])
                if new_slides is not None:
                    patched += 1
                    if not args.dry_run:
                        ep = db.query(FireEpisode).filter(FireEpisode.id == e["id"]).first()
                        if ep:
                            ep.slides_data = new_slides
                    else:
                        logger.info("[dry-run] Parchearía episodio %s con %d slides", e["id"], len(new_slides))
            if not args.dry_run and patched:
                db.commit()
            logger.info("Parcheados (o a parchear): %d", patched)
            return

        if args.mode == "clear":
            for e in episodes:
                if args.dry_run:
                    logger.info("[dry-run] Limpiaría episodio %s para regenerar", e["id"])
                else:
                    clear_episode_for_regeneration(db, e["id"])
            if not args.dry_run:
                db.commit()
            logger.info("Listo. Ejecutá el carousel (generate_carousel) para regenerar las imágenes.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
