"""Tests para app.utils.seo_filters (SEO-F-03)."""
from app.utils.seo_filters import classify_episode_for_sitemap, get_regional_threshold


def test_get_regional_threshold_empty():
    assert get_regional_threshold("", []) == 500


def test_get_regional_threshold():
    thresholds = [
        {"province_slugs": ["cordoba", "santa-fe"], "min_affected_area_ha": 250},
        {"province_slugs": ["cordoba"], "min_affected_area_ha": 300},
    ]
    assert get_regional_threshold("cordoba", thresholds) == 250


def test_classify_standard():
    ep = {
        "status": "closed",
        "has_satellite_images": True,
        "duration_days": 5,
        "affected_area_ha": 400,
        "province_slug": "cordoba",
    }
    th = [{"province_slugs": ["cordoba"], "min_affected_area_ha": 250}]
    assert classify_episode_for_sitemap(ep, th, 0, 100) == "standard"


def test_classify_excluded_status():
    ep = {
        "status": "draft",
        "has_satellite_images": True,
        "duration_days": 5,
        "affected_area_ha": 400,
        "province_slug": "cordoba",
    }
    assert classify_episode_for_sitemap(ep, [], 0, 100) == "excluded"


def test_classify_minor():
    ep = {
        "status": "closed",
        "has_satellite_images": True,
        "duration_days": 5,
        "affected_area_ha": 80,
        "province_slug": "cordoba",
    }
    th = [{"province_slugs": ["cordoba"], "min_affected_area_ha": 250}]
    assert classify_episode_for_sitemap(ep, th, 0, 100) == "minor"
