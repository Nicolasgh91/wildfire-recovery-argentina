"""Tests para app.utils.ssg_routes (SEO-F-04)."""
from app.utils.ssg_routes import (
    PROVINCES,
    ZONE_SLUGS,
    build_ssg_routes_payload,
)


def test_provinces_count():
    assert len(PROVINCES) >= 20
    assert "cordoba" in PROVINCES
    assert "ciudad-autonoma-de-buenos-aires" in PROVINCES


def test_zone_slugs():
    assert "delta-del-parana" in ZONE_SLUGS
    assert len(ZONE_SLUGS) >= 5


def test_paginacion_cordoba_45():
    p = build_ssg_routes_payload(
        [], "2026-03-09T00:00:00Z", episodes_per_province={"cordoba": 45}
    )
    assert "/provincias/cordoba/pagina/3" in p["province_routes"]
    assert "/provincias/cordoba/pagina/4" not in p["province_routes"]


def test_caba_incluida():
    p = build_ssg_routes_payload([], "2026-03-09T00:00:00Z")
    assert "/provincias/ciudad-autonoma-de-buenos-aires" in p["province_routes"]
