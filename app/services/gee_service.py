"""
Servicio para interactuar con Google Earth Engine.

Funcionalidades:
    - Buscar imágenes Sentinel-2 sin nubes
    - Descargar subsets de imágenes (RGB, NIR)
    - Calcular NDVI pre/post incendio
    - Exportar a Cloud Storage o R2
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import ee
import requests
from app.core.config import settings

logger = logging.getLogger(__name__)


class GEEService:
    """Servicio de Google Earth Engine"""
    
    def __init__(self):
        self._initialize_ee()
    
    def _initialize_ee(self):
        """Inicializa conexión con Earth Engine"""
        try:
            # Autenticar con service account
            credentials = ee.ServiceAccountCredentials(
                email=settings.GEE_SERVICE_ACCOUNT_EMAIL,
                key_file=str(settings.gee_credentials_path)
            )
            
            ee.Initialize(
                credentials,
                project=settings.GEE_PROJECT_ID
            )
            
            logger.info(f"✅ Google Earth Engine inicializado (Proyecto: {settings.GEE_PROJECT_ID})")
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar GEE: {e}")
            raise
    
    def search_sentinel2_images(
        self,
        bbox: Tuple[float, float, float, float],  # (min_lon, min_lat, max_lon, max_lat)
        start_date: datetime,
        end_date: datetime,
        max_cloud_cover: int = 20
    ) -> ee.ImageCollection:
        """
        Busca imágenes Sentinel-2 L2A (corrección atmosférica).
        
        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_date: Fecha inicio
            end_date: Fecha fin
            max_cloud_cover: % máximo de nubes (0-100)
        
        Returns:
            ImageCollection de Sentinel-2
        """
        # Crear geometría del área de interés
        aoi = ee.Geometry.Rectangle(list(bbox))
        
        # Filtrar colección Sentinel-2 L2A
        collection = (
            ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')  # Surface Reflectance (L2A)
            .filterBounds(aoi)
            .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud_cover))
            .sort('CLOUDY_PIXEL_PERCENTAGE')  # Ordenar por menor nubosidad
        )
        
        count = collection.size().getInfo()
        logger.info(f"Imágenes encontradas: {count} (nubes < {max_cloud_cover}%)")
        
        return collection
    
    def get_best_image(
        self,
        bbox: Tuple[float, float, float, float],
        target_date: datetime,
        search_window_days: int = 30,
        max_cloud_cover: int = 20
    ) -> Optional[ee.Image]:
        """
        Obtiene la mejor imagen (menos nubes) cercana a una fecha objetivo.
        
        Args:
            bbox: Área de interés
            target_date: Fecha objetivo
            search_window_days: Ventana de búsqueda en días
            max_cloud_cover: % máximo de nubes
        
        Returns:
            ee.Image o None si no hay imágenes
        """
        start_date = target_date - timedelta(days=search_window_days // 2)
        end_date = target_date + timedelta(days=search_window_days // 2)
        
        collection = self.search_sentinel2_images(bbox, start_date, end_date, max_cloud_cover)
        
        # Obtener primera imagen (ya está ordenada por menor nubosidad)
        if collection.size().getInfo() > 0:
            image = collection.first()
            
            # Log metadata
            image_info = image.getInfo()
            image_id = image_info['id']
            cloud_pct = image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
            
            logger.info(f"Mejor imagen: {image_id} (nubes: {cloud_pct:.1f}%)")
            
            return image
        else:
            logger.warning(f"No se encontraron imágenes sin nubes para {target_date}")
            return None
    
    def calculate_ndvi(self, image: ee.Image) -> ee.Image:
        """
        Calcula NDVI (Normalized Difference Vegetation Index).
        
        NDVI = (NIR - RED) / (NIR + RED)
        
        Sentinel-2 L2A bands:
            - B4: Red (665 nm)
            - B8: NIR (842 nm)
        """
        nir = image.select('B8')
        red = image.select('B4')
        
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        
        return ndvi
    
    def get_rgb_visualization(self, image: ee.Image) -> ee.Image:
        """
        Prepara imagen RGB para visualización.
        
        Sentinel-2 L2A RGB bands:
            - B4: Red
            - B3: Green
            - B2: Blue
        """
        rgb = image.select(['B4', 'B3', 'B2'])
        
        # Normalizar valores (0-3000 a 0-255)
        rgb_vis = rgb.divide(3000).multiply(255).clamp(0, 255).uint8()
        
        return rgb_vis
    
    def export_to_url(
        self,
        image: ee.Image,
        bbox: Tuple[float, float, float, float],
        scale: int = 10,  # Resolución en metros
        format: str = 'GEO_TIFF'
    ) -> str:
        """
        Genera URL de descarga para una imagen.
        
        Args:
            image: Imagen de Earth Engine
            bbox: Área de interés
            scale: Resolución espacial (10m para Sentinel-2)
            format: GEO_TIFF o PNG
        
        Returns:
            URL de descarga
        """
        aoi = ee.Geometry.Rectangle(list(bbox))
        
        # Generar URL de descarga
        url = image.getDownloadURL({
            'region': aoi,
            'scale': scale,
            'format': format,
            'crs': 'EPSG:4326'
        })
        
        logger.info(f"URL de descarga generada: {url[:100]}...")
        
        return url
    
    def download_image_to_file(
        self,
        image: ee.Image,
        bbox: Tuple[float, float, float, float],
        output_path: Path,
        scale: int = 10
    ) -> Path:
        """
        Descarga imagen a archivo local.
        
        Args:
            image: Imagen de Earth Engine
            bbox: Área de interés
            output_path: Ruta donde guardar la imagen
            scale: Resolución
        
        Returns:
            Path del archivo descargado
        """
        url = self.export_to_url(image, bbox, scale)
        
        logger.info(f"Descargando imagen a: {output_path}")
        
        # Descargar con requests
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Guardar archivo
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Descargado: {output_path} ({file_size_mb:.2f} MB)")
        
        return output_path
    
    def get_fire_analysis(
        self,
        fire_lat: float,
        fire_lon: float,
        fire_date: datetime,
        buffer_meters: int = 5000
    ) -> Dict:
        """
        Análisis completo de un incendio:
            - Imagen pre-fuego
            - Imagen post-fuego
            - NDVI antes/después
            - Cambio en vegetación
        
        Args:
            fire_lat: Latitud del incendio
            fire_lon: Longitud del incendio
            fire_date: Fecha del incendio
            buffer_meters: Radio de análisis en metros
        
        Returns:
            Dict con URLs y estadísticas
        """
        # Crear buffer alrededor del punto
        point = ee.Geometry.Point([fire_lon, fire_lat])
        aoi = point.buffer(buffer_meters).bounds()
        bbox_coords = aoi.coordinates().getInfo()[0]
        
        # Extraer min/max lat/lon
        lons = [coord[0] for coord in bbox_coords]
        lats = [coord[1] for coord in bbox_coords]
        bbox = (min(lons), min(lats), max(lons), max(lats))
        
        # Buscar imagen PRE-fuego (30 días antes)
        pre_fire_date = fire_date - timedelta(days=30)
        pre_fire_image = self.get_best_image(
            bbox,
            pre_fire_date,
            search_window_days=60,
            max_cloud_cover=20
        )
        
        # Buscar imagen POST-fuego (7 días después)
        post_fire_date = fire_date + timedelta(days=7)
        post_fire_image = self.get_best_image(
            bbox,
            post_fire_date,
            search_window_days=30,
            max_cloud_cover=30  # Más permisivo post-fuego
        )
        
        result = {
            'fire_location': {'lat': fire_lat, 'lon': fire_lon},
            'fire_date': fire_date.isoformat(),
            'analysis_area_km2': (buffer_meters / 1000) ** 2 * 3.14159,
            'pre_fire': None,
            'post_fire': None,
            'ndvi_change': None
        }
        
        if pre_fire_image:
            # RGB
            pre_rgb = self.get_rgb_visualization(pre_fire_image)
            result['pre_fire'] = {
                'image_id': pre_fire_image.getInfo()['id'],
                'date': pre_fire_image.date().format('YYYY-MM-dd').getInfo(),
                'cloud_cover': pre_fire_image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo(),
                'rgb_url': self.export_to_url(pre_rgb, bbox, scale=10, format='PNG')
            }
            
            # NDVI
            pre_ndvi = self.calculate_ndvi(pre_fire_image)
            ndvi_stats_pre = pre_ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).getInfo()
            
            result['pre_fire']['ndvi_mean'] = ndvi_stats_pre.get('NDVI')
        
        if post_fire_image:
            # RGB
            post_rgb = self.get_rgb_visualization(post_fire_image)
            result['post_fire'] = {
                'image_id': post_fire_image.getInfo()['id'],
                'date': post_fire_image.date().format('YYYY-MM-dd').getInfo(),
                'cloud_cover': post_fire_image.get('CLOUDY_PIXEL_PERCENTAGE').getInfo(),
                'rgb_url': self.export_to_url(post_rgb, bbox, scale=10, format='PNG')
            }
            
            # NDVI
            post_ndvi = self.calculate_ndvi(post_fire_image)
            ndvi_stats_post = post_ndvi.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=10
            ).getInfo()
            
            result['post_fire']['ndvi_mean'] = ndvi_stats_post.get('NDVI')
        
        # Calcular cambio en NDVI
        if result['pre_fire'] and result['post_fire']:
            ndvi_change = result['post_fire']['ndvi_mean'] - result['pre_fire']['ndvi_mean']
            result['ndvi_change'] = {
                'absolute': ndvi_change,
                'percentage': (ndvi_change / result['pre_fire']['ndvi_mean']) * 100 if result['pre_fire']['ndvi_mean'] else None
            }
        
        return result