from typing import Any, List, Optional
from urllib.parse import quote_plus  # ← AGREGADO

from pydantic import AnyHttpUrl, Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ForestGuard"
    VERSION: str = "3.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # --- Environment & Debug ---
    ENVIRONMENT: str = "local"
    DEBUG: bool = False  # Default to False for security
    LOG_LEVEL: str = "INFO"

    # --- Testing ---
    EST_DATABASE_URL: str | None = None

    # --- Security ---
    API_KEY: Optional[SecretStr] = None  # Loaded from .env or environment variables
    ADMIN_API_KEY: Optional[SecretStr] = None  # Admin capabilities
    SECRET_KEY: Optional[SecretStr] = None  # For JWT/session signing; loaded from .env
    GOOGLE_CLIENT_ID: Optional[str] = None  # Google OAuth client ID for frontend auth
    SUPABASE_URL: Optional[str] = None
    SUPABASE_JWT_SECRET: Optional[SecretStr] = None
    SUPABASE_JWT_AUDIENCE: Optional[str] = "authenticated"

    # --- Alerting ---
    ALERT_EMAIL: Optional[str] = None  # Email to receive security alerts
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # --- MercadoPago ---
    MERCADOPAGO_ACCESS_TOKEN: str = Field(
        default="",
        description="Token de acceso de MercadoPago. NUNCA hardcodear.",
    )
    MP_ACCESS_TOKEN: Optional[str] = None
    MP_WEBHOOK_SECRET: Optional[str] = None
    MP_NOTIFICATION_URL: Optional[str] = None
    MP_MOCK_MODE: bool = False
    MP_MOCK_APPROVE: bool = True

    # --- Banco Nacion (USD/ARS) ---
    BNA_EXCHANGE_RATE_URL: str = "https://www.bna.com.ar/Personas"

    # --- Geocoding (Nominatim) ---
    GEOCODE_BASE_URL: str = "https://nominatim.openstreetmap.org/search"
    GEOCODE_USER_AGENT: str = "ForestGuard/1.0 (contact@forestguard.ar)"
    GEOCODE_EMAIL: Optional[str] = None
    GEOCODE_COUNTRY: Optional[str] = "ar"
    GEOCODE_TIMEOUT: int = 8
    GEOCODE_LIMIT: int = 1

    # URLs de retorno de pagos
    PAYMENT_SUCCESS_URL: str = "https://forestguard.ar/payments/return?status=success"
    PAYMENT_FAILURE_URL: str = "https://forestguard.ar/payments/return?status=failure"
    PAYMENT_PENDING_URL: str = "https://forestguard.ar/payments/return?status=pending"
    PAYMENT_SUCCESS_URL_ANDROID: Optional[str] = None
    PAYMENT_FAILURE_URL_ANDROID: Optional[str] = None
    PAYMENT_PENDING_URL_ANDROID: Optional[str] = None

    # --- Feature Flags (MVP) ---
    FEATURE_CERTIFICATES: bool = False
    FEATURE_REFUGES: bool = False

    # --- Rate Limiting / Proxy ---
    TRUSTED_PROXIES: List[str] = Field(
        default_factory=lambda: ["127.0.0.1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        description="CIDR ranges of trusted reverse proxies for X-Forwarded-For",
    )

    # --- Storage ---
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: str = "storage"
    STORAGE_PUBLIC_URL: str = "http://127.0.0.1:9000"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # --- CORS ---
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=list,
        description="List of allowed CORS origins. Configure in .env",
    )
    ALLOWED_METHODS: List[str] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS (BL-004).",
    )
    ALLOWED_HEADERS: List[str] = Field(
        default_factory=lambda: [
            "Authorization", "Content-Type", "X-API-Key",
            "X-Request-ID", "X-Idempotency-Key", "Idempotency-Key", "X-Skip-Auth-Redirect",
            "Accept", "Accept-Language",
        ],
        description="Allowed HTTP headers for CORS (BL-004).",
    )
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]

    # --- Database Config ---
    DB_HOST: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_PORT: Optional[str] = "5432"
    DB_NAME: Optional[str] = "postgres"
    TEST_DATABASE_URL: Optional[str] = None

    # --- Connection Pool ---
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_PRE_PING: bool = True

    # --- URL Maestra ---
    DATABASE_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def default_allowed_origins(
        cls, v: Optional[List[str]], info: ValidationInfo
    ) -> Optional[List[str]]:
        env = info.data.get("ENVIRONMENT") or "local"
        if env != "production":
            if v is None:
                return ["http://localhost:5173", "http://localhost:3000"]
            if isinstance(v, str) and v.strip() in ("", "[]"):
                return ["http://localhost:5173", "http://localhost:3000"]
            if isinstance(v, list) and len(v) == 0:
                return ["http://localhost:5173", "http://localhost:3000"]
        return v

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
    def validate_secret_key(
        cls, v: Optional[SecretStr], info: ValidationInfo
    ) -> Optional[SecretStr]:
        # Require a SECRET_KEY for non-local deployments
        env = info.data.get("ENVIRONMENT") or "local"
        if env != "local" and not v:
            raise ValueError(
                "SECRET_KEY must be set in environment for non-local deployments"
            )
        return v

    @field_validator("STORAGE_BACKEND", mode="after")
    @classmethod
    def validate_storage_backend(cls, v: str, info: ValidationInfo) -> str:
        """Block local storage in production (BL-003 / SEC-012)."""
        env = info.data.get("ENVIRONMENT") or "local"
        if env == "production" and v == "local":
            raise ValueError(
                "STORAGE_BACKEND='local' is not allowed in production. "
                "Use 'gcs' or 'r2'."
            )
        return v


settings = Settings()

# Import centralized email configuration
from app.core.email_config import email_config
