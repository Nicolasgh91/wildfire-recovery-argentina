"""
Detector de construcciones mediante análisis de cambios en NDVI y NDBI
Identifica posibles construcciones nuevas en áreas afectadas por incendios
"""
import ee
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from image_service.config import settings


class ConstruccionesDetector:
    """Detector de cambios que sugieren construcciones"""
    
    def __init__(self):
        """Inicializa el detector"""
        self.resolucion = settings.resolucion_metros
        self.max_nubosidad = settings.max_nubosidad
        self.umbral_cambio = settings.umbral_cambio_construccion
    
    def detectar_cambios(
        self,
        latitud: float,
        longitud: float,
        fecha_antes: datetime,
        fecha_despues: datetime,
        radio_metros: float = None
    ) -> Dict:
        """
        Detecta cambios entre dos fechas que sugieren construcción
        
        Estrategia:
        - Compara NDVI (debe disminuir si construyeron)
        - Calcula NDBI (Normalized Difference Built-up Index)
        - Analiza cambios en reflectancia
        
        Args:
            latitud: Latitud del centro
            longitud: Longitud del centro
            fecha_antes: Fecha de referencia (antes)
            fecha_despues: Fecha a comparar (después)
            radio_metros: Radio del área
        
        Returns:
            Dict con análisis de cambios
        """
        if radio_metros is None:
            radio_metros = settings.radio_buffer_metros
        
        # Crear área de interés
        punto = ee.Geometry.Point([longitud, latitud])
        area = punto.buffer(radio_metros)
        
        # Obtener imágenes para ambas fechas
        imagen_antes = self._obtener_imagen(area, fecha_antes)
        imagen_despues = self._obtener_imagen(area, fecha_despues)
        
        if imagen_antes is None or imagen_despues is None:
            return {
                'construcciones_detectadas': False,
                'confianza': 0.0,
                'razon': 'Imágenes no disponibles para comparación',
                'imagen_antes_disponible': imagen_antes is not None,
                'imagen_despues_disponible': imagen_despues is not None
            }
        
        # Calcular índices para ambas fechas
        ndvi_antes = self._calcular_ndvi(imagen_antes)
        ndvi_despues = self._calcular_ndvi(imagen_despues)
        
        ndbi_antes = self._calcular_ndbi(imagen_antes)
        ndbi_despues = self._calcular_ndbi(imagen_despues)
        
        # Calcular estadísticas del área
        stats_antes = self._obtener_stats(ndvi_antes, ndbi_antes, area)
        stats_despues = self._obtener_stats(ndvi_despues, ndbi_despues, area)
        
        # Analizar cambios
        cambio_ndvi = stats_despues['ndvi_mean'] - stats_antes['ndvi_mean']
        cambio_ndbi = stats_despues['ndbi_mean'] - stats_antes['ndbi_mean']
        
        # Lógica de detección:
        # 1. NDVI disminuyó significativamente (vegetación → construcción)
        # 2. NDBI aumentó (más superficie construida)
        construccion_detectada = (
            cambio_ndvi < -self.umbral_cambio and  # NDVI bajó
            cambio_ndbi > 0.05  # NDBI subió
        )
        
        # Calcular confianza (0-1)
        confianza = self._calcular_confianza(
            cambio_ndvi,
            cambio_ndbi,
            stats_antes,
            stats_despues
        )
        
        return {
            'construcciones_detectadas': construccion_detectada,
            'confianza': round(confianza, 3),
            'cambio_ndvi': round(cambio_ndvi, 4),
            'cambio_ndbi': round(cambio_ndbi, 4),
            'ndvi_antes': round(stats_antes['ndvi_mean'], 4),
            'ndvi_despues': round(stats_despues['ndvi_mean'], 4),
            'ndbi_antes': round(stats_antes['ndbi_mean'], 4),
            'ndbi_despues': round(stats_despues['ndbi_mean'], 4),
            'interpretacion': self._interpretar_cambio(cambio_ndvi, cambio_ndbi)
        }
    
    def _obtener_imagen(
        self,
        area: ee.Geometry,
        fecha: datetime
    ) -> Optional[ee.Image]:
        """
        Obtiene la mejor imagen Sentinel-2 para una fecha
        
        Args:
            area: Geometría del área
            fecha: Fecha objetivo
        
        Returns:
            Imagen de Earth Engine o None
        """
        fecha_inicio = fecha - timedelta(days=settings.dias_ventana_imagen)
        fecha_fin = fecha + timedelta(days=settings.dias_ventana_imagen)
        
        coleccion = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')) \
            .filterBounds(area) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', self.max_nubosidad))
        
        count = coleccion.size().getInfo()
        if count == 0:
            return None
        
        return coleccion.sort('system:time_start', False).first()
    
    def _calcular_ndvi(self, imagen: ee.Image) -> ee.Image:
        """Calcula NDVI"""
        return imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
    
    def _calcular_ndbi(self, imagen: ee.Image) -> ee.Image:
        """
        Calcula NDBI (Normalized Difference Built-up Index)
        NDBI = (SWIR - NIR) / (SWIR + NIR)
        
        Valores altos indican áreas construidas
        Sentinel-2: B11 = SWIR (1610nm), B8 = NIR (842nm)
        """
        return imagen.normalizedDifference(['B11', 'B8']).rename('NDBI')
    
    def _obtener_stats(
        self,
        ndvi: ee.Image,
        ndbi: ee.Image,
        area: ee.Geometry
    ) -> Dict:
        """Obtiene estadísticas de los índices"""
        combinado = ndvi.addBands(ndbi)
        
        stats = combinado.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
            scale=self.resolucion,
            maxPixels=1e9
        ).getInfo()
        
        return {
            'ndvi_mean': stats.get('NDVI', 0),
            'ndbi_mean': stats.get('NDBI', 0)
        }
    
    def _calcular_confianza(
        self,
        cambio_ndvi: float,
        cambio_ndbi: float,
        stats_antes: Dict,
        stats_despues: Dict
    ) -> float:
        """
        Calcula nivel de confianza de la detección (0-1)
        
        Mayor confianza si:
        - Cambio de NDVI es muy negativo (vegetación desapareció)
        - Cambio de NDBI es muy positivo (construcción apareció)
        - Valores finales de NDBI son altos
        """
        # Factor 1: Magnitud del cambio en NDVI (más negativo = más confianza)
        factor_ndvi = min(1.0, abs(cambio_ndvi) / 0.5)
        
        # Factor 2: Magnitud del cambio en NDBI (más positivo = más confianza)
        factor_ndbi = min(1.0, cambio_ndbi / 0.3)
        
        # Factor 3: Valor final de NDBI (alto = construcción)
        factor_ndbi_final = min(1.0, (stats_despues['ndbi_mean'] + 0.2) / 0.4)
        
        # Combinar factores (promedio ponderado)
        confianza = (
            factor_ndvi * 0.4 +
            factor_ndbi * 0.3 +
            factor_ndbi_final * 0.3
        )
        
        return max(0.0, min(1.0, confianza))
    
    def _interpretar_cambio(self, cambio_ndvi: float, cambio_ndbi: float) -> str:
        """Interpreta los cambios detectados"""
        if cambio_ndvi < -self.umbral_cambio and cambio_ndbi > 0.05:
            return "Posible nueva construcción detectada"
        elif cambio_ndvi < -self.umbral_cambio:
            return "Pérdida de vegetación sin construcción evidente"
        elif cambio_ndbi > 0.05:
            return "Aumento leve en superficie construida"
        elif cambio_ndvi > 0.1:
            return "Recuperación de vegetación (sin construcción)"
        else:
            return "Sin cambios significativos"


if __name__ == '__main__':
    print("=== Probando Detector de Construcciones ===\n")
    
    # Inicializar Earth Engine
    import json
    
    credentials_path = settings.gee_private_key_path
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
    
    service_account = credentials_data['client_email']
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
    
    # Crear detector
    detector = ConstruccionesDetector()
    
    # Probar comparando 2 fechas diferentes en Villa Carlos Paz
    print("Comparando área en Villa Carlos Paz:")
    print("Fecha ANTES: 2023-06-15 (fecha del incendio)")
    print("Fecha DESPUÉS: 2024-06-15 (1 año después)\n")
    
    resultado = detector.detectar_cambios(
        latitud=-31.4135,
        longitud=-64.4955,
        fecha_antes=datetime(2023, 6, 15),
        fecha_despues=datetime(2024, 6, 15),
        radio_metros=500
    )
    
    print("Resultados:")
    for key, value in resultado.items():
        print(f"  {key}: {value}")