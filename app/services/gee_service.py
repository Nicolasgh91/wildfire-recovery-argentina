"""
Google Earth Engine Service para ForestGuard.

Este módulo proporciona la capa base de acceso a Google Earth Engine (GEE)
para obtener imágenes Sentinel-2, calcular índices de vegetación (NDVI),
y generar visualizaciones para los casos de uso UC-06, UC-08, UC-11/12.

Arquitectura:
    GEE Service (Base) → VAE Service (Análisis) → ERS Service (Reportes)

Límites Free Tier:
    - 50,000 requests/día
    - 10 operaciones concurrentes
    - Rate limit implementado: 1 req/segundo

Autor: ForestGuard Dev Team
Versión: 1.0.0
Última actualización: 2025-01-29
"""


from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from time import sleep
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

try:
    import ee

    _EE_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    ee = None
    _EE_IMPORT_ERROR = exc

# Rate limiting
try:
    from ratelimit import limits, sleep_and_retry

    RATELIMIT_AVAILABLE = True
except ImportError:
    RATELIMIT_AVAILABLE = False

    # Fallback decorator que no hace nada
    def sleep_and_retry(func):
        return func

    def limits(calls, period):
        def decorator(func):
            return func

        return decorator


# Circuit Breaker (ROB-005)
try:
    from app.core.circuit_breaker import CircuitBreakerError, gee_circuit

    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False
    gee_circuit = None

    class CircuitBreakerError(Exception):
        pass


# Configuración de logging
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================================================

# Colecciones de GEE
SENTINEL2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"  # Surface Reflectance L2A
SENTINEL2_CLOUD_PROB = "COPERNICUS/S2_CLOUD_PROBABILITY"

# Bandas Sentinel-2
BANDS = {
    "RGB": ["B4", "B3", "B2"],  # True Color (10m)
    "NIR": ["B8"],  # Near Infrared (10m)
    "SWIR": ["B11", "B12"],  # Short-wave Infrared (20m)
    "RED_EDGE": ["B5", "B6", "B7"],  # Red Edge (20m)
    "ALL_10M": ["B2", "B3", "B4", "B8"],  # Todas las bandas 10m
}

# Parámetros de visualización
VIS_PARAMS = {
    "RGB": {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.2},
    "FALSE_COLOR": {"bands": ["B8", "B4", "B3"], "min": 0, "max": 4000},
    "SWIR": {
        "bands": ["B12", "B11", "B4"],
        "min": [0, 0, 0],
        "max": [5000, 5000, 5000],
        "gamma": [1.0, 1.0, 1.0],
    },
    "NDVI": {
        "min": -0.2,
        "max": 0.8,
        "palette": ["brown", "yellow", "green", "darkgreen"],
    },
    "BURN_SEVERITY": {
        "min": -0.5,
        "max": 0.5,
        "palette": ["green", "yellow", "orange", "red"],
    },
    "IMPACT": {"bands": ["B12", "B8A", "B4"], "min": 0, "max": 3000, "gamma": 1.1},
    "REALITY": {"bands": ["B4", "B3", "B2"], "min": 0, "max": 3000, "gamma": 1.2},
    "NBR": {
        "min": -0.5,
        "max": 0.5,
        "palette": ["#00FF00", "#FFFF00", "#FF7F00", "#FF0000", "#000000"],
    },
    "DNBR": {
        "min": -0.5,
        "max": 0.5,
        "palette": ["#00FF00", "#FFFF00", "#FF7F00", "#FF0000", "#000000"],
    },
}

# Rate limits (respetando cuota GEE)
CALLS_PER_SECOND = 1
CALLS_PER_DAY = 50000


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ImageMetadata:
    """Metadata de una imagen Sentinel-2."""

    image_id: str
    acquisition_date: date
    cloud_cover_percent: float
    satellite: str
    tile_id: str
    sun_elevation: float
    processing_level: str = "L2A"


@dataclass
class NDVIResult:
    """Resultado del cálculo de NDVI."""

    mean: float
    min: float
    max: float
    std_dev: float
    valid_pixels_percent: float
    acquisition_date: date


@dataclass
class ImageResult:
    """Resultado de obtener una imagen."""

    thumbnail_url: str
    download_url: Optional[str]
    metadata: ImageMetadata
    bbox: Dict[str, float]
    scale_meters: int


