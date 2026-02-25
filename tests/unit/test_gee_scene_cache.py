"""
Tests unitarios para gee_scene_cache.py con el nuevo modelo de cache por episode_id.
"""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from app.services.gee_scene_cache import (
    compute_recipe_hash,
    find_all_cached_scenes,
    find_cached_scene,
    should_regenerate_thumbnail,
)


VIS_RGB = {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.2, "spatial_resolution": 10}
VIS_SWIR = {"bands": ["B12", "B11", "B4"], "min": [0, 0, 0], "max": [5000, 5000, 5000], "gamma": [1.0, 1.0, 1.0], "spatial_resolution": 20}


class TestComputeRecipeHash:
    def test_deterministic(self):
        h1 = compute_recipe_hash("S2A_XYZ", VIS_RGB, "ep-001")
        h2 = compute_recipe_hash("S2A_XYZ", VIS_RGB, "ep-001")
        assert h1 == h2

    def test_different_episode_different_hash(self):
        h1 = compute_recipe_hash("S2A_XYZ", VIS_RGB, "ep-001")
        h2 = compute_recipe_hash("S2A_XYZ", VIS_RGB, "ep-002")
        assert h1 != h2

    def test_different_vis_different_hash(self):
        h1 = compute_recipe_hash("S2A_XYZ", VIS_RGB, "ep-001")
        h2 = compute_recipe_hash("S2A_XYZ", VIS_SWIR, "ep-001")
        assert h1 != h2


def make_sat_image(episode_id=None, fire_event_id=None, gee_system_index="S2A_XYZ",
                   vis_params=None, thumbnail_url="https://example.com/thumb.png",
                   is_reproducible=True):
    img = MagicMock()
    img.id = uuid4()
    img.episode_id = episode_id
    img.fire_event_id = fire_event_id
    img.gee_system_index = gee_system_index
    img.visualization_params = vis_params or VIS_RGB
    img.thumbnail_url = thumbnail_url
    img.is_reproducible = is_reproducible
    img.created_at = None
    return img


class TestFindCachedScene:
    def _make_db(self, result=None):
        db = MagicMock()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = result
        db.query.return_value = query_chain
        return db

    def test_cache_hit_by_episode_id(self):
        """Cache hit cuando episode_id + scene + vis_params coinciden."""
        ep_id = str(uuid4())
        img = make_sat_image(episode_id=ep_id, gee_system_index="S2A_TEST", vis_params=VIS_RGB)
        db = self._make_db(result=img)

        result = find_cached_scene(db, "S2A_TEST", VIS_RGB, episode_id=ep_id)
        assert result is img

    def test_cache_miss_wrong_vis_params(self):
        """Cache miss si los vis_params difieren."""
        ep_id = str(uuid4())
        img = make_sat_image(episode_id=ep_id, gee_system_index="S2A_TEST", vis_params=VIS_SWIR)
        db = self._make_db(result=img)

        result = find_cached_scene(db, "S2A_TEST", VIS_RGB, episode_id=ep_id)
        assert result is None

    def test_cache_miss_no_episode_id(self):
        """Sin episode_id y sin fire_event_id => None."""
        db = self._make_db(result=None)
        result = find_cached_scene(db, "S2A_TEST", VIS_RGB, episode_id="")
        assert result is None

    def test_fallback_to_fire_event_id(self):
        """Fallback a fire_event_id para registros legacy sin episode_id.

        Cuando episode_id esta vacio, se omite la busqueda primaria y se usa
        fire_event_id directamente. Por eso solo hay UNA llamada a .first().
        """
        ev_id = str(uuid4())
        img = make_sat_image(
            episode_id=None, fire_event_id=ev_id,
            gee_system_index="S2A_TEST", vis_params=VIS_RGB,
        )
        db = self._make_db(result=img)

        result = find_cached_scene(
            db, "S2A_TEST", VIS_RGB,
            episode_id="",
            fire_event_id=ev_id,
        )
        assert result is img


class TestShouldRegenerateThumbnail:
    def test_skip_when_same_image_id(self):
        assert should_regenerate_thumbnail("ep-1", "S2A_20260101", "S2A_20260101") is False

    def test_regenerate_when_image_changed(self):
        assert should_regenerate_thumbnail("ep-1", "S2A_20260202", "S2A_20260101") is True

    def test_regenerate_when_no_current_image(self):
        assert should_regenerate_thumbnail("ep-1", None, "S2A_20260101") is True

    def test_regenerate_when_no_previous_image(self):
        assert should_regenerate_thumbnail("ep-1", "S2A_20260101", None) is True
