# ForestGuard - Backend API Documentation v2.0

**Fecha de actualización**: Febrero 2026  
**Framework**: FastAPI 0.110+  
**Python**: 3.11+  
**Estado**: 85% implementado (21/31 tareas técnicas)

---

## 1. Visión General del Backend

El backend de ForestGuard es una **API REST asíncrona** construida con FastAPI que gestiona:

1. **Detección y análisis de incendios** desde datos satelitales NASA FIRMS
2. **Generación de evidencia legal** para fiscalización bajo Ley 26.815
3. **Procesamiento de imágenes satelitales** vía Google Earth Engine
4. **Reportes especializados** históricos y judiciales
5. **Sistema de pagos** vía MercadoPago
6. **Workers asíncronos** con Celery para operaciones pesadas

### Principios de Diseño

- **Async-First**: Todas las operaciones I/O son asíncronas (httpx, asyncpg)
- **Service Layer**: Lógica de negocio separada de endpoints
- **Type Safety**: Pydantic v2 para validación estricta
- **Separation of Concerns**: 11 routers v1 + 12 legacy en transición
- **Idempotencia**: Endpoints críticos con deduplicación
- **Auditoría**: Logging estructurado JSON + audit_events table

---

## 2. Estructura del Proyecto

```
app/
├── main.py                 # FastAPI app + router registration
├── api/
│   ├── v1/                 # Modern API (11 routers)
│   │   ├── fires.py
│   │   ├── audit.py
│   │   ├── explorations.py
│   │   ├── quality.py
│   │   ├── analysis.py
│   │   ├── reports.py
│   │   ├── contact.py
│   │   ├── payments.py
│   │   ├── certificates.py
│   │   ├── auth.py
│   │   └── webhooks.py
│   └── routes/             # Legacy API (12 routers - transitioning)
│       ├── fires.py
│       ├── episodes.py
│       ├── historical.py
│       └── ...
├── services/               # Business logic (30 services)
│   ├── fire_service.py     (45KB)
│   ├── ers_service.py      (69KB)
│   ├── gee_service.py      (39KB)
│   ├── vae_service.py      (33KB)
│   ├── storage_service.py  (28KB)
│   └── ...
├── models/                 # SQLAlchemy 2.0 models (19 models)
│   ├── fire.py
│   ├── episode.py
│   ├── user.py
│   ├── protected_area.py
│   └── ...
├── schemas/                # Pydantic v2 schemas (15 schemas)
│   ├── fire.py
│   ├── audit.py
│   ├── report.py
│   └── ...
├── core/                   # Core infrastructure
│   ├── config.py           # Settings (Pydantic BaseSettings)
│   ├── security.py         # JWT, RLS, API keys
│   ├── middleware.py       # CORS, logging, error handling
│   ├── database.py         # AsyncSession factory
│   └── logging_config.py   # Structured JSON logging
├── workers/                # Celery workers
│   ├── episode_worker.py
│   ├── carousel_worker.py
│   ├── closure_worker.py
│   └── ...
└── utils/                  # Shared utilities
    ├── spatial.py          # PostGIS helpers
    ├── h3_utils.py         # H3 index operations
    └── validators.py       # Custom validators
```

---

## 3. API Routes (v1)

### 3.1 Inventario de Endpoints

**Total**: ~35 endpoints activos (11 v1 routers + 12 legacy)

#### `/api/v1/fires` - Gestión de Incendios

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| GET | `/api/v1/fires` | Listar incendios con filtros | UC-F03 | ✅ |
| GET | `/api/v1/fires/{fire_id}` | Detalle de un incendio | UC-F03 | ✅ |
| GET | `/api/v1/fires/stats` | Estadísticas agregadas | UC-F03 | ✅ |
| GET | `/api/v1/fires/export` | Exportar a CSV/JSON | UC-F03 | ✅ |
| GET | `/api/v1/fires/{fire_id}/slides` | Carousel de imágenes satelitales | UC-F08 | ✅ |

**Filtros soportados**:
- `province` (str)
- `start_date`, `end_date` (ISO8601)
- `min_area`, `max_area` (hectáreas)
- `status` (active, controlled, monitoring, extinguished)
- `has_protected_area` (bool)
- `page`, `page_size` (paginación)

**Ejemplo Request**:
```http
GET /api/v1/fires?province=Córdoba&start_date=2024-01-01&min_area=100&page=1&page_size=20
Authorization: Bearer <jwt>
```

