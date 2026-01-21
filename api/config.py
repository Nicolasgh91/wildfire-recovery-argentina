"""
Configuración de la aplicación
Lee variables de entorno y provee settings globales
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Settings de la aplicación"""
    
    # API
    app_name: str = "Wildfire Recovery API"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    supabase_db_url: str
    
    # Google Earth Engine
    gee_service_account_email: str
    gee_private_key_path: str
    
    # Microservicio de imágenes
    image_service_url: str = "http://localhost:8001"
    
    # Configuración de análisis
    max_incendios_por_consulta: int = 100
    meses_analisis_post_incendio: int = 36
    
    # Reglas de negocio
    distancia_recurrencia_metros: int = 100
    dias_minimos_recurrencia: int = 180  # 6 meses
    porcentaje_superposicion_minimo: float = 5.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Retorna settings cacheadas (singleton)
    Usa lru_cache para no recrear el objeto en cada llamada
    """
    return Settings()


# Para importar fácilmente
settings = get_settings()


if __name__ == "__main__":
    # Test de configuración
    print("=== Configuración de la API ===\n")
    print(f"App: {settings.app_name} v{settings.app_version}")
    print(f"Puerto: {settings.api_port}")
    print(f"Supabase URL: {settings.supabase_url[:30]}...")
    print(f"GEE Service Account: {settings.gee_service_account_email}")
    print(f"Image Service: {settings.image_service_url}")
    print(f"\nReglas de negocio:")
    print(f"- Distancia recurrencia: {settings.distancia_recurrencia_metros}m")
    print(f"- Días mínimos recurrencia: {settings.dias_minimos_recurrencia}")
    print(f"- Superposición mínima: {settings.porcentaje_superposicion_minimo}%")