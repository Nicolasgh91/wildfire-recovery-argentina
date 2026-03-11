import json
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import text

from workers.tasks.seo import CHUNK_SIZE, export_ssg_artifacts


def _seed_episode(db_session, slug="cordoba-2026-a3f2b1c9", province="Córdoba"):
    db_session.execute(
        text(
            """
            INSERT INTO fire_episodes (
                slug, status, estimated_area_hectares,
                provinces, start_date, end_date,
                slides_status, slides_data,
                bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
                seo_title, seo_description, updated_at, last_seen_at
            )
            VALUES (
                :slug, 'active', 300,
                ARRAY[:province], NOW() - INTERVAL '10 days', NOW() - INTERVAL '5 days',
                'ready',
                '[{"thumbnail_url": "https://cdn.test/t.webp"}]'::jsonb,
                -65.0, -35.0, -60.0, -30.0,
                'Título SEO', 'Descripción SEO', NOW(), NOW()
            )
            """
        ),
        {"slug": slug, "province": province},
    )
    db_session.commit()


def test_chunking_usa_fetchmany_no_fetchall(monkeypatch, db_session, mocker):
    """El query principal nunca debe cargar todos los registros de una vez."""
    fetchmany_calls: list[int] = []

    original_fetchmany = type(
        db_session.execute(text("SELECT 1")).fetchmany()
    ).__mro__[0]

    def spy(self, size):
        fetchmany_calls.append(size)
        return original_fetchmany(self, size)

    monkeypatch.setattr(
        "sqlalchemy.engine.CursorResult.fetchmany",
        spy,
    )

    _seed_episode(db_session)
    mocker.patch(
        "app.services.storage_service.get_storage_service"
    )().upload_bytes.return_value = None

    export_ssg_artifacts()

    assert fetchmany_calls, "fetchmany debería haberse llamado al menos una vez"
    assert all(c == CHUNK_SIZE for c in fetchmany_calls)


def test_memoria_plana_3000_episodios(db_session, mocker):
    """Procesar miles de episodios no debe disparar uso de RAM > 50 MB."""
    for i in range(3000):
        db_session.execute(
            text(
                """
                INSERT INTO fire_episodes (
                    slug, status, estimated_area_hectares,
                    provinces, start_date,
                    slides_status, slides_data
                )
                VALUES (
                    :slug, 'active', 300,
                    ARRAY['Córdoba'], NOW(),
                    'ready',
                    '[{"thumbnail_url": "https://cdn.test/t.webp"}]'::jsonb
                )
                """
            ),
            {"slug": f"cordoba-2026-{i:08x}"},
        )
    db_session.commit()

    mocker.patch(
        "app.services.storage_service.get_storage_service"
    )().upload_bytes.return_value = None

    import tracemalloc

    tracemalloc.start()
    export_ssg_artifacts()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert peak < 50 * 1024 * 1024, f"Pico de RAM: {peak / 1024 / 1024:.1f} MB"


def test_columnas_inexistentes_no_se_consultan(db_session, mocker):
    """Verificar que el SQL no referencia columnas derivadas como si fueran columnas reales."""
    mocker.patch(
        "app.services.storage_service.get_storage_service"
    )().upload_bytes.return_value = None

    with patch("sqlalchemy.orm.Session.execute") as mock_exec:
        mock_exec.return_value.fetchmany.return_value = []
        export_ssg_artifacts()
        sql_calls = [
            str(c.args[0])
            for c in mock_exec.call_args_list
            if "fire_episodes" in str(c.args[0])
        ]
        for sql in sql_calls:
            assert "province_slug" not in sql
            assert "thumbnail_url" not in sql
            assert "affected_area_ha" not in sql
            assert "slides_status" in sql


def test_filtro_slides_status_excluye_no_ready(db_session, mock_oci, mocker):
    """Episodios con slides_status != 'ready' no deben aparecer en los artefactos."""
    for status in ("pending", "processing", "failed"):
        db_session.execute(
            text(
                """
                INSERT INTO fire_episodes (
                    slug, status, estimated_area_hectares,
                    provinces, start_date, slides_status,
                    seo_title, seo_description
                )
                VALUES (
                    :slug, 'active', 300,
                    ARRAY['Córdoba'], NOW(), :ss,
                    'Título', 'Descripción'
                )
                """
            ),
            {"slug": f"test-{status}-00000000", "ss": status},
        )
    db_session.commit()

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    export_ssg_artifacts()
    data = json.loads(mock_oci.get_uploaded("seo/ssg-seo-data.json"))
    for status in ("pending", "processing", "failed"):
        assert f"test-{status}-00000000" not in data["episodes"]