**Ejemplo Response**:
```json
{
  "items": [
    {
      "id": "uuid",
      "centroid": {"lat": -31.4173, "lon": -64.1833},
      "province": "Córdoba",
      "start_date": "2024-02-15T10:30:00Z",
      "end_date": null,
      "status": "active",
      "estimated_area_hectares": 250.5,
      "total_detections": 45,
      "avg_frp": 120.3,
      "has_protected_area": true,
      "slides_data": [...]
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20
}
```

---

#### `/api/v1/audit` - Auditoría Legal

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/audit/land-use` | Consulta de restricciones legales | UC-F06 | 🔑 API Key |

**Request Body**:
```json
{
  "latitude": -31.4173,
  "longitude": -64.1833,
  "search_radius_meters": 5000
}
```

**Response** (200 OK):
```json
{
  "queried_location": {"lat": -31.4173, "lon": -64.1833},
  "fires_found": 3,
  "is_violation": true,
  "violation_severity": "high",
  "prohibition_until": "2054-02-15",
  "earliest_fire_date": "2024-02-15",
  "fires": [
    {
      "id": "uuid",
      "distance_km": 2.3,
      "fire_date": "2024-02-15",
      "protected_area": "Parque Nacional Quebrada del Condorito",
      "prohibition_years": 30,
      "thumbnails": ["https://storage.googleapis.com/..."]
    }
  ],
  "query_duration_ms": 234
}
```

**Rate Limiting**: 10 req/min por IP  
**Validaciones**:
- `search_radius_meters` <= 5000 (configurable en `system_parameters`)
- Lat/lon válidos para Argentina

---

#### `/api/v1/explorations` - Wizard de Exploración

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/explorations/` | Crear nueva investigación | UC-F11 | ✅ |
| GET | `/api/v1/explorations/{id}` | Estado de investigación | UC-F11 | ✅ |
| GET | `/api/v1/explorations/` | Listar investigaciones del usuario | UC-F11 | ✅ |

**Request Body** (POST):
```json
{
  "fire_event_id": "uuid",
  "investigation_type": "historical",
  "config": {
    "image_count": 12,
    "date_range_months": 36,
    "include_climate": true,
    "include_ndvi": true,
    "visualization_type": "NBR"
  }
}
```

**Flujo**:
1. POST → Crea registro con `status: draft`
2. Backend valida créditos del usuario
3. Si OK → `status: processing`, dispara Celery worker
4. Worker genera PDF con hash SHA-256
5. Actualiza `status: completed`, debita créditos
6. GET polling retorna `result_pdf_url` + `result_hash`

---

#### `/api/v1/quality` - Calidad de Datos

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| GET | `/api/v1/quality/fire-event/{fire_id}` | Métricas de confiabilidad | UC-F04 | ✅ |

**Response**:
```json
{
  "fire_event_id": "uuid",
  "reliability_score": 0.87,
  "classification": "high_confidence",
  "data_completeness": 0.92,
  "metrics": {
    "detections_confidence": 0.85,
    "imagery_quality": 0.90,
    "climate_availability": 0.88,
    "independent_detections": 0.85
  },
  "data_sources": [
    {
      "source_name": "NASA_FIRMS_VIIRS",
      "quality_weight": 0.40,
      "records_count": 45
    }
  ]
}
```

**Cálculo de `reliability_score`**:
```python
score = (
    detections_confidence * 0.40 +
    imagery_quality * 0.20 +
    climate_availability * 0.20 +
    independent_detections * 0.20
)
```

---

#### `/api/v1/analysis` - Análisis y Tendencias

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| GET | `/api/v1/analysis/recurrence` | Análisis de recurrencia H3 | UC-F05 | ✅ |
| GET | `/api/v1/analysis/trends` | Tendencias temporales | UC-F05 | ✅ |

**GET `/api/v1/analysis/recurrence?bbox=...&resolution=8`**

Retorna celdas H3 con métricas de recurrencia:
```json
{
  "cells": [
    {
      "h3_index": "886754a67ffffff",
      "event_count": 15,
      "years_with_fires": 3,
      "avg_area_hectares": 125.3,
      "max_frp_ever": 450.2,
      "recurrence_class": "high"
    }
  ],
  "resolution": 8,
  "total_cells": 234
}
```

**UC-F05**: Usa `h3_recurrence_stats` materialized view (refresh diario)

---

