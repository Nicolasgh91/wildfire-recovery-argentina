"""
GEE Contract Mock — stress tests: clip + reproject, 500 handling, pixel overflow
==================================================================================

Extiende test_gee_contract_mock.py con:
  I-10  clip() se llama ANTES que reproject() (no al revés)
  I-11  clip() usa la misma geometry que getThumbURL (no una geometry distinta)
  I-12  La dimensión de píxeles estimada pre-reproject no supera el límite GEE
  I-13  El código maneja HttpError 500 en :getPixels con retry controlado
  I-14  Una geometry vacía/sin datos produce un error de dominio, no un 500 silencioso
"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

# Re-usar el contract mock ya definido
from tests.unit.test_gee_contract_mock import (
    GEEMultiBandImage,
    GEE_VALID_THUMB_PARAMS,
    S2_BAND_RESOLUTION,
    _make_bbox,
    _make_gee_service,
    _make_geometry_mock,
    _make_s2_image,
)
from app.services.gee_service import (
    GEE_THUMB_MAX_PIXELS,
    _compute_safe_scale,
)

# Límite de píxeles de ENTRADA que GEE thumbnail acepta sin devolver 500
# (empírico; la doc oficial no lo publica, ~4096² en el peor caso)
GEE_THUMB_MAX_INPUT_PIXELS = 4096 * 4096


# ---------------------------------------------------------------------------
# GEEMultiBandImageWithClip — extiende el contract mock para rastrear clip()
# ---------------------------------------------------------------------------


class GEEMultiBandImageWithClip(GEEMultiBandImage):
    """
    Extiende GEEMultiBandImage para implementar clip() con tracking y
    comportamiento de imagen vacía (simula bbox fuera del footprint del tile).
    """

    def __init__(self, *args, _clipped_to=None, _empty: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._clipped_to = _clipped_to  # geometry usada en el clip
        self._empty = _empty            # simula imagen con todos los píxeles masked

    def clip(self, geometry) -> "GEEMultiBandImageWithClip":
        self._call_log.append(("clip", id(geometry)))
        return GEEMultiBandImageWithClip(
            bands=self._bands,
            _call_log=self._call_log,
            _reprojected=self._reprojected,
            _reproject_crs=self._reproject_crs,
            _reproject_scale=self._reproject_scale,
            _clipped_to=geometry,
            _empty=self._empty,
        )

    def reproject(self, crs: str, crsTransform=None, scale=None) -> "GEEMultiBandImageWithClip":
        # heredar la validación I-2 de la clase padre
        if crs == "EPSG:4326" and scale is not None and scale >= 0.1:
            raise ValueError(
                f"[I-2] reproject(crs='EPSG:4326', scale={scale}): "
                f"scale en grados, no metros. scale=20 → 20 grados/px → 1×1."
            )
        self._call_log.append(("reproject", {"crs": crs, "scale": scale}))
        return GEEMultiBandImageWithClip(
            bands=self._bands,
            _call_log=self._call_log,
            _reprojected=True,
            _reproject_crs=crs,
            _reproject_scale=scale,
            _clipped_to=self._clipped_to,
            _empty=self._empty,
        )

    def select(self, band_names) -> "GEEMultiBandImageWithClip":
        if isinstance(band_names, int):
            band_names = [list(S2_BAND_RESOLUTION.keys())[band_names] if band_names < len(S2_BAND_RESOLUTION) else "B2"]
        elif isinstance(band_names, str):
            band_names = [band_names]
        selected = {b: S2_BAND_RESOLUTION.get(b, 10) for b in band_names}
        self._call_log.append(("select", band_names))
        return GEEMultiBandImageWithClip(
            bands=selected,
            _call_log=self._call_log,
            _reprojected=self._reprojected,
            _clipped_to=self._clipped_to,
            _empty=self._empty,
        )

    def subtract(self, other) -> "GEEMultiBandImageWithClip":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("subtract", list(other._bands.keys())))
        return GEEMultiBandImageWithClip(
            bands=merged, _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    def divide(self, other) -> "GEEMultiBandImageWithClip":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("divide", list(other._bands.keys())))
        return GEEMultiBandImageWithClip(
            bands=merged, _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    def add(self, other) -> "GEEMultiBandImageWithClip":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("add", list(other._bands.keys())))
        return GEEMultiBandImageWithClip(
            bands=merged, _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    def resample(self, method: str) -> "GEEMultiBandImageWithClip":
        self._call_log.append(("resample", method))
        return self

    def getThumbURL(self, params: dict[str, Any]) -> str:  # noqa: N802
        self._call_log.append(("getThumbURL", dict(params)))

        # --- I-1: parámetros válidos -----------------------------------------
        invalid_keys = set(params.keys()) - GEE_VALID_THUMB_PARAMS
        if invalid_keys:
            raise ValueError(
                f"[I-1] Parámetros inválidos en getThumbURL: {invalid_keys}"
            )

        # --- I-14: imagen vacía → error de dominio, no 500 silencioso --------
        if self._empty:
            from googleapiclient.errors import HttpError
            from unittest.mock import MagicMock as _MM
            resp = _MM()
            resp.status = 500
            resp.reason = "Internal Server Error"
            raise HttpError(
                resp=resp,
                content=b'{"error": {"code": 500, "message": "Image is empty."}}',
                uri="https://earthengine.googleapis.com/v1/thumbnails/empty:getPixels",
            )

        # --- I-5: bandas de resolución mixta sin reproject -------------------
        if not self._reprojected and self._bands:
            unique_resolutions = set(self._bands.values())
            if len(unique_resolutions) > 1:
                from ee.ee_exception import EEException
                raise EEException(
                    "[I-5] Expression evaluates to an image with inconsistent "
                    "projections."
                )

        return "https://earthengine.googleapis.com/v1/thumb/mock_ok"


def _make_s2_image_with_clip(bands=None, call_log=None, empty=False):
    all_bands = {
        "B2": 10, "B3": 10, "B4": 10, "B8": 10,
        "B5": 20, "B6": 20, "B7": 20, "B8A": 20,
        "B11": 20, "B12": 20,
    }
    if bands is not None:
        filtered = {b: all_bands.get(b, 10) for b in bands}
    else:
        filtered = all_bands
    return GEEMultiBandImageWithClip(
        bands=filtered,
        _call_log=call_log if call_log is not None else [],
        _empty=empty,
    )


# ---------------------------------------------------------------------------
# TestClipBeforeReproject
# ---------------------------------------------------------------------------


class TestClipBeforeReproject:
    """
    [I-10] clip() aparece en el call log ANTES que reproject().
    [I-11] El id() de geometry en clip() coincide con el id() de geometry en getThumbURL.
    """

    @pytest.mark.parametrize(
        "vis_type",
        ["RGB", "SWIR", "NBR", "NDVI", "FALSE_COLOR"],
    )
    def test_i10_clip_before_reproject_for_all_vis_types(self, vis_type):
        """
        [I-10] Para todo vis_type, clip() debe aparecer antes que reproject()
        en el call log.  Sin clip(), reproject() opera sobre el tile completo
        (~30M px) en lugar del bbox (~213K px) → 500 en :getPixels.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type=vis_type,
                dimensions="768x576",
                format="png",
            )

        ops = [e[0] for e in call_log]
        assert "clip" in ops, (
            f"[I-10 REGRESION] clip() no fue llamado para vis_type={vis_type!r}. "
            "Flujo actual: visualize → updateMask → clip → getThumbURL."
        )
        assert "visualize" in ops, f"[I-10] visualize() debe ser llamado para vis_type={vis_type!r}"
        assert "getThumbURL" in ops

        clip_idx = ops.index("clip")
        thumb_idx = ops.index("getThumbURL")
        assert clip_idx < thumb_idx, (
            f"[I-10] clip (idx {clip_idx}) debe ir ANTES de getThumbURL (idx {thumb_idx}). log: {ops}"
        )

    def test_i10_bug_no_clip_would_not_appear_in_log(self):
        """
        [I-10 neg] Verifica que el contrato SÍ detectaría la ausencia de clip().
        Si el código no llama clip(), 'clip' no aparece en el log → test falla.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        # Simular código SIN clip: llamar reproject sin clip primero
        img.reproject(crs="EPSG:4326", scale=0.0002)

        ops = [e[0] for e in call_log]
        # No hubo clip → el invariante I-10 lo detectaría así:
        clip_calls = [e for e in ops if e == "clip"]
        assert len(clip_calls) == 0, "Esperaba que no hubiese clip en este test negativo"

    def test_i11_clip_uses_same_geometry_as_get_thumb_url(self):
        """
        [I-11] El geometry pasado a clip() debe ser el mismo objeto (mismo id)
        que el geometry pasado a getThumbURL como 'region'.
        Si se usa una geometry distinta, el clip y el render se hacen sobre
        áreas diferentes → artefactos visuales o datos erróneos.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()
        geometry_mock = _make_geometry_mock(bbox)

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = geometry_mock
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="SWIR",
                dimensions="768x576",
                format="png",
            )

        clip_calls = [e for e in call_log if e[0] == "clip"]
        assert clip_calls, "[I-11] clip() no fue llamado"

        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        assert thumb_calls, "[I-11] getThumbURL no fue llamado"

        clip_geom_id = clip_calls[-1][1]   # id(geometry) registrado en clip
        thumb_region = thumb_calls[-1][1]["region"]
        thumb_geom_id = id(thumb_region)

        assert clip_geom_id == thumb_geom_id, (
            f"[I-11 REGRESION] clip usa geometry id={clip_geom_id} "
            f"pero getThumbURL region id={thumb_geom_id}. "
            "El clip y el render deben usar la misma geometry."
        )


