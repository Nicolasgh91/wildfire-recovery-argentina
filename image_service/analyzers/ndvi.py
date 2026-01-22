"""
Analizador de NDVI (Normalized Difference Vegetation Index)
Calcula índices de vegetación a partir de imágenes Sentinel-2
"""
import ee
from datetime import datetime, timedelta
from typing import Dict, Optional
from image_service.config import settings


class NDVIAnalyzer:
    """Analizador de índice de vegetación (NDVI)"""
    
    def __init__(self):
        """Inicializa el analizador"""
        self.resolucion = settings.resolucion_metros
        self.max_nubosidad = settings.max_nubosidad
        self.dias_ventana = settings.dias_ventana_imagen
    
    def calcular_ndvi_mes(
        self,
        latitud: float,
        longitud: float,
        fecha_objetivo: datetime,
        radio_metros: float = None
    ) -> Optional[Dict]:
        """
        Calcula NDVI para un área y fecha específica
        
        Args:
            latitud: Latitud del centro
            longitud: Longitud del centro
            fecha_objetivo: Fecha objetivo para el análisis
            radio_metros: Radio del área (default: config)
        
        Returns:
            Dict con estadísticas de NDVI o None si no hay imágenes
        """
        if radio_metros is None:
            radio_metros = settings.radio_buffer_metros
        
        # Crear área de interés
        punto = ee.Geometry.Point([longitud, latitud])
        area = punto.buffer(radio_metros)
        
        # Ventana de búsqueda: ±dias_ventana desde fecha_objetivo
        fecha_inicio = fecha_objetivo - timedelta(days=self.dias_ventana)
        fecha_fin = fecha_objetivo + timedelta(days=self.dias_ventana)
        
        # Buscar imágenes Sentinel-2
        coleccion = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate(fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d')) \
            .filterBounds(area) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', self.max_nubosidad))
        
        # Verificar si hay imágenes
        count = coleccion.size().getInfo()
        if count == 0:
            return None
        
        # Tomar la imagen más cercana a la fecha objetivo
        # Ordenar por proximidad a la fecha
        imagen = coleccion.sort('system:time_start', False).first()
        
        # Calcular NDVI: (NIR - Red) / (NIR + Red)
        # Sentinel-2: B8 = NIR (842nm), B4 = Red (665nm)
        ndvi = imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Calcular estadísticas sobre el área
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.minMax(), '', True
            ).combine(
                ee.Reducer.stdDev(), '', True
            ),
            geometry=area,
            scale=self.resolucion,
            maxPixels=1e9
        ).getInfo()
        
        # Metadata de la imagen
        metadata = imagen.getInfo()
        fecha_imagen = datetime.fromtimestamp(
            metadata['properties']['system:time_start'] / 1000
        )
        
        # Clasificar calidad de la imagen basado en nubosidad
        nubosidad = metadata['properties'].get('CLOUDY_PIXEL_PERCENTAGE', 100)
        calidad = self._clasificar_calidad(nubosidad)
        
        return {
            'fecha_objetivo': fecha_objetivo.date().isoformat(),
            'fecha_imagen': fecha_imagen.date().isoformat(),
            'ndvi_promedio': round(stats.get('NDVI_mean', 0), 4),
            'ndvi_min': round(stats.get('NDVI_min', 0), 4),
            'ndvi_max': round(stats.get('NDVI_max', 0), 4),
            'ndvi_desviacion': round(stats.get('NDVI_stdDev', 0), 4),
            'nubosidad_porcentaje': round(nubosidad, 2),
            'calidad_imagen': calidad,
            'satelite': 'Sentinel-2',
            'resolucion_metros': self.resolucion
        }
    
    def _clasificar_calidad(self, nubosidad: float) -> str:
        """
        Clasifica calidad de imagen basado en nubosidad
        
        Args:
            nubosidad: Porcentaje de nubes (0-100)
        
        Returns:
            'excelente' | 'buena' | 'regular' | 'mala'
        """
        if nubosidad <= 5:
            return 'excelente'
        elif nubosidad <= 15:
            return 'buena'
        elif nubosidad <= 30:
            return 'regular'
        else:
            return 'mala'
    
    def calcular_porcentaje_recuperacion(
        self,
        ndvi_actual: float,
        ndvi_referencia: float = None
    ) -> float:
        """
        Calcula el porcentaje de recuperación de vegetación
        
        Args:
            ndvi_actual: NDVI actual
            ndvi_referencia: NDVI antes del incendio (si disponible)
        
        Returns:
            Porcentaje de recuperación (0-100+)
        """
        # Si no hay referencia, usar valores típicos de vegetación saludable
        if ndvi_referencia is None:
            ndvi_referencia = settings.ndvi_vegetacion_densa
        
        # NDVI post-incendio típico: 0.1 (suelo desnudo/quemado)
        ndvi_minimo = 0.1
        
        # Calcular recuperación normalizada
        if ndvi_referencia <= ndvi_minimo:
            return 0.0
        
        recuperacion = ((ndvi_actual - ndvi_minimo) / (ndvi_referencia - ndvi_minimo)) * 100
        
        # Limitar a rango 0-150% (puede superar 100% si crece más que antes)
        return round(max(0, min(150, recuperacion)), 2)
    
    def interpretar_ndvi(self, ndvi: float) -> str:
        """
        Interpreta el valor de NDVI en términos comprensibles
        
        Args:
            ndvi: Valor de NDVI (-1 a 1)
        
        Returns:
            Descripción del estado de vegetación
        """
        if ndvi < 0:
            return "Agua o nieve"
        elif ndvi < 0.1:
            return "Suelo desnudo o quemado"
        elif ndvi < settings.ndvi_vegetacion_moderada:
            return "Vegetación escasa"
        elif ndvi < settings.ndvi_vegetacion_densa:
            return "Vegetación moderada"
        else:
            return "Vegetación densa/saludable"


if __name__ == '__main__':
    print("=== Probando Analizador de NDVI ===\n")
    
    # Inicializar Earth Engine
    import json
    from pathlib import Path
    
    credentials_path = settings.gee_private_key_path
    with open(credentials_path, 'r') as f:
        credentials_data = json.load(f)
    
    service_account = credentials_data['client_email']
    credentials = ee.ServiceAccountCredentials(service_account, credentials_path)
    ee.Initialize(credentials)
    
    # Crear analizador
    analyzer = NDVIAnalyzer()
    
    # Probar con el incendio de Córdoba creado antes
    print("Calculando NDVI para incendio en Villa Carlos Paz...")
    print("Coordenadas: -31.4135, -64.4955")
    print("Fecha: 3 meses después del incendio (2023-09-15)\n")
    
    resultado = analyzer.calcular_ndvi_mes(
        latitud=-31.4135,
        longitud=-64.4955,
        fecha_objetivo=datetime(2023, 9, 15),
        radio_metros=500
    )
    
    if resultado:
        print("Resultados:")
        for key, value in resultado.items():
            print(f"  {key}: {value}")
        
        print(f"\nInterpretación: {analyzer.interpretar_ndvi(resultado['ndvi_promedio'])}")
        print(f"Recuperación estimada: {analyzer.calcular_porcentaje_recuperacion(resultado['ndvi_promedio'])}%")
    else:
        print("No se encontraron imágenes para esa fecha/área")