#### `/api/v1/reports` - Reportes Especializados

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/reports/judicial` | Reporte judicial | UC-F11 | ✅ + Pago |
| POST | `/api/v1/reports/historical` | Reporte histórico | UC-F11 | ✅ + Pago |
| GET | `/api/v1/reports/{report_id}` | Obtener reporte generado | UC-F11 | ✅ |

**Idempotencia**: Usa `Idempotency-Key` header (UUID v4)

**Request**:
```http
POST /api/v1/reports/historical
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <jwt>

{
  "fire_event_id": "uuid",
  "include_ndvi_analysis": true,
  "include_land_use_changes": true
}
```

**Response** (202 Accepted):
```json
{
  "report_id": "uuid",
  "status": "processing",
  "estimated_completion_seconds": 120,
  "credits_used": 10
}
```

---

#### `/api/v1/contact` - Formulario de Contacto

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/contact` | Enviar mensaje de contacto | UC-F01 | ❌ Public |

**Rate Limit**: 5 req/15min por IP  
**SMTP**: Gmail con App Password

---

#### `/api/v1/payments` - Sistema de Pagos

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/payments/create-preference` | Crear checkout MercadoPago | - | ✅ |
| GET | `/api/v1/payments/history` | Historial de pagos del usuario | - | ✅ |
| GET | `/api/v1/payments/credits` | Saldo de créditos | - | ✅ |

**POST `/api/v1/payments/create-preference`**:
```json
{
  "purpose": "credits",
  "amount_usd": 10.00,
  "credits_to_grant": 100
}
```

**Response**:
```json
{
  "payment_request_id": "uuid",
  "checkout_url": "https://www.mercadopago.com.ar/checkout/v1/redirect?pref_id=...",
  "external_reference": "FG-PAY-2024-000123",
  "expires_at": "2024-02-10T15:00:00Z"
}
```

---

#### `/api/v1/webhooks` - Webhooks Externos

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/webhooks/mercadopago` | Callback MercadoPago | - | 🔐 IP Whitelist |

**Flujo**:
1. MercadoPago POST a webhook con `topic=payment&id=<payment_id>`
2. Backend valida IP de MercadoPago
3. Consulta `/v1/payments/{id}` para obtener detalles
4. Si `status=approved` → acredita créditos vía `credit_user_balance()`
5. Registra en `payment_webhook_logs` (auditoría)

---

#### `/api/v1/certificates` - Certificados Legales

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| POST | `/api/v1/certificates` | Emitir certificado | UC-F10 | ✅ |
| GET | `/api/v1/certificates/{cert_number}/verify` | Verificar autenticidad | UC-F10 | ❌ Public |

**Certificado** incluye:
- Número único (`FG-CERT-2024-000123`)
- Snapshot JSON congelado del `fire_event`
- Hash SHA-256 del snapshot
- QR code con URL de verificación

**Verificación pública**:
```http
GET /api/v1/certificates/FG-CERT-2024-000123/verify
```

Retorna:
```json
{
  "valid": true,
  "certificate_number": "FG-CERT-2024-000123",
  "issued_at": "2024-02-09T12:00:00Z",
  "fire_event_summary": {
    "province": "Córdoba",
    "date": "2024-02-15",
    "area_hectares": 250.5
  },
  "hash_match": true
}
```

---

#### `/api/v1/auth` - Autenticación

| Método | Endpoint | Descripción | UC | Auth |
|--------|----------|-------------|----|----|
| GET | `/api/v1/auth/me` | Obtener usuario actual | - | ✅ |
| POST | `/api/v1/auth/logout` | Cerrar sesión | - | ✅ |

**GET `/auth/me`**:
- Valida JWT de Supabase
- Llama a `get_or_create_supabase_user()` para sincronizar metadata
- Retorna usuario con créditos