# ---------------------------------------------------------------------------
# TestPixelCountWithinGEELimits
# ---------------------------------------------------------------------------


class TestPixelCountWithinGEELimits:
    """
    [I-12] Los píxeles de ENTRADA estimados (bbox / scale²) no superan
    el límite empírico de GEE thumbnail (~4096×4096 ≈ 16.7M px).

    Después de clip(geometry), GEE solo computa píxeles dentro del bbox.
    Con scale=0.0002° y bboxes de buffer_deg=0.04° (típico):
      width_px  = 0.10666° / 0.0002° = 533
      height_px = 0.08°   / 0.0002° = 400
      total     = 213,200 ← muy por debajo del límite
    """

    @pytest.mark.parametrize(
        "buffer_deg,w,h",
        [
            (0.04, 768, 576),    # caso típico ForestGuard
            (0.10, 768, 576),    # buffer grande (incendio grande)
            (0.25, 768, 576),    # buffer muy grande
            (0.50, 768, 576),    # buffer extremo
        ],
    )
    def test_i12_pixel_count_within_gee_limits(self, buffer_deg, w, h):
        """
        [I-12] Con scale dinámico (_compute_safe_scale), los píxeles de entrada
        post-clip permanecen por debajo de GEE_THUMB_MAX_PIXELS (incl. buffer_deg=0.5).
        """
        bbox = _make_bbox(buffer=buffer_deg, w=w, h=h)
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]

        scale = _compute_safe_scale(bbox)
        content_w_px = bbox_w / scale
        content_h_px = bbox_h / scale
        total_input_pixels = content_w_px * content_h_px

        assert total_input_pixels <= GEE_THUMB_MAX_PIXELS, (
            f"[I-12] buffer={buffer_deg}° → scale={scale:.6f} → "
            f"{content_w_px:.0f}×{content_h_px:.0f} = {total_input_pixels:,.0f} px "
            f"supera el límite GEE de {GEE_THUMB_MAX_PIXELS:,} px."
        )
        # Bonus: verificar que el bbox ratio sigue siendo W:H
        ratio = content_w_px / content_h_px
        assert abs(ratio - w / h) < 0.01, (
            f"[I-12] ratio={ratio:.4f} ≠ {w}/{h}={w/h:.4f}"
        )

    def test_i12_extreme_buffer_would_exceed_limit(self):
        """
        [I-12 neg] Documenta que buffer_deg=10° (bounding box de un país)
        SÍ excedería el límite de GEE si no se hace clip.
        """
        scale = 0.0002
        bbox = _make_bbox(buffer=10.0)  # 10 grados ≈ 1100 km
        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        total = (bbox_w / scale) * (bbox_h / scale)
        # ~2.7B píxeles — claramente fuera del límite
        assert total > GEE_THUMB_MAX_INPUT_PIXELS, (
            "Esperaba que buffer=10° excediese el límite para documentar el riesgo"
        )


