from typing import List, Optional, Any
from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ForestGuard"
    VERSION: str = "3.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # --- Environment & Debug (Lo que faltaba) ---
    ENVIRONMENT: str = "local"  # <--- ¡ESTO FALTABA!
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # --- CORS ---
    ALLOWED_ORIGINS: List[AnyHttpUrl] = []
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]

    # --- Database Config ---
    DB_HOST: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_PORT: Optional[str] = "5432"
    DB_NAME: Optional[str] = "postgres"

    # --- Connection Pool ---
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    # --- URL Maestra ---
    DATABASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", 
        case_sensitive=True,
        extra="ignore" 
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info: ValidationInfo) -> Any:
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        if not values.get("DB_HOST") or not values.get("DB_USER"):
            return None

        user = values.get("DB_USER")
        password = values.get("DB_PASSWORD")
        host = values.get("DB_HOST")
        port = values.get("DB_PORT", "5432")
        db = values.get("DB_NAME", "postgres")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

settings = Settings()