**Response**:
```json
{
  "id": "uuid",
  "email": "usuario@example.com",
  "full_name": "Juan Pérez",
  "role": "user",
  "credits_balance": 50,
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

### 3.2 Versionado de API

**Estrategia actual**: Transición de legacy `app/api/routes/` → `app/api/v1/`

| Router | v1 Status | Legacy Status | Acción |
|--------|-----------|---------------|--------|
| `fires` | ✅ Completo | 🔄 Stub (re-export) | Eliminar legacy |
| `audit` | ✅ Completo | ❌ No existe | - |
| `explorations` | ✅ Completo | ❌ No existe | - |
| `episodes` | ❌ Solo legacy | ✅ Funcional | Migrar a v1 |
| `historical` | Parcial (reports) | ✅ Funcional | Consolidar |

**Roadmap**: Consolidar de 34 archivos a 17

---

## 4. Service Layer

### 4.1 Servicios Principales

**Total**: 30 servicios (~1.2MB de lógica de negocio)

#### FireService (45KB)

**Ubicación**: `app/services/fire_service.py`

**Responsabilidades**:
- Listar y filtrar incendios (`get_fires()`)
- Calcular estadísticas agregadas (`get_stats()`)
- Exportar a CSV/JSON (`export_fires()`)
- Gestión de carousel de imágenes (`get_slides()`)

**Métodos clave**:
```python
class FireService:
    async def get_fires(
        self,
        province: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        min_area: float | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse[FireEventSchema]:
        """Filtrado con query builder SQLAlchemy."""
        
    async def get_stats(
        self,
        province: str | None = None,
        year: int | None = None
    ) -> FireStatsSchema:
        """Usa materialized view fire_stats para performance."""
```

**Optimizaciones**:
- Usa `fire_stats` MV para estadísticas pre-calculadas
- Eager loading de relaciones (`protected_areas`, `slides_data`)
- Índices GiST en `centroid` y `perimeter`

---

#### ERSService (69KB) - Exploration & Reports Service

**Ubicación**: `app/services/ers_service.py`

**Responsabilidades**:
- Wizard de exploración UC-F11 (`create_investigation()`)
- Generación de PDFs históricos/judiciales (`generate_report()`)
- Cálculo de costos en créditos (`calculate_credits()`)
- Gestión de evidencia satelital reproducible

**Métodos clave**:
```python
class ERSService:
    async def create_investigation(
        self,
        user_id: UUID,
        fire_event_id: UUID,
        config: InvestigationConfigSchema
    ) -> ExplorationInvestigationSchema:
        """
        1. Valida saldo de créditos
        2. Crea registro con status=processing
        3. Dispara Celery task generate_report_task.delay()
        4. Retorna investigation_id para polling
        """
        
    async def generate_report(
        self,
        investigation_id: UUID
    ) -> ReportResultSchema:
        """
        (Ejecutado por Celery worker)
        1. Consulta GEE para imágenes HD usando gee_system_index
        2. Genera time series NDVI
        3. Renderiza PDF con plantilla Jinja2
        4. Calcula hash SHA-256
        5. Sube a GCS con retention 90 días
        6. Debita créditos vía credit_user_balance()
        """
```

**Dependencias**:
- `GEEService` para imágenes on-demand
- `StorageService` para GCS uploads
- `CreditService` para gestión de créditos

---

#### GEEService (39KB)

**Ubicación**: `app/services/gee_service.py`

**Responsabilidades**:
- Autenticación con GEE (`ee.Initialize()`)
- Query de Sentinel-2 ImageCollection
- Filtrado por cloud coverage, fecha, bbox
- Generación de thumbnails (SWIR, RGB, NBR)
- Reproducción de imágenes HD from `gee_system_index`

**Métodos clave**:
```python
class GEEService:
    async def find_best_image(
        self,
        bbox: BoundingBox,
        date_range: tuple[date, date],
        max_cloud_coverage: float = 30.0
    ) -> GEEImageMetadata:
        """
        1. Query ImageCollection Sentinel-2 L2A
        2. Filter por bounds, dates, cloud < max
        3. Sort por cloud coverage ASC
        4. Retorna .first() con system:index
        """
        
    async def generate_thumbnail(
        self,
        image: ee.Image,
        bands: list[str],
        visualization_params: dict
    ) -> bytes:
        """
        1. Select bands
        2. Visualize con min/max/palette
        3. getThumbURL con dimensions 512x512
        4. httpx.get para descargar bytes
        """
        
    async def reproduce_hd_image(
        self,
        gee_system_index: str,
        visualization_params: dict
    ) -> bytes:
        """
        1. ee.Image(gee_system_index) - exact reproducibility
        2. getDownloadURL con dimensions 2048x2048
        3. Retorna bytes para attachment
        """
```

**Cuotas GEE**:
- 50k requests/día
- 40 operaciones simultáneas
- Batch size configurable (default: 15 incendios/corrida)

---

#### VAEService (33KB) - Vegetation After Event

**Ubicación**: `app/services/vae_service.py`

**Responsabilidades**:
- Monitoreo post-incendio UC-F12
- Cálculo de NDVI time series
- Detección de cambios de uso del suelo
- Alertas de posibles violaciones Ley 26.815

**Métodos clave**:
```python
class VAEService:
    async def create_monitoring_record(
        self,
        fire_event_id: UUID,
        monitoring_date: date
    ) -> VegetationMonitoringSchema:
        """
        1. Consulta imagen Sentinel-2 para fecha
        2. Calcula NDVI = (NIR - Red) / (NIR + Red)
        3. Compara vs baseline_ndvi (pre-incendio)
        4. Calcula recovery_percentage
        5. Detecta human_activity si NDVI baja inesperadamente
        """
        
    async def detect_land_use_change(
        self,
        monitoring_record_id: UUID
    ) -> LandUseChangeSchema | None:
        """
        1. Compara clasificación actual vs anterior
        2. Si cambió a "agriculture" o "urban_development"
        3. Calcula severity y confidence
        4. Crea alerta con is_potential_violation=True
        """
```

**Algoritmo de clasificación**:
```python
def classify_land_use(ndvi_mean: float, ndvi_std: float) -> str:
    if ndvi_mean > 0.6:
        return "forest"
    elif ndvi_mean > 0.3:
        return "grassland"
    elif ndvi_mean > 0.1:
        return "sparse_vegetation"
    else:
        return "bare_soil_or_urban"
```

---

#### StorageService (28KB)

**Ubicación**: `app/services/storage_service.py`

**Responsabilidades**:
- Upload/download desde Google Cloud Storage
- Gestión de retention policies
- Cloudflare R2 como fallback
- URL signing para acceso temporal

**Métodos clave**:
```python
class StorageService:
    async def upload_thumbnail(
        self,
        file_bytes: bytes,
        fire_event_id: UUID,
        image_type: str
    ) -> str:
        """
        1. Genera key: fires/{fire_event_id}/{image_type}_thumb.webp
        2. Upload con content-type image/webp
        3. Set public-read ACL
        4. Retorna public URL
        """
        
    async def upload_pdf_with_retention(
        self,
        pdf_bytes: bytes,
        investigation_id: UUID,
        retention_days: int = 90
    ) -> str:
        """
        1. Upload a GCS bucket
        2. Set lifecycle policy: delete after retention_days
        3. Retorna signed URL válida por 90 días
        """
```

**FinOps**:
- Thumbnails: persistentes (< 500KB c/u, ~10k imágenes = ~5GB)
- PDFs: 90 días retention
- GeoTIFFs: 7 días retention

---

#### AuditService (16KB)

**Ubicación**: `app/services/audit_service.py`

**Responsabilidades**:
- Consultas de auditoría legal UC-F06
- Cálculo de `prohibition_until`
- Spatial queries con PostGIS `ST_DWithin`

**Métodos clave**:
```python
class AuditService:
    async def land_use_audit(
        self,
        lat: float,
        lon: float,
        radius_meters: float = 5000
    ) -> AuditResultSchema:
        """
        1. Valida radius_meters <= system_parameters.audit_search_radius_max
        2. Query fire_events con ST_DWithin(centroid, point, radius)
        3. Join fire_protected_area_intersections
        4. Calcula earliest_fire_date, prohibition_until
        5. Registra en land_use_audits table (inmutable)
        6. Retorna violación si prohibition_until > hoy
        """
```

**SQL optimizado**:
```sql
SELECT fe.*, fpai.protection_until, fpai.protected_area_id
FROM fire_events fe
JOIN fire_protected_area_intersections fpai ON fe.id = fpai.fire_event_id
WHERE ST_DWithin(
    fe.centroid::geography,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :radius_meters
)
ORDER BY fe.start_date DESC
```

---

#### EpisodeService (18KB)

**Ubicación**: `app/services/episode_service.py`

**Responsabilidades**:
- Macro-agrupación de eventos UC-F13
- Clustering espacial + temporal
- Gestión de merges de episodios
- Scoring para priorización GEE

**Métodos clave**:
```python
class EpisodeService:
    async def cluster_events_into_episodes(
        self,
        clustering_version_id: UUID
    ) -> list[EpisodeSchema]:
        """
        1. Query fire_events sin episode asignado
        2. Aplica ST-DBSCAN con clustering_version params
        3. Crea fire_episodes para cada cluster
        4. Vincula vía fire_episode_events (N:M)
        5. Calcula gee_priority score
        """
        
    def calculate_gee_priority(
        self,
        episode: Episode
    ) -> int:
        """
        Score = (
            (area_hectares / 1000) * 40 +
            (frp_sum / 10000) * 30 +
            (protected_area_overlap ? 30 : 0)
        )
        """
```

**Clustering parameters** (de `clustering_versions` table):
- `epsilon_km`: 50km (distancia máxima entre eventos)
- `min_points`: 3 (mínimo de eventos para formar episodio)
- `temporal_window_hours`: 168 (7 días)

---

### 4.2 Servicios de Soporte

| Servicio | LOC | Propósito |
|----------|-----|-----------|
| `QualityService` | 14KB | Cálculo de reliability_score UC-F04 |
| `RecurrenceService` | 6KB | Análisis H3 UC-F05 |
| `TrendsService` | 6KB | Tendencias temporales UC-F05 |
| `ClusteringService` | 12KB | ST-DBSCAN implementation |
| `ContactService` | 4KB | SMTP envío de contacto |
| `MercadoPagoService` | 15KB | Integración pagos |
| `CreditService` | 8KB | Gestión de user_credits |
| `ExportService` | 10KB | CSV/JSON/Parquet exports |
| `ImageryService` | 26KB | Gestión de satellite_images |

---

## 5. Data Models (SQLAlchemy 2.0)
### 5.1 Base Setup

```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=settings.DEBUG)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()
```

### 5.2 Modelos Principales

#### FireEvent (`app/models/fire.py`)

```python
class FireEvent(Base):
    __tablename__ = "fire_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    centroid = Column(Geometry("POINT", srid=4326), nullable=False)
    perimeter = Column(Geometry("POLYGON", srid=4326))
    
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True))
    
    province = Column(String(50), nullable=False, index=True)
    department = Column(String(100))
    
    total_detections = Column(Integer, default=0)
    estimated_area_hectares = Column(Numeric(10, 2))
    avg_frp = Column(Numeric(8, 2))
    max_frp = Column(Numeric(8, 2))
    
    status = Column(
        Enum("active", "controlled", "monitoring", "extinguished"),
        default="active",
        index=True
    )
    
    h3_index = Column(BigInteger, index=True)  # H3 resolution 8
    slides_data = Column(JSONB, default=list)  # Carousel metadata
    last_gee_image_id = Column(String(255))
    clustering_version_id = Column(UUID, ForeignKey("clustering_versions.id"))
    
    # Relationships
    detections = relationship("FireDetection", back_populates="fire_event")
    episodes = relationship("FireEpisodeEvent", back_populates="fire_event")
    protected_area_intersections = relationship(
        "FireProtectedAreaIntersection",
        back_populates="fire_event"
    )
