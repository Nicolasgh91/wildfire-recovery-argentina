"""
SEO-F-04: Rutas estáticas para SSG y sitemap.
STRATEGIC_ZONES como dict (zone_slug -> [province_slugs]) para sitemap y stats/counts.
"""
from typing import Any

PROVINCES = [
    "buenos-aires",
    "catamarca",
    "chaco",
    "chubut",
    "cordoba",
    "corrientes",
    "ciudad-autonoma-de-buenos-aires",
    "entre-rios",
    "formosa",
    "jujuy",
    "la-pampa",
    "la-rioja",
    "mendoza",
    "misiones",
    "neuquen",
    "rio-negro",
    "salta",
    "san-juan",
    "san-luis",
    "santa-cruz",
    "santa-fe",
    "santiago-del-estero",
    "tierra-del-fuego",
    "tucuman",
]

# Dict para sitemap (iterar claves) y para stats/counts by_zone (agrupar por provincia)
STRATEGIC_ZONES: dict[str, list[str]] = {
    "vaca-muerta": ["neuquen", "rio-negro"],
    "patagonia-norte": ["neuquen", "rio-negro", "chubut"],
    "delta-del-parana": ["entre-rios", "buenos-aires"],
    "gran-chaco": ["chaco", "formosa", "santiago-del-estero"],
    "corredor-verde-misionero": ["misiones"],
    "sierras-cordoba": ["cordoba"],
    "yungas-noa": ["salta", "jujuy", "tucuman"],
    "pampas-centrales": ["cordoba", "santa-fe", "la-pampa", "buenos-aires"],
}

ZONE_SLUGS = list(STRATEGIC_ZONES.keys())

PAGE_SIZE = 20  # debe coincidir con el límite de paginación del frontend


def _paginated_routes(base_path: str, item_count: int) -> list[str]:
    routes = [base_path]
    total_pages = max(1, -(-item_count // PAGE_SIZE))  # división techo
    for page in range(2, total_pages + 1):
        routes.append(f"{base_path}/pagina/{page}")
    return routes


def build_ssg_routes_payload(
    episode_slugs: list[str],
    generated_at: str,
    episodes_per_province: dict[str, int] | None = None,
    episodes_per_zone: dict[str, int] | None = None,
) -> dict[str, Any]:
    epp = episodes_per_province or {}
    epz = episodes_per_zone or {}

    province_routes: list[str] = []
    for p in PROVINCES:
        province_routes.extend(_paginated_routes(f"/provincias/{p}", epp.get(p, 0)))

    zone_routes: list[str] = []
    for z in ZONE_SLUGS:
        zone_routes.extend(_paginated_routes(f"/zonas/{z}", epz.get(z, 0)))

    episode_routes = [f"/episodios/{s}" for s in episode_slugs]
    return {
        "generated_at": generated_at,
        "static_routes": ["/metodologia", "/acerca"],
        "province_routes": province_routes,
        "zone_routes": zone_routes,
        "episode_routes": episode_routes,
        "total": 2 + len(province_routes) + len(zone_routes) + len(episode_routes),
    }
