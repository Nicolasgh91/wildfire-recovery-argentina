"""
SEO-F-03: Clasificación de episodios para sitemap (standard / minor / excluded).
Cuota de episodios "minor" por year_month; umbral por región.
"""
from typing import Any


def get_regional_threshold(province_slug: str, thresholds: list[dict[str, Any]]) -> int:
    """Devuelve el mínimo min_affected_area_ha aplicable a la provincia (vía province_slugs)."""
    applicable = [
        t["min_affected_area_ha"]
        for t in thresholds
        if province_slug and province_slug in (t.get("province_slugs") or [])
    ]
    return min(applicable) if applicable else 500


def classify_episode_for_sitemap(
    episode: dict[str, Any],
    thresholds: list[dict[str, Any]],
    minor_quota_used: int,
    minor_quota_max: int = 100,
) -> str:
    """
    Clasifica un episodio para el sitemap.
    Returns: "standard" | "minor" | "excluded".
    El caller debe pasar un dict con: status, has_satellite_images, duration_days,
    affected_area_ha, province_slug (derivados del modelo).
    """
    if episode.get("status") not in ("active", "monitoring", "closed"):
        return "excluded"
    if not episode.get("has_satellite_images"):
        return "excluded"
    if (episode.get("duration_days") or 0) < 3:
        return "excluded"
    ha = episode.get("affected_area_ha") or 0
    threshold = get_regional_threshold(episode.get("province_slug") or "", thresholds)
    if ha >= threshold:
        return "standard"
    if ha < 100 and minor_quota_used < minor_quota_max:
        return "minor"
    return "excluded"