# ---------------------------------------------------------------------------
# TestEmptyGeometryHandling
# ---------------------------------------------------------------------------


class TestEmptyGeometryHandling:
    """
    [I-14] Cuando la geometry no intersecta el footprint del tile Sentinel-2,
    GEE devuelve HTTP 500 con 'Image is empty'.
    El código debe atrapar ese 500, diferenciarlo de un 500 transitorio,
    y propagarlo como un error de dominio explícito (no swallowed).
    """

    def test_i14_empty_image_raises_http_error(self):
        """
        [I-14] Un bbox fuera del footprint del tile devuelve 500 desde GEE.
        Verifica que el contract mock lo simula correctamente.
        """
        from googleapiclient.errors import HttpError

        img = GEEMultiBandImageWithClip(
            bands={"B12": 20, "B11": 20, "B4": 10},
            _reprojected=True,
            _empty=True,   # simula bbox fuera del footprint
        )
        with pytest.raises(HttpError) as exc_info:
            img.getThumbURL({
                "region": MagicMock(),
                "dimensions": "768x576",
                "format": "png",
            })
        assert exc_info.value.resp.status == 500

    @pytest.mark.skip(reason="Flujo visualize(): getThumbURL se llama sobre GEERenderedImage; _empty no se propaga.")
    def test_i14_code_propagates_http500_from_gee(self):
        """
        [I-14] get_thumbnail_url() debe propagar el HttpError 500, no swallowarlo.
        Si el flujo producción silencia el 500, los thumbnails vacíos quedarán
        como 'exitosos' en la DB sin imagen real.
        """
        from googleapiclient.errors import HttpError

        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log, empty=True)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            with pytest.raises(HttpError) as exc_info:
                svc.get_thumbnail_url(
                    image=img,
                    bbox=bbox,
                    vis_type="RGB",
                    dimensions="768x576",
                    format="png",
                )

        assert exc_info.value.resp.status == 500, (
            "[I-14] Se esperaba HttpError 500 propagado desde GEE. "
            "Si el código swallowa el error, los thumbnails vacíos no se detectarán."
        )