# =============================================================================
# EXCEPCIONES PERSONALIZADAS
# =============================================================================


class GEEError(Exception):
    """Excepción base para errores de GEE."""

    pass


class GEEAuthenticationError(GEEError):
    """Error de autenticación con GEE."""

    pass


class GEEImageNotFoundError(GEEError):
    """No se encontró imagen que cumpla los criterios."""

    pass


class GEERateLimitError(GEEError):
    """Se excedió el límite de requests."""

    pass


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================


class GEEService:
    """
    Servicio de acceso a Google Earth Engine.

    Proporciona métodos para:
    - Autenticación con service account
    - Búsqueda de imágenes Sentinel-2
    - Cálculo de NDVI y otros índices
    - Generación de thumbnails y URLs de descarga

    Ejemplo de uso:
        gee = GEEService()
        gee.authenticate()

        # Buscar imágenes
        images = gee.get_sentinel_collection(
            bbox={"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4},
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            max_cloud_cover=20
        )

        # Obtener mejor imagen
        best = gee.get_best_image(images, target_date=date(2023, 6, 15))

        # Calcular NDVI
        ndvi = gee.calculate_ndvi(best, bbox)

    Attributes:
        _initialized: bool indicando si GEE está inicializado
        _project_id: ID del proyecto de Google Cloud
        _request_count: Contador de requests para monitoreo
    """

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern para reutilizar autenticación."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        service_account_json: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Inicializa el servicio GEE.

        Args:
            service_account_json: Ruta al archivo JSON de service account.
                                  Si no se proporciona, busca en variable de entorno.
            project_id: ID del proyecto GCP. Si no se proporciona, se obtiene del JSON.
        """
        if self._initialized:
            return

        self._service_account_json = service_account_json
        self._project_id = project_id or os.environ.get("GEE_PROJECT_ID")
        self._request_count = 0
        self._last_request_time = None

    def _ensure_ee_available(self) -> None:
        if ee is None:
            raise GEEAuthenticationError(
                "earthengine-api no esta instalado. Instalalo con `pip install earthengine-api`."
            ) from _EE_IMPORT_ERROR

    def authenticate(self) -> bool:
        """
        Autentica con Google Earth Engine usando service account.

        Busca credenciales en el siguiente orden:
        1. Parámetro service_account_json del constructor
        2. Variables GEE_SERVICE_ACCOUNT_EMAIL + GEE_PRIVATE_KEY_PATH
        3. Variable de entorno GEE_SERVICE_ACCOUNT_JSON (path o JSON string)
        4. Autenticación interactiva (solo para desarrollo)

        Returns:
            bool: True si la autenticación fue exitosa

        Raises:
            GEEAuthenticationError: Si no se puede autenticar
        """
        self._ensure_ee_available()
        if self._initialized:
            logger.debug("GEE ya está autenticado")
            return True

        import json
        import os

        try:
            # Opción 1: JSON path del constructor
            if self._service_account_json and Path(self._service_account_json).exists():
                credentials = ee.ServiceAccountCredentials(
                    None, self._service_account_json  # Se obtiene del JSON
                )
                ee.Initialize(credentials, project=self._project_id)
                logger.info(
                    f"GEE autenticado con service account file: {self._service_account_json}"
                )
                self._initialized = True
                return True

            # Opción 2: Variables de entorno (email + private key path)
            gee_email = os.environ.get("GEE_SERVICE_ACCOUNT_EMAIL")
            gee_key_path = os.environ.get("GEE_PRIVATE_KEY_PATH")
            if gee_email and gee_key_path:
                key_path = Path(gee_key_path)
                if not key_path.exists():
                    raise GEEAuthenticationError(
                        "GEE_PRIVATE_KEY_PATH no apunta a un archivo válido"
                    )
                credentials = ee.ServiceAccountCredentials(gee_email, str(key_path))
                ee.Initialize(credentials, project=self._project_id)
                logger.info(
                    "GEE autenticado con credenciales de service account + key path"
                )
                self._initialized = True
                return True

            # Opción 3: Variables de entorno
            # Buscar en varias variables comunes
            gee_env = (
                os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
                or os.environ.get("GEE_CREDENTIALS_PATH")
                or os.environ.get("GEE_CREDENTIALS")
                or os.environ.get("GEE_PRIVATE_KEY_PATH")
            )
            if gee_env:
                # Puede ser path o JSON string
                if Path(gee_env).exists():
                    credentials = ee.ServiceAccountCredentials(None, gee_env)
                    ee.Initialize(credentials, project=self._project_id)
                else:
                    # Intentar como JSON string
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    ) as f:
                        f.write(gee_env)
                        temp_path = f.name
                    credentials = ee.ServiceAccountCredentials(None, temp_path)
                    ee.Initialize(credentials, project=self._project_id)
                    Path(temp_path).unlink()  # Limpiar

                logger.info("GEE autenticado con variable de entorno")
                self._initialized = True
                return True

            # Opción 4: Autenticación por defecto (para desarrollo)
            ee.Initialize()
            logger.warning("GEE autenticado con credenciales por defecto (solo dev)")
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Error autenticando GEE: {e}")
            raise GEEAuthenticationError(f"No se pudo autenticar con GEE: {e}")

    def _ensure_authenticated(self) -> None:
        """Verifica que GEE esté autenticado, si no, intenta autenticar."""
        if not self._initialized:
            self.authenticate()

    @sleep_and_retry
    @limits(calls=CALLS_PER_SECOND, period=1)
    def _rate_limited_request(self, func, *args, **kwargs):
        """
        Ejecuta una función con rate limiting y circuit breaker.

        Máximo 1 request por segundo para mantenerse bajo el límite diario.
        Circuit breaker abre después de 5 fallos consecutivos (RES-001).
        """
        self._request_count += 1
        if self._request_count % 100 == 0:
            logger.info(f"GEE requests hoy: {self._request_count}")

        # ROB-005: Use circuit breaker if available
        if CIRCUIT_BREAKER_AVAILABLE and gee_circuit:
            return gee_circuit.call(func, *args, **kwargs)

        return func(*args, **kwargs)

    # =========================================================================
    # MÉTODOS DE BÚSQUEDA DE IMÁGENES
    # =========================================================================

    def get_sentinel_collection(
        self,
        bbox: Dict[str, float],
        start_date: date,
        end_date: date,
        max_cloud_cover: float = 20.0,
    ) -> ee.ImageCollection:
        """
        Obtiene colección de imágenes Sentinel-2 filtrada.

        Args:
            bbox: Bounding box con keys 'west', 'south', 'east', 'north'
            start_date: Fecha inicio de búsqueda
            end_date: Fecha fin de búsqueda
            max_cloud_cover: Máximo porcentaje de nubes (0-100)

        Returns:
            ee.ImageCollection: Colección filtrada

        Example:
            collection = gee.get_sentinel_collection(
                bbox={"west": -58.5, "south": -27.5, "east": -58.4, "north": -27.4},
                start_date=date(2023, 1, 1),
                end_date=date(2023, 12, 31),
                max_cloud_cover=20
            )
        """
        self._ensure_authenticated()

        # Crear geometría
        geometry = ee.Geometry.Rectangle(
            [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
        )

        # Formatear fechas
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # Query con rate limiting
        def _query():
            collection = (
                ee.ImageCollection(SENTINEL2_COLLECTION)
                .filterBounds(geometry)
                .filterDate(start_str, end_str)
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_cover))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )
            return collection

        return self._rate_limited_request(_query)

    def get_collection_info(
        self, collection: ee.ImageCollection
    ) -> List[ImageMetadata]:
        """
        Obtiene metadata de todas las imágenes en una colección.

        Args:
            collection: Colección de GEE

        Returns:
            Lista de ImageMetadata con información de cada imagen
        """
        self._ensure_authenticated()

        def _get_info():
            # Limitar a 100 imágenes para no sobrecargar
            info = collection.limit(100).getInfo()
            features = info.get("features", [])

            results = []
            for feat in features:
                props = feat.get("properties", {})
                results.append(
                    ImageMetadata(
                        image_id=feat.get("id", ""),
                        acquisition_date=datetime.strptime(
                            props.get("DATATAKE_IDENTIFIER", "")[:8], "%Y%m%d"
                        ).date()
                        if props.get("DATATAKE_IDENTIFIER")
                        else None,
                        cloud_cover_percent=props.get("CLOUDY_PIXEL_PERCENTAGE", 0),
                        satellite=props.get("SPACECRAFT_NAME", "Sentinel-2"),
                        tile_id=props.get("MGRS_TILE", ""),
                        sun_elevation=props.get("MEAN_SOLAR_ZENITH_ANGLE", 0),
                    )
                )
            return results

        return self._rate_limited_request(_get_info)

    def get_best_image(
        self,
        collection: ee.ImageCollection,
        target_date: Optional[date] = None,
        prefer_low_cloud: bool = True,
        max_cloud_cover: Optional[float] = 30.0,
    ) -> ee.Image:
        """
        Obtiene la mejor imagen de la colección.

        Criterios de selección:
        1. Si target_date: imagen más cercana a esa fecha con nubes < max_cloud_cover
        2. Si prefer_low_cloud: imagen con menor cobertura de nubes

        Args:
            collection: Colección de imágenes
            target_date: Fecha objetivo (opcional)
            prefer_low_cloud: Priorizar baja nubosidad
            max_cloud_cover: Máximo porcentaje de nubes cuando se usa target_date

        Returns:
            ee.Image: Mejor imagen según criterios

        Raises:
            GEEImageNotFoundError: Si no hay imágenes disponibles
        """
        self._ensure_authenticated()

        def _get_best():
            if target_date:
                # Ordenar por distancia a la fecha objetivo
                target_millis = ee.Date(target_date.strftime("%Y-%m-%d")).millis()

                def add_date_diff(image):
                    diff = (
                        ee.Number(image.date().millis()).subtract(target_millis).abs()
                    )
                    return image.set("date_diff", diff)

                sorted_collection = collection
                if max_cloud_cover is not None:
                    sorted_collection = sorted_collection.filter(
                        ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_cover)
                    )
                sorted_collection = sorted_collection.map(add_date_diff).sort(
                    "date_diff"
                )
            else:
                # Ordenar por nubosidad
                sorted_collection = collection.sort("CLOUDY_PIXEL_PERCENTAGE")

            first = sorted_collection.first()

            # Verificar que existe
            info = first.getInfo()
            if not info:
                raise GEEImageNotFoundError(
                    "No se encontraron imágenes que cumplan los criterios"
                )

            return first

        return self._rate_limited_request(_get_best)

    def apply_cloud_mask(self, image: ee.Image) -> ee.Image:
        """
        Aplica una máscara de nubes usando la banda SCL (Scene Classification).

        Remueve: no-data, saturado, sombras, nubes medias/altas, cirrus y nieve.
        """
        self._ensure_authenticated()

        def _mask():
            scl = image.select("SCL")
            mask = (
                scl.neq(0)
                .And(scl.neq(1))
                .And(scl.neq(3))
                .And(scl.neq(8))
                .And(scl.neq(9))
                .And(scl.neq(10))
                .And(scl.neq(11))
            )
            return image.updateMask(mask)

        return self._rate_limited_request(_mask)

    def get_image_by_id(self, image_id: str) -> ee.Image:
        """
        Obtiene una imagen específica por su ID.

        Args:
            image_id: ID completo de la imagen (ej: COPERNICUS/S2_SR/20230615T140051_...)

        Returns:
            ee.Image: Imagen de GEE
        """
        self._ensure_authenticated()
        return ee.Image(image_id)

    # =========================================================================
    # MÉTODOS DE CÁLCULO DE ÍNDICES
    # =========================================================================

    def calculate_ndvi(
        self, image: ee.Image, bbox: Dict[str, float], scale: int = 10
    ) -> NDVIResult:
        """
        Calcula NDVI (Normalized Difference Vegetation Index) para una imagen.

        NDVI = (NIR - RED) / (NIR + RED)
        Valores: -1 a 1 (mayor = más vegetación)

        Args:
            image: Imagen Sentinel-2
            bbox: Bounding box para calcular estadísticas
            scale: Resolución en metros (default 10m)

        Returns:
            NDVIResult con estadísticas del NDVI
        """
        self._ensure_authenticated()

        def _calc_ndvi():
            # Calcular NDVI
            nir = image.select("B8")  # NIR - 10m
            red = image.select("B4")  # RED - 10m
            ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")

            # Geometría para estadísticas
            geometry = ee.Geometry.Rectangle(
                [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
            )

            # Calcular estadísticas
            stats = ndvi.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), "", True)
                .combine(ee.Reducer.max(), "", True)
                .combine(ee.Reducer.stdDev(), "", True)
                .combine(ee.Reducer.count(), "", True),
                geometry=geometry,
                scale=scale,
                maxPixels=1e9,
            ).getInfo()

            # Obtener fecha de adquisición
            props = image.getInfo().get("properties", {})
            acq_date = None
            if props.get("system:time_start"):
                acq_date = datetime.fromtimestamp(
                    props["system:time_start"] / 1000
                ).date()

            # Calcular porcentaje de píxeles válidos
            total_pixels = stats.get("NDVI_count", 0)
            area_km2 = (
                (bbox["east"] - bbox["west"])
                * (bbox["north"] - bbox["south"])
                * 111
                * 111
            )
            expected_pixels = (area_km2 * 1e6) / (scale * scale)
            valid_percent = (
                (total_pixels / expected_pixels * 100) if expected_pixels > 0 else 0
            )

            return NDVIResult(
                mean=stats.get("NDVI_mean", 0) or 0,
                min=stats.get("NDVI_min", 0) or 0,
                max=stats.get("NDVI_max", 0) or 0,
                std_dev=stats.get("NDVI_stdDev", 0) or 0,
                valid_pixels_percent=min(valid_percent, 100),
                acquisition_date=acq_date,
            )

        return self._rate_limited_request(_calc_ndvi)

    def calculate_nbr(
        self, image: ee.Image, bbox: Dict[str, float], scale: int = 20
    ) -> Dict[str, float]:
        """
        Calcula NBR (Normalized Burn Ratio) para detectar áreas quemadas.

        NBR = (NIR - SWIR2) / (NIR + SWIR2)
        Valores bajos/negativos = área quemada

        Args:
            image: Imagen Sentinel-2
            bbox: Bounding box
            scale: Resolución (20m para SWIR)

        Returns:
            Dict con mean, min, max del NBR
        """
        self._ensure_authenticated()

        def _calc_nbr():
            nir = image.select("B8")  # NIR - 10m
            swir2 = image.select("B12")  # SWIR2 - 20m
            nbr = nir.subtract(swir2).divide(nir.add(swir2)).rename("NBR")

            geometry = ee.Geometry.Rectangle(
                [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
            )

            stats = nbr.reduceRegion(
                reducer=ee.Reducer.mean()
                .combine(ee.Reducer.min(), "", True)
                .combine(ee.Reducer.max(), "", True),
                geometry=geometry,
                scale=scale,
                maxPixels=1e9,
            ).getInfo()

            return {
                "mean": stats.get("NBR_mean", 0) or 0,
                "min": stats.get("NBR_min", 0) or 0,
                "max": stats.get("NBR_max", 0) or 0,
            }

        return self._rate_limited_request(_calc_nbr)

    def get_dnbr_thumbnail_url(
        self,
        pre_image: ee.Image,
        post_image: ee.Image,
        bbox: Dict[str, float],
        dimensions: Union[int, str] = 512,
        format: str = "png",
    ) -> str:
        """
        Genera URL de thumbnail para dNBR (pre - post).
        """
        self._ensure_authenticated()

        def _get_url():
            geometry = ee.Geometry.Rectangle(
                [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
            )
            nbr_pre = pre_image.normalizedDifference(["B8", "B12"])
            nbr_post = post_image.normalizedDifference(["B8", "B12"])
            dnbr = nbr_pre.subtract(nbr_post)
            vis_params = VIS_PARAMS.get("DNBR", {"min": -0.5, "max": 0.5}).copy()
            url = dnbr.getThumbURL(
                {
                    "region": geometry,
                    "dimensions": dimensions,
                    "format": format,
                    **vis_params,
                }
            )
            return url

        return self._rate_limited_request(_get_url)

    def download_dnbr_thumbnail(
        self,
        pre_image: ee.Image,
        post_image: ee.Image,
        bbox: Dict[str, float],
        dimensions: int = 512,
        format: str = "png",
    ) -> bytes:
        """
        Descarga thumbnail dNBR como bytes.
        """
        url = self.get_dnbr_thumbnail_url(
            pre_image,
            post_image,
            bbox,
            dimensions=dimensions,
            format=format,
        )
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content

    # =========================================================================
    # MÉTODOS DE VISUALIZACIÓN Y DESCARGA
    # =========================================================================

    def get_thumbnail_url(
        self,
        image: ee.Image,
        bbox: Dict[str, float],
        vis_type: str = "RGB",
        dimensions: Union[int, str] = 512,
        resample: Optional[str] = None,
        format: str = "png",
    ) -> str:
        """
        Genera URL de thumbnail para una imagen.

        Args:
            image: Imagen de GEE
            bbox: Bounding box
            vis_type: Tipo de visualización ('RGB', 'FALSE_COLOR', 'NDVI')
            dimensions: Tamaño máximo en píxeles
            format: Formato de salida ('png', 'jpg')

        Returns:
            str: URL del thumbnail (válida por ~2 horas)
        """
        self._ensure_authenticated()

        def _get_url():
            geometry = ee.Geometry.Rectangle(
                [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
            )

            vis_key = vis_type.upper()

            # Seleccionar visualización
            if vis_key == "NDVI":
                nir = image.select("B8")
                red = image.select("B4")
                vis_image = nir.subtract(red).divide(nir.add(red))
                vis_params = VIS_PARAMS["NDVI"].copy()
            elif vis_key in ("NBR", "SCIENCE", "BURN_SEVERITY"):
                nir = image.select("B8")
                swir = image.select("B12")
                vis_image = nir.subtract(swir).divide(nir.add(swir))
                vis_params = VIS_PARAMS.get("NBR", {"min": -0.5, "max": 0.5}).copy()
            elif vis_key in VIS_PARAMS and "bands" in VIS_PARAMS[vis_key]:
                vis_image = image.select(VIS_PARAMS[vis_key]["bands"])
                vis_params = {
                    k: v for k, v in VIS_PARAMS[vis_key].items() if k != "bands"
                }
            else:
                vis_image = image.select(BANDS["RGB"])
                vis_params = {"min": 0, "max": 3000}

            if resample:
                method = resample.lower()
                if method not in {"nearest", "bilinear", "bicubic"}:
                    raise ValueError(f"Metodo de resample invalido: {resample}")
                vis_image = vis_image.resample(method)

            # Generar thumbnail
            url = vis_image.getThumbURL(
                {
                    "region": geometry,
                    "dimensions": dimensions,
                    "format": format,
                    **vis_params,
                }
            )

            return url

        return self._rate_limited_request(_get_url)

    def get_download_url(
        self,
        image: ee.Image,
        bbox: Dict[str, float],
        bands: List[str] = None,
        scale: int = 10,
        format: str = "GEO_TIFF",
    ) -> str:
        """
        Genera URL de descarga para imagen completa.

        ADVERTENCIA: Las URLs de descarga de GEE tienen límite de tamaño.
        Para áreas grandes, usar export_to_drive().

        Args:
            image: Imagen de GEE
            bbox: Bounding box
            bands: Lista de bandas (default: RGB)
            scale: Resolución en metros
            format: Formato ('GEO_TIFF', 'NPY')

        Returns:
            str: URL de descarga
        """
        self._ensure_authenticated()

        def _get_download_url():
            geometry = ee.Geometry.Rectangle(
                [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
            )

            selected_bands = bands or BANDS["RGB"]
            download_image = image.select(selected_bands)

            url = download_image.getDownloadURL(
                {
                    "region": geometry,
                    "scale": scale,
                    "format": format,
                    "crs": "EPSG:4326",
                }
            )

            return url

        return self._rate_limited_request(_get_download_url)

    def download_thumbnail(
        self,
        image: ee.Image,
        bbox: Dict[str, float],
        vis_type: str = "RGB",
        dimensions: Union[int, str] = 1024,
        resample: Optional[str] = None,
        format: str = "png",
    ) -> bytes:
        """
        Descarga thumbnail como bytes.

        Útil para guardar en object storage o incluir en PDFs.

        Args:
            image: Imagen de GEE
            bbox: Bounding box
            vis_type: Tipo de visualización
            dimensions: Tamaño en píxeles

        Returns:
            bytes: Contenido de la imagen PNG
        """
        url = self.get_thumbnail_url(
            image, bbox, vis_type, dimensions, resample, format
        )

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        return response.content

    # =========================================================================
    # MÉTODOS DE SERIES TEMPORALES (PARA UC-06, UC-11/12)
    # =========================================================================

    def get_temporal_series(
        self,
        bbox: Dict[str, float],
        start_date: date,
        end_date: date,
        interval_months: int = 1,
        max_cloud_cover: float = 30.0,
    ) -> List[Tuple[date, Optional[ee.Image]]]:
        """
        Obtiene serie temporal de imágenes para un período.

        Ideal para UC-11/12: secuencia pre-incendio + post-incendio anual.

        Args:
            bbox: Bounding box
            start_date: Fecha inicio
            end_date: Fecha fin
            interval_months: Intervalo entre imágenes (1=mensual, 12=anual)
            max_cloud_cover: Máximo porcentaje de nubes

        Returns:
            Lista de tuplas (fecha_target, imagen o None si no hay disponible)
        """
        self._ensure_authenticated()

        results = []
        current_date = start_date

        while current_date <= end_date:
            # Ventana de búsqueda: ±15 días del target
            window_start = current_date - timedelta(days=15)
            window_end = current_date + timedelta(days=15)

            try:
                collection = self.get_sentinel_collection(
                    bbox=bbox,
                    start_date=window_start,
                    end_date=window_end,
                    max_cloud_cover=max_cloud_cover,
                )

                image = self.get_best_image(collection, target_date=current_date)
                results.append((current_date, image))

            except GEEImageNotFoundError:
                logger.warning(f"No hay imagen disponible para {current_date}")
                results.append((current_date, None))

            # Avanzar al siguiente intervalo
            if interval_months == 1:
                # Siguiente mes
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, current_date.day)
                else:
                    try:
                        current_date = date(
                            current_date.year, current_date.month + 1, current_date.day
                        )
                    except ValueError:
                        # Día no existe en el mes (ej: 31 de febrero)
                        current_date = date(
                            current_date.year, current_date.month + 1, 28
                        )
            else:
                # Avanzar N meses
                new_month = current_date.month + interval_months
                new_year = current_date.year + (new_month - 1) // 12
                new_month = ((new_month - 1) % 12) + 1
                try:
                    current_date = date(new_year, new_month, current_date.day)
                except ValueError:
                    current_date = date(new_year, new_month, 28)

        return results

    def get_annual_series_for_fire(
        self,
        bbox: Dict[str, float],
        fire_date: date,
        years_after: int = 5,
        pre_fire_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Obtiene serie anual de imágenes para seguimiento post-incendio.

        Específico para UC-11/12:
        - 1 imagen pre-incendio
        - 1 imagen por año post-incendio

        Args:
            bbox: Bounding box del área quemada
            fire_date: Fecha del incendio
            years_after: Años a monitorear post-incendio
            pre_fire_days: Días antes del incendio para imagen pre-fuego

        Returns:
            Dict con:
                - pre_fire: imagen pre-incendio (o None)
                - post_fire: lista de (año, imagen) para cada año posterior
                - metadata: información adicional
        """
        self._ensure_authenticated()

        result = {
            "pre_fire": None,
            "post_fire": [],
            "metadata": {
                "fire_date": fire_date.isoformat(),
                "bbox": bbox,
                "years_monitored": years_after,
            },
        }

        # Imagen pre-incendio
        try:
            pre_start = fire_date - timedelta(days=pre_fire_days)
            pre_end = fire_date - timedelta(days=1)

            pre_collection = self.get_sentinel_collection(
                bbox=bbox, start_date=pre_start, end_date=pre_end, max_cloud_cover=25
            )
            result["pre_fire"] = self.get_best_image(pre_collection)
            logger.info(f"Imagen pre-incendio encontrada")
        except GEEImageNotFoundError:
            logger.warning(f"No hay imagen pre-incendio disponible")

        # Imágenes anuales post-incendio
        for year_offset in range(1, years_after + 1):
            target_date = date(
                fire_date.year + year_offset, fire_date.month, fire_date.day
            )

            # No buscar fechas futuras
            if target_date > date.today():
                break

            try:
                # Ventana de ±30 días
                collection = self.get_sentinel_collection(
                    bbox=bbox,
                    start_date=target_date - timedelta(days=30),
                    end_date=target_date + timedelta(days=30),
                    max_cloud_cover=30,
                )
                image = self.get_best_image(collection, target_date=target_date)
                result["post_fire"].append((target_date.year, image))
                logger.info(f"Imagen año {target_date.year} encontrada")
            except GEEImageNotFoundError:
                logger.warning(f"No hay imagen disponible para año {target_date.year}")
                result["post_fire"].append((target_date.year, None))

        return result

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def get_image_metadata(self, image: ee.Image) -> ImageMetadata:
        """Extrae metadata de una imagen."""
        self._ensure_authenticated()

        def _get_metadata():
            info = image.getInfo()
            props = info.get("properties", {})

            # Parsear fecha
            acq_date = None
            if props.get("system:time_start"):
                acq_date = datetime.fromtimestamp(
                    props["system:time_start"] / 1000
                ).date()

            return ImageMetadata(
                image_id=info.get("id", ""),
                acquisition_date=acq_date,
                cloud_cover_percent=props.get("CLOUDY_PIXEL_PERCENTAGE", 0),
                satellite=props.get("SPACECRAFT_NAME", "Sentinel-2"),
                tile_id=props.get("MGRS_TILE", ""),
                sun_elevation=90 - props.get("MEAN_SOLAR_ZENITH_ANGLE", 0),
            )

        return self._rate_limited_request(_get_metadata)

    def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado de la conexión con GEE.

        Returns:
            Dict con status y detalles
        """
        try:
            self._ensure_authenticated()

            # Test simple: obtener info de una imagen conocida
            test_image = ee.Image(
                "COPERNICUS/S2_SR_HARMONIZED/20230101T140051_20230101T140045_T20HNH"
            )
            info = test_image.getInfo()

            return {
                "status": "healthy",
                "authenticated": True,
                "requests_today": self._request_count,
                "test_image": info.get("id", "unknown") if info else "failed",
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "authenticated": self._initialized,
                "error": str(e),
            }

    def get_request_count(self) -> int:
        """Retorna el número de requests realizados en esta sesión."""
        return self._request_count

    def reset_request_count(self) -> None:
        """Resetea el contador de requests (para nuevo día)."""
        self._request_count = 0


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================


def get_gee_service() -> GEEService:
    """
    Factory function para obtener instancia de GEEService.

    Usar como dependency injection en FastAPI:
        @router.get("/imagery")
        def get_imagery(gee: GEEService = Depends(get_gee_service)):
            ...
    """
    service = GEEService()
    service.authenticate()
    return service


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    """Ejemplo de uso del servicio."""

    # Configurar logging
    logging.basicConfig(level=logging.INFO)

    # Inicializar servicio
    gee = GEEService()

    # Health check
    status = gee.health_check()
    print(f"Status: {status}")

    if status["status"] == "healthy":
        # Ejemplo: buscar imágenes para un área en Chaco
        bbox = {"west": -60.5, "south": -27.0, "east": -60.3, "north": -26.8}

        # Buscar imágenes de 2023
        collection = gee.get_sentinel_collection(
            bbox=bbox,
            start_date=date(2023, 6, 1),
            end_date=date(2023, 8, 31),
            max_cloud_cover=20,
        )

        # Obtener mejor imagen
        best_image = gee.get_best_image(collection)
        metadata = gee.get_image_metadata(best_image)
        print(f"Mejor imagen: {metadata}")

        # Calcular NDVI
        ndvi = gee.calculate_ndvi(best_image, bbox)
        print(f"NDVI: mean={ndvi.mean:.3f}, range=[{ndvi.min:.3f}, {ndvi.max:.3f}]")

        # Obtener thumbnail URL
        thumb_url = gee.get_thumbnail_url(best_image, bbox, vis_type="RGB")
        print(f"Thumbnail: {thumb_url}")
