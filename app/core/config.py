from typing import List, Optional, Any
from urllib.parse import quote_plus  # ← AGREGADO
from pydantic import AnyHttpUrl, SecretStr, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "ForestGuard"
    VERSION: str = "3.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # --- Environment & Debug ---
    ENVIRONMENT: str = "local"
    DEBUG: bool = False  # Default to False for security
    LOG_LEVEL: str = "INFO"

    # --- Security ---
    API_KEY: Optional[SecretStr] = None  # Loaded from .env or environment variables
    ADMIN_API_KEY: Optional[SecretStr] = None  # Admin capabilities
    SECRET_KEY: Optional[SecretStr] = None  # For JWT/session signing; loaded from .env
    GOOGLE_CLIENT_ID: Optional[str] = None  # Google OAuth client ID for frontend auth
    
    # --- Alerting ---
    ALERT_EMAIL: Optional[str] = None  # Email to receive security alerts
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # --- CORS ---
    ALLOWED_ORIGINS: List[str] = ["*"]  # Open for MVP accessibility
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
        # Si ya viene una URL completa, usarla directamente
        if isinstance(v, str) and v:
            return v
        
        values = info.data
        if not values.get("DB_HOST") or not values.get("DB_USER"):
            return None

        user = values.get("DB_USER")
        # URL-encode el password para manejar caracteres especiales (@, #, !, etc.)
        password = quote_plus(values.get("DB_PASSWORD") or "")
        host = values.get("DB_HOST")
        port = values.get("DB_PORT", "5432")
        db = values.get("DB_NAME", "postgres")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[SecretStr], info: ValidationInfo) -> Optional[SecretStr]:
        # Require a SECRET_KEY for non-local deployments
        env = info.data.get("ENVIRONMENT") or "local"
        if env != "local" and not v:
            raise ValueError("SECRET_KEY must be set in environment for non-local deployments")
        return v

settings = Settings()

# Import centralized email configuration
from app.core.email_config import email_config