```

**Indices**:
- GiST en `centroid` y `perimeter`
- B-tree en `start_date`, `province`, `status`, `h3_index`

---

#### User (`app/models/user.py`)

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True)  # From Supabase auth.users
    email = Column(String(255), unique=True, nullable=False, index=True)
    dni = Column(String(20), unique=True)
    full_name = Column(String(255))
    role = Column(Enum("admin", "user"), default="user")
    google_id = Column(String(255), unique=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True))
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    credits = relationship("UserCredits", uselist=False, back_populates="user")
    investigations = relationship("ExplorationInvestigation", back_populates="user")
    saved_filters = relationship("UserSavedFilter", back_populates="user")
```

---

#### ExplorationInvestigation (`app/models/exploration.py`)

```python
class ExplorationInvestigation(Base):
    __tablename__ = "exploration_investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    fire_event_id = Column(UUID, ForeignKey("fire_events.id"), nullable=False)
    
    investigation_type = Column(Enum("historical", "judicial"), nullable=False)
    status = Column(
        Enum("draft", "submitted", "processing", "completed", "failed"),
        default="draft"
    )
    
    config = Column(JSONB, nullable=False)  # User selections
    result_pdf_url = Column(Text)
    result_hash = Column(String(64))  # SHA-256
    
    total_cost_usd = Column(Numeric(10, 2))
    credits_used = Column(Integer)
    payment_request_id = Column(UUID, ForeignKey("payment_requests.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    submitted_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
```

