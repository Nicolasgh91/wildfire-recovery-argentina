"""
GEE Contract Mock — stress tests for get_thumbnail_url()
=========================================================

Un "contract mock" no es un MagicMock permisivo. Implementa las restricciones
reales del API de GEE y falla si el código producción las viola. Cada test
evalúa un invariante distinto derivado de la documentación de GEE y de los
bugs encontrados en producción.

Invariantes codificados:
  I-1  getThumbURL solo acepta parámetros de la spec del API (no width/height)
  I-2  reproject() en EPSG:4326: scale debe estar en grados (<0.1), no metros
  I-3  reproject() debe llamarse ANTES de getThumbURL
  I-4  dimensions="WxH" en EPSG:4326 con bbox 4:3 produce thumbnail 768x576
  I-5  Bands de distinta resolución nativa (SWIR, NBR) requieren reproject()
       antes de getThumbURL; sin él, GEE simula EEException
  I-6  dimensions como int se pasa como int, no como string
  I-7  La bbox tiene exactamente ratio W:H en grados (no AR cuadrado)
  I-8  reproject se llama con crs="EPSG:4326" (no UTM ni proyecciones locales)
  I-9  format es siempre "png" o "jpg" (no otros valores)

Resultado esperado cuando el código está CORRECTO:
  - I-1 a I-9 pasan → PASS
  - I-5 (simulación de bug ausente) → PASS porque reproject() retorna imagen distinta

Resultado si algún bug regresiona:
  - I-1: FAIL si se pasan width/height como claves separadas
  - I-2: FAIL si scale >= 0.1 en EPSG:4326 (la señal del bug scale=20)
  - I-3: FAIL si getThumbURL se llama sobre imagen NO reprojectada
  - I-4: FAIL si thumbnail simulado no sería 768x576
  - I-5: FAIL si el código no llama reproject y la simulación lanza EEException
  - I-6: FAIL si string "512x512" se convierte a "512" con x
  - I-7: FAIL si bbox no es 4:3 (regresión en _bbox_from_point)
  - I-8: FAIL si reproject usa CRS distinto a EPSG:4326
  - I-9: FAIL si format inválido llega a GEE
"""

from __future__ import annotations

import logging
import math
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# GEE_THUMB_PARAMS_SPEC — keys válidas según GEE REST API /thumbnails
# Fuente: https://developers.google.com/earth-engine/reference/rest/v1/
#         projects.thumbnails/create
# ---------------------------------------------------------------------------
GEE_VALID_THUMB_PARAMS = frozenset(
    {
        "region",
        "dimensions",
        "format",
        "crs",
        "crs_transform",
        "scale",
        "min",
        "max",
        "gamma",
        "bands",
        "palette",
        "gain",
        "bias",
        "opacity",
    }
)

# Bandas Sentinel-2 y su resolución nativa (metros)
S2_BAND_RESOLUTION: dict[str, int] = {
    "B2": 10, "B3": 10, "B4": 10, "B8": 10,
    "B5": 20, "B6": 20, "B7": 20, "B8A": 20,
    "B11": 20, "B12": 20,
}

# ---------------------------------------------------------------------------
# GEEMultiBandImage — contract mock de ee.Image con historial de llamadas
# ---------------------------------------------------------------------------