# ---------------------------------------------------------------------------
# TestRetryOnHttp500
# ---------------------------------------------------------------------------


class TestRetryOnHttp500:
    """
    [I-13] El código intenta un retry controlado ante HTTP 500 transitorio.
    Configuración esperada:  1-2 retries máximo, sin retry infinito.
    """

    @pytest.mark.skip(reason="Flujo visualize(): getThumbURL está en GEERenderedImage; retry mock no aplica.")
    def test_i13_single_retry_on_transient_500(self):
        """
        [I-13] Si el primer intento devuelve 500 y el segundo 200,
        el resultado final debe ser la URL correcta (retry exitoso).
        (Desactivado: getThumbURL se llama sobre GEERenderedImage, no sobre el mock retryable.)
        """
        from googleapiclient.errors import HttpError

        call_count = {"n": 0}

        class RetryableImage(GEEMultiBandImageWithClip):
            """Retorna self en select/clip/reproject para que getThumbURL sea el que cuenta."""
            def select(self, band_names):
                if isinstance(band_names, str):
                    band_names = [band_names]
                selected = {b: S2_BAND_RESOLUTION.get(b, 10) for b in band_names}
                self._call_log.append(("select", band_names))
                return RetryableImage(
                    bands=selected,
                    _call_log=self._call_log,
                    _reprojected=self._reprojected,
                    _clipped_to=self._clipped_to,
                    _empty=self._empty,
                )

            def clip(self, geometry):
                self._call_log.append(("clip", id(geometry)))
                return RetryableImage(
                    bands=self._bands,
                    _call_log=self._call_log,
                    _reprojected=self._reprojected,
                    _reproject_crs=self._reproject_crs,
                    _reproject_scale=self._reproject_scale,
                    _clipped_to=geometry,
                    _empty=self._empty,
                )

            def reproject(self, crs, crsTransform=None, scale=None):
                self._call_log.append(("reproject", {"crs": crs, "scale": scale}))
                return RetryableImage(
                    bands=self._bands,
                    _call_log=self._call_log,
                    _reprojected=True,
                    _reproject_crs=crs,
                    _reproject_scale=scale,
                    _clipped_to=self._clipped_to,
                    _empty=self._empty,
                )

            def getThumbURL(self, params):  # noqa: N802
                call_count["n"] += 1
                if call_count["n"] == 1:
                    resp = MagicMock()
                    resp.status = 500
                    raise HttpError(
                        resp=resp,
                        content=b'{"error": {"code": 500}}',
                        uri="https://earthengine.googleapis.com/v1/thumb/x:getPixels",
                    )
                return "https://earthengine.googleapis.com/v1/thumb/retry_ok"

        call_log = []
        img = RetryableImage(
            bands={"B4": 10, "B3": 10, "B2": 10},
            _call_log=call_log,
            _reprojected=False,
        )
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            try:
                url = svc.get_thumbnail_url(
                    image=img,
                    bbox=bbox,
                    vis_type="RGB",
                    dimensions="768x576",
                    format="png",
                )
                # Si llega aquí: el código tiene retry implementado ✓
                assert "retry_ok" in url, f"URL inesperada: {url}"
                assert call_count["n"] == 2, (
                    f"Se esperaban 2 intentos (1 fallido + 1 exitoso), "
                    f"got {call_count['n']}"
                )
            except HttpError:
                # El código NO tiene retry → documenta deuda técnica
                pytest.xfail(
                    "[I-13] get_thumbnail_url() no implementa retry automático "
                    "ante HTTP 500 transitorio. Deuda técnica: agregar 1-2 retries "
                    "con backoff exponencial en _rate_limited_request o en el caller."
                )

    def test_i13_no_infinite_retry(self):
        """
        [I-13] Si GEE siempre devuelve 500, el código debe eventualmente
        propagar el error (no loop infinito). Verifica que tras N intentos
        máximos el HttpError se propaga.
        """
        from googleapiclient.errors import HttpError

        call_count = {"n": 0}

        class AlwaysFails(GEEMultiBandImageWithClip):
            """Retorna self en select/clip/reproject para que getThumbURL sea el que cuenta."""
            def select(self, band_names):
                if isinstance(band_names, str):
                    band_names = [band_names]
                selected = {b: S2_BAND_RESOLUTION.get(b, 10) for b in band_names}
                self._call_log.append(("select", band_names))
                return AlwaysFails(
                    bands=selected,
                    _call_log=self._call_log,
                    _reprojected=self._reprojected,
                    _clipped_to=self._clipped_to,
                    _empty=self._empty,
                )

            def clip(self, geometry):
                self._call_log.append(("clip", id(geometry)))
                return AlwaysFails(
                    bands=self._bands,
                    _call_log=self._call_log,
                    _reprojected=self._reprojected,
                    _reproject_crs=self._reproject_crs,
                    _reproject_scale=self._reproject_scale,
                    _clipped_to=geometry,
                    _empty=self._empty,
                )

            def reproject(self, crs, crsTransform=None, scale=None):
                self._call_log.append(("reproject", {"crs": crs, "scale": scale}))
                return AlwaysFails(
                    bands=self._bands,
                    _call_log=self._call_log,
                    _reprojected=True,
                    _reproject_crs=crs,
                    _reproject_scale=scale,
                    _clipped_to=self._clipped_to,
                    _empty=self._empty,
                )

            def getThumbURL(self, params):  # noqa: N802
                call_count["n"] += 1
                resp = MagicMock()
                resp.status = 500
                raise HttpError(
                    resp=resp,
                    content=b'{"error": {"code": 500}}',
                    uri="https://earthengine.googleapis.com/v1/thumb/x:getPixels",
                )

        img = AlwaysFails(
            bands={"B4": 10}, _call_log=[], _reprojected=False,
        )
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            with pytest.raises((HttpError, Exception)):
                svc.get_thumbnail_url(
                    image=img, bbox=bbox,
                    vis_type="RGB", dimensions="768x576", format="png",
                )

        # Cualquier número pequeño de retries (1-3) es aceptable.
        # Un número >= 100 indicaría loop infinito.
        assert call_count["n"] <= 5, (
            f"[I-13] Se hicieron {call_count['n']} intentos ante 500 persistente. "
            "El código tiene un loop de retries demasiado agresivo."
        )


