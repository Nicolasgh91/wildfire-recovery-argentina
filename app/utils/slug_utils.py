"""
SEO-F-01: Generación de slugs para episodios de incendio.
Colisión segura con sufijo incremental; uso de text() y parámetros nombrados.
"""
import re
import unicodedata

from sqlalchemy import text
from sqlalchemy.orm import Session


def normalize_province_to_slug(province: str) -> str:
    """Normaliza nombre de provincia a slug (minúsculas, sin acentos, guiones)."""
    if not province:
        return "argentina"
    normalized = unicodedata.normalize("NFD", province)
    ascii_str = normalized.encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower()).strip("-")
    return slug or "argentina"


def generate_episode_slug(
    province: str,
    year: int,
    episode_id: str,
    db: Session | None = None,
) -> str:
    """Genera slug tipo provincia-year-8chars_uuid. Sufijo incremental si colisiona en DB."""
    normalized = unicodedata.normalize("NFD", province or "argentina")
    ascii_str = normalized.encode("ascii", "ignore").decode()
    slug_base = re.sub(r"[^a-z0-9]+", "-", ascii_str.lower()).strip("-") or "argentina"
    candidate = f"{slug_base}-{year}-{episode_id[:8]}"

    if db is None:
        return candidate

    result = db.execute(
        text("SELECT slug FROM fire_episodes WHERE slug LIKE :prefix"),
        {"prefix": f"{candidate}%"},
    )
    existing = {row[0] for row in result.fetchall()}

    if candidate not in existing:
        return candidate
    suffix = 2
    while f"{candidate}-{suffix}" in existing:
        suffix += 1
    return f"{candidate}-{suffix}"
