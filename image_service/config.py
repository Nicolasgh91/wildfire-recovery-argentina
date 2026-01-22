"""
Configuración del microservicio de análisis de imágenes
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class ImageServiceSettings(BaseSettings):
    """Settings del microservicio de imágenes"""
    
    # API
    service_name: str = "Image Analysis Service"
    service_version: str = "1.0.0"
    service_host: str = "0.0.0.0"
    service_port: int = 8001
    debug: bool = True
    
    # Supabase (para guardar resultados)
    supabase_url: str
    supabase_service_key: str
    
    # Google Earth Engine
    gee_service_account_email: str
    gee_private_key_path: str
    
    # Configuración de análisis
    meses_analisis: int = 36  # 3 años
    dias_ventana_imagen: int = 15  # ±15 días para buscar imagen
    max_nubosidad: int = 20  # % máximo de nubes
    resolucion_metros: int = 10  # Sentinel-2
    radio_buffer_metros: int = 500  # Radio adicional alrededor del punto
    
    # Umbrales de detección
    ndvi_vegetacion_densa: float = 0.6  # NDVI > 0.6 = vegetación densa
    ndvi_vegetacion_moderada: float = 0.3  # 0.3 < NDVI < 0.6 = moderada
    umbral_cambio_construccion: float = 0.15  # Cambio en NDVI que sugiere construcción
    
    # Performance
    max_workers: int = 3  # Máximo de análisis en paralelo
    timeout_por_mes: int = 60  # Segundos máximo por mes
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorar variables extra del .env


@lru_cache()
def get_image_settings() -> ImageServiceSettings:
    """Retorna settings cacheadas"""
    return ImageServiceSettings()


# Export
settings = get_image_settings()


if __name__ == "__main__":
    print("=== Configuración del Microservicio de Imágenes ===\n")
    print(f"Servicio: {settings.service_name} v{settings.service_version}")
    print(f"Puerto: {settings.service_port}")
    print(f"\nParámetros de análisis:")
    print(f"- Meses a analizar: {settings.meses_analisis}")
    print(f"- Ventana de búsqueda: ±{settings.dias_ventana_imagen} días")
    print(f"- Nubosidad máxima: {settings.max_nubosidad}%")
    print(f"- Resolución: {settings.resolucion_metros}m")
    print(f"\nUmbrales:")
    print(f"- Vegetación densa: NDVI > {settings.ndvi_vegetacion_densa}")
    print(f"- Vegetación moderada: NDVI > {settings.ndvi_vegetacion_moderada}")
    print(f"- Cambio construcción: Δ NDVI > {settings.umbral_cambio_construccion}")