**RLS Policy** (aplicado a nivel Supabase):
```sql
CREATE POLICY "Users can only see their own investigations"
ON exploration_investigations
FOR ALL
USING (auth.uid() = user_id);
```

---

## 6. Pydantic Schemas

### 6.1 Request/Response Schemas

#### FireEventSchema (`app/schemas/fire.py`)

```python
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID

class FireEventSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    centroid: dict[str, float]  # {"lat": ..., "lon": ...}
    province: str
    start_date: datetime
    end_date: datetime | None
    status: Literal["active", "controlled", "monitoring", "extinguished"]
    estimated_area_hectares: float | None
    total_detections: int
    avg_frp: float | None
    h3_index: int | None
    slides_data: list[dict] = Field(default_factory=list)
    protected_areas: list[str] = Field(default_factory=list)
    
class FireFiltersSchema(BaseModel):
    province: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    min_area: float | None = Field(None, ge=0)
    max_area: float | None = Field(None, ge=0)
    status: str | None = None
    has_protected_area: bool | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
```

---

#### AuditSchema (`app/schemas/audit.py`)

```python
class LandUseAuditRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    search_radius_meters: float = Field(5000, ge=100, le=5000)

class AuditResultSchema(BaseModel):
    queried_location: dict[str, float]
    fires_found: int
    is_violation: bool
    violation_severity: Literal["none", "low", "medium", "high"] | None
    prohibition_until: date | None
    earliest_fire_date: date | None
    fires: list[dict]
    query_duration_ms: int
```