def test_provinces_vacio_no_genera_index_error(db_session, mock_oci, mocker):
    db_session.execute(
        text(
            """
            INSERT INTO fire_episodes (
                slug, status, estimated_area_hectares,
                provinces, start_date, slides_status,
                seo_title, seo_description
            )
            VALUES (
                'test-vacio-2026-00000000', 'active', 300,
                ARRAY[]::text[], NOW(), 'ready',
                'Título', 'Descripción'
            )
            """
        )
    )
    db_session.commit()

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()
    storage_mock.upload_bytes.return_value = None

    result = export_ssg_artifacts()
    assert result["seo_data_count"] >= 0


def test_thumbnail_nulo_no_aparece_en_og_image(db_session, mock_oci, mocker):
    db_session.execute(
        text(
            """
            INSERT INTO fire_episodes (
                slug, status, estimated_area_hectares,
                provinces, start_date, slides_data, slides_status,
                seo_title, seo_description
            )
            VALUES (
                'sin-thumb-2026-00000001', 'active', 300,
                ARRAY['Córdoba'], NOW(),
                '[]'::jsonb, 'ready',
                'Título', 'Descripción'
            )
            """
        )
    )
    db_session.commit()

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    export_ssg_artifacts()
    data = json.loads(mock_oci.get_uploaded("seo/ssg-seo-data.json"))
    ep = data["episodes"].get("sin-thumb-2026-00000001")
    assert ep is not None, "Episodio debería haber pasado la clasificación"
    assert ep["og_image"] is None


def test_genera_ambos_artefactos_en_oci(db_session, mock_oci, mocker):
    _seed_episode(db_session)

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    export_ssg_artifacts()
    keys = mock_oci.uploaded_keys()
    assert "seo/ssg-routes.json" in keys
    assert "seo/ssg-seo-data.json" in keys


def test_site_base_url_en_canonical(db_session, mock_oci, settings_override, mocker):
    settings_override.SITE_BASE_URL = "https://forestguard.com.ar"
    _seed_episode(db_session, slug="cordoba-2026-a3f2b1c9")

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    export_ssg_artifacts()
    data = json.loads(mock_oci.get_uploaded("seo/ssg-seo-data.json"))
    ep = data["episodes"]["cordoba-2026-a3f2b1c9"]
    assert ep["canonical"].startswith("https://forestguard.com.ar")
    assert not ep["canonical"].startswith("https://forestguard.freedynamicdns")


def test_zone_counts_sin_peticion_http(db_session, mock_oci, monkeypatch, mocker):
    """zone_counts se calcula localmente — no debe haber ninguna llamada de red."""
    import httpx

    monkeypatch.setattr(
        httpx,
        "get",
        lambda *a, **kw: (_ for _ in ()).throw(
            AssertionError("zone_counts no debe hacer peticiones HTTP")
        ),
    )
    _seed_episode(db_session, slug="cordoba-2026-a3f2b1c9", province="Córdoba")

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    result = export_ssg_artifacts()
    assert result["zone_counts"].get("sierras-cordoba", 0) >= 1
    assert result["zone_counts"].get("pampas-centrales", 0) >= 1


def test_generated_at_es_utc_con_sufijo_z(db_session, mock_oci, mocker):
    _seed_episode(db_session)

    storage_mock = mocker.patch(
        "app.services.storage_service.get_storage_service"
    )()

    def upload_bytes_side_effect(data: bytes, key: str, **kwargs):
        mock_oci.put_object(key, data)
        return None

    storage_mock.upload_bytes.side_effect = upload_bytes_side_effect

    export_ssg_artifacts()
    data = json.loads(mock_oci.get_uploaded("seo/ssg-seo-data.json"))
    assert data["generated_at"].endswith("Z")
    assert "+00:00" not in data["generated_at"]

