"""
SEO-F-02: JSON-LD tipo Dataset para episodios de incendio.
Acepta start_date/end_date (datetime o ISO string); base_url inyectado por el caller.
"""
from datetime import datetime


def _to_iso(dt: datetime | str | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _build_temporal_coverage(start_iso: str, end_iso: str | None) -> str:
    """Cerrado: 'start/end'. Activo: solo 'start' (barra final sola no es ISO 8601 válido)."""
    if end_iso:
        return f"{start_iso}/{end_iso}"
    return start_iso


def build_episode_jsonld(episode: dict, base_url: str) -> dict:
    """Construye JSON-LD Dataset para un episodio. base_url sin trailing slash (ej. settings.SITE_BASE_URL)."""
    slug = episode.get("slug") or ""
    canonical = f"{base_url.rstrip('/')}/episodios/{slug}"

    start_date = episode.get("start_date") or episode.get("started_at")
    end_date = episode.get("end_date") or episode.get("ended_at")
    start_iso = _to_iso(start_date) or ""
    end_iso = _to_iso(end_date)

    province_name = episode.get("province_name") or "Argentina"

    geo = {}
    if all(
        episode.get(k) is not None
        for k in ("bbox_minx", "bbox_miny", "bbox_maxx", "bbox_maxy")
    ):
        geo = {
            "@type": "GeoShape",
            "box": (
                f"{episode['bbox_miny']} {episode['bbox_minx']} "
                f"{episode['bbox_maxy']} {episode['bbox_maxx']}"
            ),
        }

    spatial = {"@type": "Place", "geo": geo} if geo else {"@type": "Place"}

    return {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": canonical,
        "url": canonical,
        "name": episode.get("seo_title") or "",
        "description": episode.get("seo_description") or "",
        "spatialCoverage": spatial,
        "temporalCoverage": _build_temporal_coverage(start_iso, end_iso),
        "creator": {"@type": "Organization", "name": "ForestGuard", "url": base_url.rstrip("/")},
        "keywords": ["incendio forestal", "Argentina", province_name, "Sentinel-2", "VIIRS"],
        "license": "https://creativecommons.org/licenses/by/4.0/",
    }
