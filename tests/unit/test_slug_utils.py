"""Tests para app.utils.slug_utils (SEO-F-01)."""
import pytest
from app.utils.slug_utils import generate_episode_slug, normalize_province_to_slug


def test_normalize_province_to_slug_empty():
    assert normalize_province_to_slug("") == "argentina"
    assert normalize_province_to_slug(None) == "argentina"


def test_normalize_province_to_slug():
    assert normalize_province_to_slug("Córdoba") == "cordoba"
    assert normalize_province_to_slug("Río Negro") == "rio-negro"


def test_slug_8_chars():
    assert generate_episode_slug("Córdoba", 2026, "a3f2b1c9deadbeef", db=None) == "cordoba-2026-a3f2b1c9"


def test_slug_normalization():
    assert generate_episode_slug("Río Negro", 2026, "d9e8f7a600000000", db=None) == "rio-negro-2026-d9e8f7a6"


# test_slug_suffix_on_collision: requiere fixture db_session o DB real; se puede añadir con conftest
