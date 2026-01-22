"""
Configuración de la API Principal - Wildfire Recovery System
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class APISettings(BaseSettings):
    """Settings de la API Principal"""
    
    # API
    app_name: str = "Wildfire Recovery API"
    app_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # Supabase (base de datos)
    supabase_url: str
    supabase_service_key: str
    
    # Límites
    max_incendios_por_consulta: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignorar variables extra del .env


@lru_cache()
def get_api_settings() -> APISettings:
    """Retorna settings cacheadas"""
    return APISettings()


# Export
settings = get_api_settings()


if __name__ == "__main__":
    print("=== Configuración de la API ===\n")
    print(f"App: {settings.app_name} v{settings.app_version}")
    print(f"Host: {settings.api_host}:{settings.api_port}")
    print(f"Debug: {settings.debug}")
    print(f"Max incendios por consulta: {settings.max_incendios_por_consulta}")
