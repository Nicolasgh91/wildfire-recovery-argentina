"""
Cliente para Google Earth Engine
Maneja autenticación y operaciones con imágenes satelitales
"""
import ee
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()


class GEEClient:
    """Cliente para interactuar con Google Earth Engine"""
    
    def __init__(self):
        """Inicializa y autentica con GEE usando Service Account"""
        self.authenticated = False
        self._authenticate()
    
    def _authenticate(self):
        """Autentica usando Service Account credentials"""
        try:
            # Leer credenciales del archivo JSON
            credentials_path = os.getenv('GEE_PRIVATE_KEY_PATH')
            
            if not credentials_path or not Path(credentials_path).exists():
                raise FileNotFoundError(
                    f"Archivo de credenciales no encontrado: {credentials_path}"
                )
            
            # Leer el archivo JSON
            with open(credentials_path, 'r') as f:
                credentials_data = json.load(f)
            
            service_account = credentials_data['client_email']
            
            # Crear credenciales desde el archivo
            credentials = ee.ServiceAccountCredentials(
                service_account, 
                credentials_path
            )
            
            # Inicializar Earth Engine
            ee.Initialize(credentials)
            
            self.authenticated = True
            print(f"✓ Autenticado con GEE: {service_account}")
            
        except Exception as e:
            print(f"✗ Error autenticando GEE: {e}")
            raise
    
    def detectar_incendios(
        self,
        provincia: str,
        fecha_inicio: str,
        fecha_fin: str,
        umbral_confianza: float = 0.8
    ) -> List[Dict]:
        """
        Detecta incendios usando MODIS/VIIRS thermal anomalies
        
        Args:
            provincia: Nombre de la provincia argentina
            fecha_inicio: Formato 'YYYY-MM-DD'
            fecha_fin: Formato 'YYYY-MM-DD'
            umbral_confianza: Nivel de confianza (0-1)
        
        Returns:
            Lista de incendios detectados con metadata
        """
        if not self.authenticated:
            raise Exception("GEE no autenticado")
        
        # Argentina boundaries (simplificado - en producción usar geometría real)
        # Para prueba, usar un punto en Buenos Aires
        argentina = ee.Geometry.Point([-58.3816, -34.6037]).buffer(50000)
        
        # MODIS Thermal Anomalies / Fire dataset
        # Usamos MODIS porque tiene datos históricos desde 2000
        fire_collection = ee.ImageCollection('MODIS/006/MOD14A1') \
            .filterDate(fecha_inicio, fecha_fin) \
            .filterBounds(argentina) \
            .select(['FireMask', 'MaxFRP'])  # Fire Radiative Power
        
        print(f"Colección filtrada: {fire_collection.size().getInfo()} imágenes")
        
        # En producción, aquí procesarías la colección completa
        # Por ahora, retornamos metadata básica
        
        return {
            'provincia': provincia,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'imagenes_disponibles': fire_collection.size().getInfo(),
            'dataset': 'MODIS/006/MOD14A1'
        }
    
    def obtener_ndvi(
        self,
        latitud: float,
        longitud: float,
        radio_metros: float,
        fecha: str
    ) -> Dict:
        """
        Calcula NDVI promedio para un área y fecha
        
        Args:
            latitud: Latitud del centro
            longitud: Longitud del centro
            radio_metros: Radio del área circular
            fecha: Fecha en formato 'YYYY-MM-DD'
        
        Returns:
            Dict con estadísticas de NDVI
        """
        if not self.authenticated:
            raise Exception("GEE no autenticado")
        
        # Área de interés
        punto = ee.Geometry.Point([longitud, latitud])
        area = punto.buffer(radio_metros)
        
        # Sentinel-2: resolución 10m, mejor para análisis de vegetación
        # Buscar imagen más cercana a la fecha (±15 días)
        fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
        fecha_inicio = (fecha_dt - timedelta(days=15)).strftime('%Y-%m-%d')
        fecha_fin = (fecha_dt + timedelta(days=15)).strftime('%Y-%m-%d')
        
        # Colección Sentinel-2 Surface Reflectance
        s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate(fecha_inicio, fecha_fin) \
            .filterBounds(area) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        
        # Verificar si hay imágenes disponibles
        count = s2_collection.size().getInfo()
        if count == 0:
            return {
                'error': 'No hay imágenes disponibles para esta fecha/área',
                'fecha_buscada': fecha,
                'area': f'{radio_metros}m radio'
            }
        
        # Tomar la imagen más reciente
        imagen = s2_collection.sort('system:time_start', False).first()
        
        # Calcular NDVI: (NIR - Red) / (NIR + Red)
        # Sentinel-2: B8 = NIR, B4 = Red
        ndvi = imagen.normalizedDifference(['B8', 'B4']).rename('NDVI')
        
        # Estadísticas sobre el área
        stats = ndvi.reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.minMax(), '', True
            ).combine(
                ee.Reducer.stdDev(), '', True
            ),
            geometry=area,
            scale=10,  # Resolución de 10 metros
            maxPixels=1e9
        ).getInfo()
        
        # Metadata de la imagen
        metadata = imagen.getInfo()
        fecha_imagen = datetime.fromtimestamp(
            metadata['properties']['system:time_start'] / 1000
        ).strftime('%Y-%m-%d')
        
        return {
            'fecha_solicitada': fecha,
            'fecha_imagen': fecha_imagen,
            'ndvi_promedio': round(stats.get('NDVI_mean', 0), 4),
            'ndvi_min': round(stats.get('NDVI_min', 0), 4),
            'ndvi_max': round(stats.get('NDVI_max', 0), 4),
            'ndvi_desviacion': round(stats.get('NDVI_stdDev', 0), 4),
            'nubosidad': metadata['properties'].get('CLOUDY_PIXEL_PERCENTAGE'),
            'satelite': 'Sentinel-2'
        }
    
    def test_connection(self) -> Dict:
        """
        Prueba la conexión a GEE y retorna info básica
        
        Returns:
            Dict con información de la conexión
        """
        if not self.authenticated:
            return {'status': 'error', 'message': 'No autenticado'}
        
        try:
            # Prueba simple: obtener info de un dataset conocido
            dataset = ee.Image('CGIAR/SRTM90_V4')
            info = dataset.getInfo()
            
            return {
                'status': 'success',
                'message': 'Conexión exitosa a Google Earth Engine',
                'dataset_test': 'CGIAR/SRTM90_V4',
                'bandas_disponibles': info['bands'][0]['id']
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


# Script de prueba
if __name__ == '__main__':
    print("=== Probando conexión a Google Earth Engine ===\n")
    
    # Inicializar cliente
    client = GEEClient()
    
    # Test 1: Verificar conexión
    print("Test 1: Verificar conexión")
    resultado = client.test_connection()
    print(f"Status: {resultado['status']}")
    print(f"Mensaje: {resultado['message']}\n")
    
    # Test 2: Detectar incendios (ejemplo)
    print("Test 2: Detectar incendios en Buenos Aires (2023)")
    incendios = client.detectar_incendios(
        provincia='Buenos Aires',
        fecha_inicio='2023-01-01',
        fecha_fin='2023-12-31'
    )
    print(f"Resultado: {incendios}\n")
    
    # Test 3: Calcular NDVI (ejemplo en Buenos Aires)
    print("Test 3: Calcular NDVI en Buenos Aires")
    ndvi = client.obtener_ndvi(
        latitud=-34.6037,
        longitud=-58.3816,
        radio_metros=1000,
        fecha='2024-01-15'
    )
    print(f"NDVI: {ndvi}")