"""Tests para app.utils.jsonld_utils (SEO-F-02)."""
from app.utils.jsonld_utils import build_episode_jsonld


def _ep(ended_at=None):
    return {
        "slug": "cordoba-2026-a3f2b1c9",
        "seo_title": "T",
        "seo_description": "D",
        "bbox_minx": -64.5,
        "bbox_miny": -31.5,
        "bbox_maxx": -63.0,
        "bbox_maxy": -30.0,
        "started_at": "2026-01-15T00:00:00Z",
        "ended_at": ended_at,
        "province_name": "Córdoba",
    }


def test_jsonld_id_canonico():
    r = build_episode_jsonld(_ep(), "https://forestguard.com.ar")
    assert r["@id"] == "https://forestguard.com.ar/episodios/cordoba-2026-a3f2b1c9"
    assert r["url"] == r["@id"]


def test_temporal_coverage_cerrado():
    ep = _ep(ended_at="2026-01-20T00:00:00Z")
    ep["start_date"] = None
    ep["end_date"] = None
    r = build_episode_jsonld(ep, "https://example.com")
    assert "/" in r["temporalCoverage"]


def test_temporal_coverage_activo_sin_barra():
    ep = _ep()
    ep["start_date"] = None
    ep["end_date"] = None
    r = build_episode_jsonld(ep, "https://example.com")
    assert "/" not in r["temporalCoverage"] or r["temporalCoverage"].endswith("Z")