---

### 6.2 Validación Personalizada

```python
from pydantic import field_validator

class ExplorationConfigSchema(BaseModel):
    image_count: int = Field(..., ge=1, le=24)
    date_range_months: int = Field(..., ge=1, le=60)
    include_climate: bool = True
    include_ndvi: bool = True
    visualization_type: Literal["SWIR", "RGB", "NBR", "NDVI"]
    
    @field_validator("image_count")
    @classmethod
    def validate_image_count(cls, v, info):
        if v > 12 and not info.data.get("include_climate"):
            raise ValueError("image_count > 12 requires include_climate=True")
        return v
```

---

## 7. Core Infrastructure

### 7.1 Settings (`app/core/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "ForestGuard API"
    VERSION: str = "2.0"
    ENVIRONMENT: Literal["development", "staging", "production"]
    DEBUG: bool = Field(default=False)
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    ALLOWED_ORIGINS: list[str] = Field(default_factory=list)
    
    # Database
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Security
    SECRET_KEY: str  # For production JWT signing
    API_KEY_HEADER: str = "X-API-Key"
    
    # GEE
    GOOGLE_APPLICATION_CREDENTIALS: str
    
    # Storage
    GCS_BUCKET_NAME: str
    GCS_PROJECT_ID: str
    
    # Workers
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    
    # External APIs
    NASA_FIRMS_API_KEY: str
    MERCADOPAGO_ACCESS_TOKEN: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

---

### 7.2 Security (`app/core/security.py`)

#### JWT Validation (Supabase)

```python
import jwt
from fastapi import Depends, HTTPException, Header

async def get_current_user(
    authorization: str = Header(None)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")
    
    token = authorization.split(" ")[1]
    
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated"
        )
        user_id = UUID(payload["sub"])
    except jwt.JWTError:
        raise HTTPException(401, "Invalid token")
    
    # Sync user from Supabase auth.users to local users table
    user = await get_or_create_supabase_user(user_id, payload)
    return user
```

#### API Key Validation

```python
async def validate_api_key(
    api_key: str = Header(None, alias=settings.API_KEY_HEADER)
):
    if not api_key:
        raise HTTPException(401, f"Missing {settings.API_KEY_HEADER} header")
    
    # Query from api_keys table or settings
    if api_key not in settings.VALID_API_KEYS:
        raise HTTPException(403, "Invalid API key")
```

#### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/contact")
@limiter.limit("5/15minutes")
async def contact_endpoint(...):
    ...
```

---

### 7.3 Middleware (`app/core/middleware.py`)

#### CORS

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Request Logging

```python
import time
import logging
from uuid import uuid4

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id": getattr(request.state, "user_id", None),
        }
    )
    
    response.headers["X-Request-ID"] = request_id
    return response
```

#### Error Handling

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={"request_id": request.state.request_id}
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "request_id": request.state.request_id
        }
    )
```

---

## 8. Celery Workers

### 8.1 Setup

```python
# app/workers/celery_app.py
from celery import Celery

celery_app = Celery(
    "forestguard_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
)
```