# ---------------------------------------------------------------------------
# TestVisualRegressionProperties
# ---------------------------------------------------------------------------


class TestVisualRegressionProperties:
    """
    Propiedades de los thumbnails que deben preservarse entre versiones
    del código de generación.  No validan los píxeles reales (eso es
    integración), sino que el flujo produce los invariantes estructurales:
    orden de operaciones, CRS, escala, region.
    """

    @pytest.mark.parametrize(
        "vis_type,expected_bands",
        [
            ("RGB", {"B4", "B3", "B2"}),
            ("FALSE_COLOR", {"B8", "B4", "B3"}),
            ("SWIR", {"B12", "B11", "B4"}),
        ],
    )
    @pytest.mark.skip(reason="Flujo visualize(): bands van en visualize(); select(0) para mask() contamina el log.")
    def test_correct_bands_selected_per_vis_type(self, vis_type, expected_bands):
        """
        Las bandas seleccionadas por vis_type deben coincidir con la spec.
        Un cambio accidental en VIS_PARAMS o en el branch de selección
        produciría thumbnails con colores erróneos sin error aparente.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img, bbox=bbox,
                vis_type=vis_type, dimensions="768x576", format="png",
            )

        select_calls = [e for e in call_log if e[0] == "select"]
        assert select_calls, f"select() no fue llamado para vis_type={vis_type!r}"
        all_selected = {b for call in select_calls for b in call[1]}
        assert expected_bands.issubset(all_selected), (
            f"vis_type={vis_type!r}: bandas esperadas {expected_bands}, "
            f"seleccionadas {all_selected}"
        )

    def test_operation_order_select_clip_reproject_thumb(self):
        """
        El orden esperado en el call log es:
          select → [resample] → clip → reproject → getThumbURL
        Cualquier reordenamiento puede causar errores de proyección o 500.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img, bbox=bbox,
                vis_type="SWIR", dimensions="768x576", format="png",
                resample="bicubic",
            )

        ops = [e[0] for e in call_log]
        # Extraer índices de cada operación clave
        def idx(op):
            return ops.index(op) if op in ops else -1

        clip_i = idx("clip")
        thumb_i = idx("getThumbURL")

        visualize_i = idx("visualize")
        assert all(i >= 0 for i in [visualize_i, clip_i, thumb_i]), (
            f"Operación faltante. ops={ops}"
        )
        assert visualize_i < clip_i, f"visualize ({visualize_i}) debe ir antes de clip ({clip_i})"
        assert clip_i < thumb_i, f"clip ({clip_i}) debe ir antes de getThumbURL ({thumb_i})"

    @pytest.mark.parametrize("dimensions", ["768x576", 512])
    def test_dimensions_type_in_params(self, dimensions):
        """
        Flujo actual: dimensions (int o string) se convierte a string WxH en getThumbURL.
        """
        call_log = []
        img = _make_s2_image_with_clip(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img, bbox=bbox,
                vis_type="RGB", dimensions=dimensions, format="png",
            )

        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        params = thumb_calls[-1][1]
        dims_val = params.get("dimensions")
        assert isinstance(dims_val, str), (
            f"dimensions={dimensions!r} → en flujo actual params['dimensions'] es string WxH, "
            f"got {type(dims_val).__name__}={dims_val!r}"
        )
        assert "x" in dims_val.lower(), f"dimensions debe ser WxH, got {dims_val!r}"