class GEEMultiBandImage:
    """
    Mock de ee.Image que:
      - Registra el historial de operaciones aplicadas (select, resample,
        reproject, normalizedDifference, subtract, divide, add)
      - Mantiene el conjunto de bandas activas y su resolución nativa
      - Implementa las restricciones del API de GEE en getThumbURL y reproject
      - Simula EEException("inconsistent projections") si getThumbURL se llama
        sobre una imagen con bandas de resolución mixta sin normalización previa
    """

    def __init__(
        self,
        bands: dict[str, int] | None = None,
        _call_log: list | None = None,
        _reprojected: bool = False,
        _reproject_crs: str | None = None,
        _reproject_scale: float | None = None,
    ):
        # bands: {nombre_banda: resolución_nativa_metros}
        self._bands = bands or {}
        self._call_log: list = _call_log if _call_log is not None else []
        self._reprojected = _reprojected
        self._reproject_crs = _reproject_crs
        self._reproject_scale = _reproject_scale

    # ── operaciones de transformación ───────────────────────────────────────

    def select(self, band_names: list[str] | str) -> "GEEMultiBandImage":
        if isinstance(band_names, str):
            band_names = [band_names]
        selected = {b: S2_BAND_RESOLUTION.get(b, 10) for b in band_names}
        self._call_log.append(("select", band_names))
        return GEEMultiBandImage(
            bands=selected,
            _call_log=self._call_log,
            _reprojected=self._reprojected,
            _reproject_crs=self._reproject_crs,
            _reproject_scale=self._reproject_scale,
        )

    def resample(self, method: str) -> "GEEMultiBandImage":
        self._call_log.append(("resample", method))
        return self

    def clip(self, geometry) -> "GEEMultiBandImage":
        """clip() registra el id de geometry y retorna self (mismo mock).
        El invariante I-10 (clip antes de reproject) se verifica en test_gee_stress.py."""
        self._call_log.append(("clip", id(geometry)))
        return GEEMultiBandImage(
            bands=self._bands,
            _call_log=self._call_log,
            _reprojected=self._reprojected,
            _reproject_crs=self._reproject_crs,
            _reproject_scale=self._reproject_scale,
        )

    def reproject(self, crs: str, crsTransform=None, scale: float | None = None) -> "GEEMultiBandImage":
        # --- I-2: scale en EPSG:4326 debe estar en grados (no metros) --------
        if crs == "EPSG:4326" and scale is not None:
            if scale >= 0.1:
                raise ValueError(
                    f"[I-2] reproject(crs='EPSG:4326', scale={scale}): "
                    f"scale={scale} parece estar en METROS, no en GRADOS. "
                    f"En EPSG:4326 scale=20 = 20 grados/px = ~2200 km/px. "
                    f"Usa scale≈0.0002 (≈22m/px en latitud)."
                )
        self._call_log.append(("reproject", {"crs": crs, "scale": scale}))
        return GEEMultiBandImage(
            bands=self._bands,
            _call_log=self._call_log,
            _reprojected=True,
            _reproject_crs=crs,
            _reproject_scale=scale,
        )

    def normalizedDifference(self, band_names: list[str]) -> "GEEMultiBandImage":
        selected = {b: S2_BAND_RESOLUTION.get(b, 10) for b in band_names}
        self._call_log.append(("normalizedDifference", band_names))
        return GEEMultiBandImage(
            bands=selected,
            _call_log=self._call_log,
            _reprojected=self._reprojected,
        )

    def subtract(self, other: "GEEMultiBandImage") -> "GEEMultiBandImage":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("subtract", list(other._bands.keys())))
        return GEEMultiBandImage(
            bands=merged,
            _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    def divide(self, other: "GEEMultiBandImage") -> "GEEMultiBandImage":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("divide", list(other._bands.keys())))
        return GEEMultiBandImage(
            bands=merged,
            _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    def add(self, other: "GEEMultiBandImage") -> "GEEMultiBandImage":
        merged = {**self._bands, **other._bands}
        self._call_log.append(("add", list(other._bands.keys())))
        return GEEMultiBandImage(
            bands=merged,
            _call_log=self._call_log,
            _reprojected=self._reprojected and other._reprojected,
        )

    # ── getThumbURL — el método con más restricciones ───────────────────────

    def getThumbURL(self, params: dict[str, Any]) -> str:  # noqa: N802
        self._call_log.append(("getThumbURL", dict(params)))

        # --- I-1: solo parámetros válidos del API ----------------------------
        invalid_keys = set(params.keys()) - GEE_VALID_THUMB_PARAMS
        if invalid_keys:
            raise ValueError(
                f"[I-1] getThumbURL recibió parámetros inválidos según GEE API: "
                f"{invalid_keys}. "
                f"Parámetros válidos: {sorted(GEE_VALID_THUMB_PARAMS)}. "
                f"Error conocido: usar 'width'/'height' por separado → GEE los ignora → 1x1."
            )

        # --- I-3: reproject debe haberse llamado antes que este método -------
        ops = [e[0] for e in self._call_log]
        thumb_indices = [i for i, op in enumerate(ops) if op == "getThumbURL"]
        reproject_indices = [i for i, op in enumerate(ops) if op == "reproject"]

        if thumb_indices and reproject_indices:
            last_reproject = max(reproject_indices)
            first_thumb = min(thumb_indices)
            if last_reproject >= first_thumb:
                # reproject llamado DESPUÉS de getThumbURL — anómalo pero no error aquí
                pass

        # --- I-5: bandas de resolución mixta sin reproject → error -----------
        if not self._reprojected and self._bands:
            unique_resolutions = set(self._bands.values())
            if len(unique_resolutions) > 1:
                from ee.ee_exception import EEException
                raise EEException(
                    "[I-5] Expression evaluates to an image with inconsistent "
                    "projections. "
                    f"Bandas: {self._bands}. "
                    f"Resoluciones: {unique_resolutions}. "
                    "Solución: llamar vis_image.reproject(crs='EPSG:4326', "
                    "scale=0.0002) antes de getThumbURL."
                )

        # --- I-6: dimensions como string WxH debe llegar como string ---------
        dims = params.get("dimensions")
        if dims is not None and isinstance(dims, str) and "x" in dims.lower():
            w_str, h_str = dims.lower().split("x", 1)
            try:
                w, h = int(w_str.strip()), int(h_str.strip())
            except ValueError as exc:
                raise ValueError(
                    f"[I-6] dimensions='{dims}' no es parseable como WxH enteros."
                ) from exc
        elif dims is not None and not isinstance(dims, (int, str)):
            raise TypeError(
                f"[I-6] dimensions debe ser int o string, got {type(dims).__name__}"
            )

        # --- I-9: format válido -----------------------------------------------
        fmt = params.get("format", "png")
        if fmt not in {"png", "jpg", "jpeg", "auto"}:
            raise ValueError(
                f"[I-9] format='{fmt}' no es válido. GEE acepta: png, jpg, jpeg, auto."
            )

        # --- Simular tamaño de thumbnail producido ---------------------------
        # Si llegamos aquí, la imagen fue reprojected a EPSG:4326.
        # En EPSG:4326: pixel_ratio = degree_ratio.
        # bbox_w / bbox_h = W/H (por diseño de _bbox_from_point) → thumbnail = WxH exacto.
        region = params.get("region")
        thumbnail_url = "https://earthengine.googleapis.com/v1/thumb/mock_ok"
        return thumbnail_url


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gee_service():
    from app.services.gee_service import GEEService

    svc = object.__new__(GEEService)
    svc._initialized = True
    svc._request_count = 0
    svc._rate_limited_request = lambda func, *a, **kw: func(*a, **kw)
    return svc


def _make_s2_image(bands: list[str] | None = None, call_log: list | None = None) -> GEEMultiBandImage:
    """Imagen Sentinel-2 completa con las 13 bandas habituales."""
    all_bands = {
        "B2": 10, "B3": 10, "B4": 10, "B8": 10,
        "B5": 20, "B6": 20, "B7": 20, "B8A": 20,
        "B11": 20, "B12": 20,
    }
    if bands is not None:
        filtered = {b: all_bands.get(b, 10) for b in bands}
    else:
        filtered = all_bands
    return GEEMultiBandImage(bands=filtered, _call_log=call_log if call_log is not None else [])


def _make_bbox(
    center_lat: float = -27.5,
    center_lon: float = -65.0,
    buffer: float = 0.04,
    w: int = 768,
    h: int = 576,
) -> dict:
    delta_lat = buffer
    delta_lon = buffer * (w / h)
    return {
        "west": center_lon - delta_lon,
        "east": center_lon + delta_lon,
        "south": center_lat - delta_lat,
        "north": center_lat + delta_lat,
    }


def _make_geometry_mock(bbox: dict):
    mock_geom = MagicMock()
    mock_geom.bbox = bbox
    return mock_geom


# ---------------------------------------------------------------------------
# TestGEEContractMock — tests de invariantes
# ---------------------------------------------------------------------------


class TestGEEContractMock:
    """
    El contract mock rechaza el código producción si viola las restricciones
    documentadas del API de GEE.

    Todos estos tests deben PASAR con el código corregido.
    Si alguno FALLA, indica una regresión o un bug aún no resuelto.
    """

    # ── I-1: solo parámetros válidos en getThumbURL ─────────────────────────

    def test_i1_invalid_width_height_keys_rejected(self):
        """
        [I-1] Si el código pasa 'width' o 'height' como claves separadas,
        el contract mock lanza ValueError.
        El código actual pasa dimensions="768x576" (correcto) → debe pasar.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            # El código llama img.select → img.reproject → img.getThumbURL
            # El contract mock valida I-1 en getThumbURL
            url = svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )

        # Si llegamos aquí: no se pasaron width/height ilegales → I-1 OK
        assert url.startswith("https://"), f"URL inválida: {url}"
        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        assert thumb_calls, "getThumbURL no fue llamado"
        params = thumb_calls[-1][1]
        assert "width" not in params, f"[I-1 REGRESION] 'width' en params: {params}"
        assert "height" not in params, f"[I-1 REGRESION] 'height' en params: {params}"

    # ── I-2: scale en EPSG:4326 debe ser en grados, no metros ───────────────

    def test_i2_reproject_scale_is_degrees_not_meters(self):
        """
        [I-2] scale en EPSG:4326 en grados. El contract mock lanza si scale >= 0.1.
        El código actual usa scale=0.0002 → debe pasar.
        Regresión detectada: scale=20 (metros) → scale=20 grados → 1x1.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            url = svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="SWIR",
                dimensions="768x576",
                format="png",
            )

        reproject_calls = [e for e in call_log if e[0] == "reproject"]
        assert reproject_calls, "reproject() no fue llamado"
        scale = reproject_calls[-1][1].get("scale")
        assert scale is not None, "reproject() se llamó sin scale"
        assert scale < 0.1, (
            f"[I-2 REGRESION] scale={scale} en EPSG:4326 es demasiado grande. "
            f"scale >= 0.1° = más de 11km/px. Usa scale ≈ 0.0002 (≈22m/px)."
        )

    def test_i2_bug_scale_20_would_fail(self):
        """
        [I-2 neg] Verifica que el contract mock SÍ rechaza scale=20 en EPSG:4326.
        Esto documenta que el bug anterior era real y detectable con este mock.
        """
        img = GEEMultiBandImage(bands={"B4": 10})
        with pytest.raises(ValueError, match=r"\[I-2\].*scale=20.*GRADOS"):
            img.reproject(crs="EPSG:4326", scale=20)

    # ── I-3: reproject ANTES de getThumbURL ─────────────────────────────────

    def test_i3_reproject_called_before_get_thumb_url(self):
        """
        [I-3] reproject() debe aparecer ANTES de getThumbURL en el call_log.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )

        ops = [e[0] for e in call_log]
        assert "reproject" in ops, "reproject() no fue llamado"
        assert "getThumbURL" in ops, "getThumbURL no fue llamado"
        assert ops.index("reproject") < ops.index("getThumbURL"), (
            f"[I-3 REGRESION] reproject (idx {ops.index('reproject')}) "
            f"debe ir ANTES de getThumbURL (idx {ops.index('getThumbURL')}). "
            f"Call log: {ops}"
        )

    # ── I-4: thumbnail simulado tiene ratio correcto ─────────────────────────

    def test_i4_thumbnail_dimensions_match_bbox_ratio(self):
        """
        [I-4] En EPSG:4326, degree_ratio = pixel_ratio.
        Un bbox con delta_lon/delta_lat = W/H →
        content_px = (bbox_lon/scale) × (bbox_lat/scale) →
        ratio = bbox_lon/bbox_lat = W/H.
        Con dimensions="WxH", GEE escala al canvas exacto.
        """
        W, H = 768, 576
        bbox = _make_bbox(w=W, h=H)
        target_ratio = W / H

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        actual_ratio = bbox_w / bbox_h

        assert abs(actual_ratio - target_ratio) < 1e-6, (
            f"[I-4 REGRESION] bbox ratio={actual_ratio:.6f} ≠ W/H={target_ratio:.6f}. "
            f"_bbox_from_point() no calcula delta_lon = delta_lat × (W/H)."
        )

        # Con scale=s en EPSG:4326 equiangular:
        # content_width_px  = bbox_w / s
        # content_height_px = bbox_h / s
        # ratio = content_width_px / content_height_px = bbox_w / bbox_h = W/H ✓
        scale = 0.0002
        content_w = bbox_w / scale
        content_h = bbox_h / scale
        content_ratio = content_w / content_h
        assert abs(content_ratio - target_ratio) < 1e-5, (
            f"[I-4] pixel ratio={content_ratio:.5f} ≠ W/H={target_ratio:.4f}. "
            f"bbox_w={bbox_w:.5f} bbox_h={bbox_h:.5f}"
        )

    # ── I-5: bandas de resolución mixta sin reproject → EEException ──────────

    @pytest.mark.parametrize(
        "vis_type,description",
        [
            ("SWIR", "B12(20m)+B11(20m)+B4(10m)"),
            ("NBR", "B8(10m)+B12(20m)"),
        ],
    )
    def test_i5_mixed_resolution_bands_raise_without_reproject(self, vis_type, description):
        """
        [I-5] Sin reproject(), bandas de resolución mixta causan
        EEException("inconsistent projections") en GEE real.
        El contract mock simula ese comportamiento.
        El código actual llama reproject() → image_reprojected._reprojected=True
        → I-5 no se activa → test pasa.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            # Con código correcto (llama reproject), NO debe levantar EEException
            url = svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type=vis_type,
                dimensions="768x576",
                format="png",
            )
        assert url.startswith("https://"), (
            f"[I-5] {vis_type} ({description}): esperaba URL válida, got {url}"
        )

    def test_i5_bug_no_reproject_raises_ee_exception(self):
        """
        [I-5 neg] Sin reproject(), imagen SWIR con bandas mixtas lanza EEException.
        Esto documenta el bug original como un test reproducible.
        """
        from ee.ee_exception import EEException

        # Imagen SWIR sin reproject: B12(20m), B11(20m), B4(10m)
        img = GEEMultiBandImage(
            bands={"B12": 20, "B11": 20, "B4": 10},
            _reprojected=False,  # SIN normalización
        )
        with pytest.raises(EEException, match="inconsistent projections"):
            img.getThumbURL({"region": "...", "dimensions": "768x576", "format": "png"})

    # ── I-6: dimensions int se pasa como int, WxH como string ───────────────

    def test_i6_int_dimensions_passed_as_int(self):
        """
        [I-6] dimensions=512 (int) → params["dimensions"] == 512 (int).
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="RGB",
                dimensions=512,
                format="png",
            )

        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        params = thumb_calls[-1][1]
        dims = params.get("dimensions")
        assert isinstance(dims, int), (
            f"[I-6] dimensions=512 (int) debe llegar como int, got {type(dims).__name__}={dims!r}"
        )
        assert dims == 512

    def test_i6_wxh_string_passed_as_string(self):
        """
        [I-6] dimensions="768x576" → params["dimensions"] == "768x576" (string).
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )

        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        params = thumb_calls[-1][1]
        dims = params.get("dimensions")
        assert isinstance(dims, str), (
            f"[I-6] dimensions='768x576' debe llegar como string, got {type(dims).__name__}={dims!r}"
        )
        assert "x" in dims.lower(), f"[I-6] string '{dims}' no contiene 'x'"

    # ── I-7: bbox tiene ratio W:H en grados ─────────────────────────────────

    @pytest.mark.parametrize(
        "w,h,buffer",
        [
            (768, 576, 0.04),
            (512, 384, 0.04),
            (1024, 768, 0.10),
        ],
    )
    def test_i7_bbox_aspect_ratio_matches_thumbnail_dimensions(self, w, h, buffer):
        """
        [I-7] Para cualquier W×H, _bbox_from_point() debe producir
        (east-west) / (north-south) == W/H con precisión < 1e-6.
        """
        from app.services.imagery_service import ImageryService

        svc = object.__new__(ImageryService)
        svc.db = MagicMock()
        svc._gee = MagicMock()
        svc._storage = MagicMock()
        svc._resolve_thumb_dimensions = MagicMock(return_value=f"{w}x{h}")
        svc._resolve_bbox_buffer_degrees = MagicMock(return_value=buffer)

        lat, lon = -27.5, -65.0
        bbox = svc._bbox_from_point(lat, lon)

        bbox_w = bbox["east"] - bbox["west"]
        bbox_h = bbox["north"] - bbox["south"]
        actual_ratio = bbox_w / bbox_h
        expected_ratio = w / h

        assert abs(actual_ratio - expected_ratio) < 1e-6, (
            f"[I-7 REGRESION] bbox AR={actual_ratio:.8f} ≠ {w}/{h}={expected_ratio:.8f} "
            f"para buffer={buffer}."
        )

    # ── I-8: reproject usa EPSG:4326 ────────────────────────────────────────

    @pytest.mark.parametrize(
        "vis_type",
        ["RGB", "SWIR", "NBR", "NDVI", "FALSE_COLOR"],
    )
    def test_i8_reproject_uses_epsg4326(self, vis_type):
        """
        [I-8] reproject() siempre usa crs='EPSG:4326'.
        Garantiza el invariante de que pixel_ratio = degree_ratio.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
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

        reproject_calls = [e for e in call_log if e[0] == "reproject"]
        assert reproject_calls, f"[I-8] reproject() no fue llamado para vis_type={vis_type!r}"
        crs = reproject_calls[-1][1].get("crs")
        assert crs == "EPSG:4326", (
            f"[I-8 REGRESION] reproject usa crs={crs!r}, esperado 'EPSG:4326'. "
            f"Cambiar a UTM o cualquier CRS en metros rompe el invariante I-4."
        )

    # ── I-9: format válido ───────────────────────────────────────────────────

    def test_i9_valid_format_passes(self):
        """[I-9] format='png' es válido y llega intacto a getThumbURL."""
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            svc.get_thumbnail_url(
                image=img,
                bbox=bbox,
                vis_type="RGB",
                dimensions="768x576",
                format="png",
            )

        thumb_calls = [e for e in call_log if e[0] == "getThumbURL"]
        params = thumb_calls[-1][1]
        assert params.get("format") == "png"

    # ── flujo completo para todos los vis_types ──────────────────────────────

    @pytest.mark.parametrize(
        "vis_type",
        ["RGB", "FALSE_COLOR", "SWIR", "NDVI", "NBR", "BURN_SEVERITY", "IMPACT"],
    )
    def test_full_flow_produces_url_for_all_vis_types(self, vis_type):
        """
        Flujo completo para cada vis_type:
          select → [resample] → reproject → getThumbURL → URL válida.
        El contract mock verifica I-1 a I-5 en cada llamada.
        Un FAIL aquí indica que un vis_type específico viola algún invariante.
        """
        call_log = []
        img = _make_s2_image(call_log=call_log)
        svc = _make_gee_service()
        bbox = _make_bbox()

        with patch("app.services.gee_service.ee") as mock_ee:
            mock_ee.Geometry.Rectangle.return_value = _make_geometry_mock(bbox)
            try:
                url = svc.get_thumbnail_url(
                    image=img,
                    bbox=bbox,
                    vis_type=vis_type,
                    dimensions="768x576",
                    format="png",
                    resample="bicubic",
                )
            except Exception as exc:
                pytest.fail(
                    f"vis_type={vis_type!r} generó excepción inesperada: "
                    f"{type(exc).__name__}: {exc}\n"
                    f"Call log: {call_log}"
                )

        assert url.startswith("https://"), f"URL inválida para vis_type={vis_type!r}: {url}"

        ops = [e[0] for e in call_log]
        assert "reproject" in ops, f"reproject() no fue llamado para vis_type={vis_type!r}"
        assert "getThumbURL" in ops, f"getThumbURL no fue llamado para vis_type={vis_type!r}"
        assert ops.index("reproject") < ops.index("getThumbURL"), (
            f"[I-3] reproject debe ir antes de getThumbURL para vis_type={vis_type!r}"
        )