### 8.2 Tasks

#### Episode Clustering

```python
@celery_app.task(name="cluster_fire_episodes")
def cluster_episodes_task(clustering_version_id: str):
    """
    Ejecuta ST-DBSCAN clustering diario.
    Triggered by: Celery Beat @ 03:00 ART
    """
    episode_service = EpisodeService()
    episodes = await episode_service.cluster_events_into_episodes(
        UUID(clustering_version_id)
    )
    return {"episodes_created": len(episodes)}
```

#### Carousel Generation

```python
@celery_app.task(name="generate_fire_carousels")
def generate_carousels_task():
    """
    Genera thumbnails GEE para incendios activos.
    Batch size: 15 incendios
    Triggered by: Celery Beat @ daily 04:00 ART
    """
    gee_service = GEEService()
    storage_service = StorageService()
    
    active_fires = await fire_service.get_active_fires_without_slides(limit=15)
    
    for fire in active_fires:
        images = await gee_service.find_best_images(fire.bbox, fire.date_range)
        slides = []
        
        for image_type in ["SWIR", "RGB", "NBR"]:
            thumb_bytes = await gee_service.generate_thumbnail(image, image_type)
            url = await storage_service.upload_thumbnail(thumb_bytes, fire.id, image_type)
            slides.append({
                "image_type": image_type,
                "url": url,
                "gee_system_index": image.system_index,
                "bands_config": image.bands_config
            })
        
        await fire_service.update_slides_data(fire.id, slides)
```

#### Report Generation

```python
@celery_app.task(name="generate_investigation_report")
def generate_report_task(investigation_id: str):
    """
    Genera PDF de reporte histórico/judicial.
    Triggered by: POST /api/v1/explorations/
    """
    ers_service = ERSService()
    result = await ers_service.generate_report(UUID(investigation_id))
    return {"pdf_url": result.pdf_url, "hash": result.hash}
```

### 8.3 Celery Beat Schedule

```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cluster-episodes-daily": {
        "task": "cluster_fire_episodes",
        "schedule": crontab(hour=3, minute=0),  # 03:00 ART
        "args": (str(settings.DEFAULT_CLUSTERING_VERSION_ID),)
    },
    "generate-carousels-daily": {
        "task": "generate_fire_carousels",
        "schedule": crontab(hour=4, minute=0),  # 04:00 ART
    },
    "refresh-materialized-views": {
        "task": "refresh_all_mvs",
        "schedule": crontab(hour=2, minute=0),  # 02:00 ART
    },
    "ingest-nasa-firms": {
        "task": "ingest_firms_data",
        "schedule": crontab(hour=1, minute=0),  # 01:00 ART (daily)
    },
}
```

---

## 9. Testing

### 9.1 Unit Tests

```python
# tests/services/test_fire_service.py
import pytest
from app.services.fire_service import FireService

@pytest.mark.asyncio
async def test_get_fires_filters_by_province():
    service = FireService()
    result = await service.get_fires(province="Córdoba", page_size=10)
    
    assert result.total > 0
    assert all(fire.province == "Córdoba" for fire in result.items)
```

### 9.2 Integration Tests

```python
# tests/api/test_audit_endpoint.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_land_use_audit_returns_violations(client: AsyncClient):
    response = await client.post(
        "/api/v1/audit/land-use",
        json={"latitude": -31.4173, "longitude": -64.1833, "search_radius_meters": 5000},
        headers={"X-API-Key": "test-key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "is_violation" in data
    assert "fires_found" in data
```

---

## 10. Deployment

### Systemd Service

```ini
# /etc/systemd/system/forestguard-api.service
[Unit]
Description=ForestGuard FastAPI Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=forestguard
WorkingDirectory=/opt/forestguard
Environment="PATH=/opt/forestguard/venv/bin"
ExecStart=/opt/forestguard/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port XXXXX --workers 4

[Install]
WantedBy=multi-user.target
```

### Celery Worker Service

```ini
# /etc/systemd/system/forestguard-worker.service
[Unit]
Description=ForestGuard Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=forestguard
WorkingDirectory=/opt/forestguard
ExecStart=/opt/forestguard/venv/bin/celery -A app.workers.celery_app worker --loglevel=info --concurrency=2

[Install]
WantedBy=multi-user.target
```

---

**Documento generado**: Febrero 2026  
**Próxima actualización**: Post-consolidación de routers (34→17)
