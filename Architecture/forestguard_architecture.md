# 🏗️ Wildfire Recoveries in Argentina - Arquitectura del Sistema

## Resumen Ejecutivo

Wildfire Recoveries implementa una **arquitectura híbrida API+Workers** diseñada para:

1. **Respuestas rápidas** a consultas de usuarios (< 2 seg)
2. **Procesamiento pesado asíncrono** usando Google Earth Engine
3. **Escalabilidad horizontal** mediante workers independientes
4. **Costo operativo $0** utilizando capas gratuitas

---

## 📐 Diagrama de Arquitectura de Alto Nivel (Actualizado con GEE)

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIO FINAL                            │
│  (Escribanos, ONGs, Ciudadanos, Fiscales, Investigadores)       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE CDN                              │
│  - SSL/TLS Termination                                           │
│  - DDoS Protection                                               │
│  - Rate Limiting (100 req/min por IP)                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                NGINX REVERSE PROXY (Oracle Cloud)                │
│  - Load Balancing                                                │
│  - Static file serving                                           │
│  - Compression (gzip)                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌──────────────────┐    ┌──────────────────────┐
│   FASTAPI APP    │    │   STATIC FRONTEND    │
│   (Gunicorn +    │    │   (React + Leaflet)  │
│    Uvicorn)      │    │                      │
│                  │    │   - Dashboard        │
│  - REST API      │    │   - Formularios      │
│  - Auth/RBAC     │    │   - Mapas            │
│  - Validation    │    └──────────────────────┘
│  - Logging       │
│  - 🆕 Rate Limit │
└────────┬─────────┘
         │
         │ Read/Write
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              SUPABASE POSTGRESQL + POSTGIS                       │
│                                                                  │
│  Tables:                                                         │
│   - fire_detections (300k+ rows)                                │
│   - fire_events (10k+ rows)                                     │
│   - protected_areas (500+ rows)                                 │
│   - satellite_images (5k+ rows)                                 │
│   - climate_data (20k+ rows)                                    │
│   - land_certificates, citizen_reports, etc.                    │
│                                                                  │
│  Límite: 500MB storage                                          │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │
         │ Async Tasks
         │
┌────────┴─────────┐
│   REDIS BROKER   │
│   (Message Queue)│
│                  │
│  - Celery tasks  │
│  - Result backend│
└────────┬─────────┘
         │
         │ Pull Tasks
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CELERY WORKERS (x3)                           │
│                                                                  │
│  Worker 1: Ingestion Worker                                     │
│   - Download NASA FIRMS CSV bulk files                          │
│   - Parse and filter                                            │
│   - Insert into fire_detections                                 │
│   - Trigger clustering                                          │
│                                                                  │
│  Worker 2: Vegetation Analysis Engine (VAE) 🆕         │
│   - Query GEE ImageCollection (Sentinel-2)                      │
│   - Calculate NDVI server-side                                  │
│   - Detect Anomalies (Recovery vs Illegal Use)                  │
│   - Shared by UC-06 & UC-08                                     │
│   - NOTE: Uses separate queues (recovery_queue, destruction_queue) │
│          to prevent blocking between analyses                   │
│                                                                  │
│  Worker 3: Climate Worker                                       │
│   - Cluster fires spatially (H3 hexagons)                       │
│   - Query Open-Meteo API (batched)                              │
│   - Insert into climate_data                                    │
│   - Create fire_climate_associations                            │
└─────────────────────────────────────────────────────────────────┘
         │
         │ Store Results
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              CLOUDFLARE R2 OBJECT STORAGE                        │
│                                                                  │
│  Buckets:                                                        │
│   - wildfire-images/ (Thumbnails, visualizaciones)              │
│   - wildfire-reports/ (PDFs, ZIPs)                              │
│   - wildfire-certificates/ (Certificados legales)               │
│                                                                  │
│  Límite: 10GB storage                                           │
│  Egreso: ILIMITADO (costo $0)                                   │
└─────────────────────────────────────────────────────────────────┘
         ▲
         │
         │ Fetch External Data
         │
┌────────┴─────────────────────────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                          │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │   NASA FIRMS     │  │ 🆕 GOOGLE EARTH  │  │  Open-Meteo    │ │
│  │   (VIIRS/MODIS)  │  │     ENGINE       │  │  (ERA5-Land)   │ │
│  │                  │  │                  │  │                │ │
│  │  - Fire hotspots │  │  - Sentinel-2    │  │  - Temperature │ │
│  │  - 20 years data │  │  - NDVI          │  │  - Wind        │ │
│  │  - 375m resol.   │  │  - Server-side   │  │  - Drought idx │ │
│  │                  │  │    processing    │  │                │ │
│  │                  │  │  - FREE ilimitado│  │                │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                  │
│  🆕 Google Cloud Project: forest-guard-484400                    │
│     Service Account: gee-service-account@...iam.gserviceaccount.com │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Estructura de Directorios del Proyecto (Actualizada)

```
wildfire-recoveries/
│
├── app/                          # Código principal de la aplicación
│   ├── __init__.py
│   ├── main.py                   # ✅ Entry point FastAPI
│   │
│   ├── api/                      # Endpoints REST
│   │   ├── __init__.py
│   │   ├── deps.py               # ✅ Dependencias (DB sessions)
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── fires.py          # ✅ GET /fires, /fires/{id}
│   │       ├── audit.py          # ✅ UC-01: POST /audit/land-use
│   │       ├── reports.py        # UC-02: POST /reports/judicial
│   │       ├── certificates.py   # ✅ UC-07: POST /certificates/request
│   │       ├── monitoring.py     # UC-06: GET /monitoring/recovery
│   │       ├── citizen.py        # UC-09: POST /citizen/report
│   │       ├── historical.py     # UC-11: POST /reports/historical-fire
│   │       └── health.py         # GET /health
│   │
│   ├── core/                     # Configuración core
│   │   ├── __init__.py
│   │   ├── config.py             # ✅ Pydantic Settings (con GEE)
│   │   ├── security.py           # ✅ Auth, API keys (APIKeyHeader)
│   │   ├── rate_limiter.py       # ✅ IP Blocking + Email Alerts
│   │   ├── logging.py            # ✅ Structured logging
│   │   ├── errors.py             # ✅ Global Exception Handler
│   │   └── exceptions.py         # Custom exceptions
│   │
│   ├── models/                   # ✅ SQLAlchemy ORM Models
│   │   ├── __init__.py
│   │   ├── base.py               
│   │   ├── fire.py               # FireDetection, FireEvent
│   │   ├── region.py             # ProtectedArea, Intersections
│   │   ├── climate.py            # ClimateData
│   │   ├── evidence.py           # SatelliteImage, VegetationMonitoring
│   │   ├── audit.py              # LandUseAudit, LandCertificate
│   │   └── citizen.py            # CitizenReport, LandUseChange
│   │
│   ├── schemas/                  # ✅ Pydantic Models (Request/Response)
│   │   ├── __init__.py
│   │   ├── fire.py               # FireEventResponse
│   │   ├── audit.py              # LandUseAuditRequest/Response
│   │   ├── certificate.py        # CertificateRequest/Response
│   │   └── report.py             # JudicialReportRequest
│   │
│   ├── services/                 # Lógica de negocio
│   │   ├── __init__.py
│   │   ├── firms_service.py      # ✅ NASA FIRMS logic
│   │   ├── gee_service.py        # ✅ NUEVO: Google Earth Engine
│   │   ├── vae_service.py        # 🆕 Vegetation Analysis Engine (Shared)
│   │   │   # Core methods:
│   │   │   #  - fetch_ndvi_monthly(fire_event_id, date) -> NDVIResult
│   │   │   #  - detect_anomalies(ndvi_values) -> AnomalyType
│   │   ├── ers_service.py        # 🆕 Evidence Reporting Service (Shared)
│   │   │   # Core methods:
│   │   │   #  - aggregate_evidence(fire_event_id, date_range) -> Evidence
│   │   │   #  - generate_pdf(evidence, template) -> PDFFile
│   │   │   #  - create_verification_hash(pdf_bytes) -> str
│   │   ├── climate_service.py    # Open-Meteo API wrapper
│   │   ├── spatial_service.py    # PostGIS queries
│   │   ├── certificate_service.py # Generación certificados
│   │   └── pdf_composer.py       # Engine renderizado PDFs
│   │
│   └── db/                       # Database utilities
│       ├── __init__.py
│       ├── session.py            # ✅ SQLAlchemy session factory
│       └── base.py               
│
├── workers/                      # Celery workers
│   ├── __init__.py
│   ├── celery_app.py             # ✅ Celery configuration
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── ingestion.py          # ✅ download_firms_data
│   │   ├── clustering.py         # ✅ cluster_detections
│   │   ├── destruction.py        # 🆕 VAE: Check land use change (UC-08)
│   │   ├── recovery.py           # 🆕 VAE: Check reforestation (UC-06)
│   │   ├── imagery.py            # ✅ ACTUALIZADO: usa GEE
│   │   ├── climate.py            # enrich_with_climate
│   │   └── monitoring.py         # DEPRECATED: Merged into VAE
│   │
│   └── utils/
│       ├── __init__.py
│       ├── geo_utils.py          # H3 hexagons
│       └── retry.py              # Exponential backoff
│
├── scripts/                      # ✅ Scripts de carga de datos
│   ├── load_firms_history.py    # ✅ Carga NASA FIRMS
│   ├── load_protected_areas.py  # ✅ Carga shapefiles
│   ├── cluster_fire_events.py   # ✅ Clustering DBSCAN
│   ├── seed_test_data.py        # Datos de prueba
│   └── validate_data.py         # Checks de integridad
│
├── db/
│   ├── migrations/               # Alembic migrations
│   │   ├── env.py
│   │   ├── versions/
│   │   └── script.py.mako
│   │
│   └── schema_v3_final.sql       # ✅ Schema completo
│
├── tests/                        # Tests
│   ├── __init__.py
│   ├── conftest.py               
│   │
│   ├── unit/                     
│   │   ├── test_services/
│   │   └── test_models/
│   │
│   ├── integration/              
│   │   ├── test_api/
│   │   └── test_workers/
│   │
│   └── e2e/                      
│       └── test_full_audit_flow.py
│
├── docs/                         # ✅ Documentación
│   ├── USE_CASES.md              # ✅ Casos de uso completos
│   ├── ARCHITECTURE.md           # ✅ Este archivo
│   ├── TEST_CASES.md             # ✅ Casos de prueba
│   ├── BRANDING_GUIDE.md         # ✅ Guía de branding
│   ├── SCRIPTS_README.md         # ✅ Guía de scripts
│   └── API_REFERENCE.md          # OpenAPI spec
│
├── docker/                       # ✅ Dockerfiles
│   ├── Dockerfile.api            # ✅ FastAPI image
│   ├── Dockerfile.worker         # ✅ Celery worker
│   └── nginx.conf                # ✅ Nginx config
│
├── .github/
│   └── workflows/
│       └── ci.yml                # GitHub Actions CI/CD
│
├── gee-service-account.json      # 🆕 GEE credentials (NO COMMITEAR)
├── .env                          # ✅ Variables de entorno (NO COMMITEAR)
├── .env.example                  # ✅ Template
├── .gitignore                    # ✅
├── .dockerignore                 # ✅
├── docker-compose.yml            # ✅ Orquestación local
├── docker-compose.prod.yml       # Orquestación producción
├── alembic.ini                   # ✅ Config migraciones
├── Makefile                      # ✅ Comandos simplificados
├── pyproject.toml                # ✅ Poetry dependencies
├── requirements.txt              # ✅ Pip dependencies (con earthengine-api)
├── README.md                     # ✅ Documentación principal
├── CONTRIBUTING.md               # Guía de contribución
├── LICENSE                       # MIT License
└── CHANGELOG.md                  # Historial de versiones
```

---

## 🔄 Flujo de Datos: UC-01 Auditoría con GEE

**Ejemplo:** Un escribano verifica si un terreno en `-27.4658, -58.8346` está prohibido.

```
1. REQUEST → API
   ┌────────────────────────────────────────────────┐
   │ POST /api/v1/audit/land-use                    │
   │ Body: {                                        │
   │   "latitude": -27.4658,                        │
   │   "longitude": -58.8346,                       │
   │   "radius_meters": 500                         │
   │ }                                              │
   └────────────────┬───────────────────────────────┘
                    │
2. NGINX → FASTAPI
                    │
                    ▼
3. FASTAPI VALIDA REQUEST
   ┌────────────────────────────────────────────────┐
   │ app/api/routes/audit.py                        │
   │ - Validate lat/lon                             │
   │ - Create LandUseAudit log                      │
   │ → Call spatial queries                         │
   └────────────────┬───────────────────────────────┘
                    │
4. POSTGIS SPATIAL QUERY
   ┌────────────────────────────────────────────────┐
   │ SELECT fe.*, pa.official_name                  │
   │ FROM fire_events fe                            │
   │ LEFT JOIN fire_protected_area_intersections    │
   │ WHERE ST_DWithin(                              │
   │   fe.centroid,                                 │
   │   ST_MakePoint(-58.8346, -27.4658),            │
   │   500                                          │
   │ )                                              │
   │ → Returns: 2 fire events                       │
   └────────────────┬───────────────────────────────┘
                    │
5. FETCH EVIDENCE
   ┌────────────────────────────────────────────────┐
   │ For each fire:                                 │
   │  - Get satellite_images (R2 URLs)              │
   │  - Get climate_data                            │
   │  - Calculate prohibition_until                 │
   └────────────────┬───────────────────────────────┘
                    │
6. RESPONSE
   ┌────────────────────────────────────────────────┐
   │ {                                              │
   │   "fires_found": 2,                            │
   │   "is_prohibited": true,                       │
   │   "prohibition_until": "2075-08-22",           │
   │   "fires": [...]                               │
   │ }                                              │
   └────────────────────────────────────────────────┘

Tiempo: < 2 segundos
```

---

## 🛰️ Flujo Asíncrono: Descarga de Imágenes con GEE

**Trigger:** Nuevo fire_event creado sin imágenes

```
1. TRIGGER (Celery Beat Scheduler)
   ┌────────────────────────────────────────────────┐
   │ SELECT id FROM fire_events                     │
   │ WHERE has_satellite_imagery = FALSE            │
   │ → fire_event_id = "uuid-456"                   │
   └────────────────┬───────────────────────────────┘
                    │
2. ENQUEUE TASK
   ┌────────────────────────────────────────────────┐
   │ download_fire_imagery.delay(                   │
   │   fire_event_id="uuid-456"                     │
   │ )                                              │
   │ → Redis queue                                  │
   └────────────────┬───────────────────────────────┘
                    │
3. WORKER TAKES TASK
   ┌────────────────────────────────────────────────┐
   │ Celery Worker 2 (Imagery)                      │
   │ @celery_app.task                               │
   │ def download_fire_imagery(fire_id):            │
   └────────────────┬───────────────────────────────┘
                    │
4. 🆕 GOOGLE EARTH ENGINE QUERY
   ┌────────────────────────────────────────────────┐
   │ gee = GEEService()                             │
   │                                                │
   │ # Buscar imágenes Sentinel-2 L2A               │
   │ collection = ee.ImageCollection(               │
   │   'COPERNICUS/S2_SR_HARMONIZED'                │
   │ )                                              │
   │ .filterBounds(fire_area)                       │
   │ .filterDate(fire_date - 30, fire_date + 30)    │
   │ .filter(ee.Filter.lt(                          │
   │   'CLOUDY_PIXEL_PERCENTAGE', 20                │
   │ ))                                             │
   │                                                │
   │ # Obtener mejor imagen (menos nubes)           │
   │ image = collection.sort(                       │
   │   'CLOUDY_PIXEL_PERCENTAGE'                    │
   │ ).first()                                      │
   │                                                │
   │ → Imagen encontrada: 12% nubes                 │
   └────────────────┬───────────────────────────────┘
                    │
5. 🆕 CALCULAR NDVI (SERVER-SIDE en GEE)
   ┌────────────────────────────────────────────────┐
   │ # Calcular NDVI en GEE (NO descargar imagen)   │
   │ nir = image.select('B8')                       │
   │ red = image.select('B4')                       │
   │ ndvi = nir.subtract(red).divide(               │
   │   nir.add(red)                                 │
   │ ).rename('NDVI')                               │
   │                                                │
   │ # Estadísticas sobre el área                   │
   │ stats = ndvi.reduceRegion(                     │
   │   reducer=ee.Reducer.mean(),                   │
   │   geometry=fire_area,                          │
   │   scale=10                                     │
   │ )                                              │
   │                                                │
   │ ndvi_mean = 0.72 ← Calculado en GEE            │
   └────────────────┬───────────────────────────────┘
                    │
6. 🆕 GENERAR URL DE VISUALIZACIÓN
   ┌────────────────────────────────────────────────┐
   │ # Crear RGB para visualización                 │
   │ rgb = image.select(['B4', 'B3', 'B2'])         │
   │                                                │
   │ # Obtener URL de descarga (solo thumbnail)     │
   │ url = rgb.getDownloadURL({                     │
   │   'region': fire_bbox,                         │
   │   'scale': 20,  # 20m (más liviano)            │
   │   'format': 'PNG'                              │
   │ })                                             │
   │                                                │
   │ → URL temporal de GEE                          │
   └────────────────┬───────────────────────────────┘
                    │
7. DOWNLOAD THUMBNAIL & UPLOAD TO R2
   ┌────────────────────────────────────────────────┐
   │ # Descargar thumbnail pequeño de GEE           │
   │ response = requests.get(url)                   │
   │ # Size: ~500KB (vs 700MB imagen completa!)     │
   │                                                │
   │ # Subir a Cloudflare R2                        │
   │ s3_client.put_object(                          │
   │   Bucket='wildfire-images',                    │
   │   Key=f'fires/{fire_id}/post_fire.png',        │
   │   Body=response.content                        │
   │ )                                              │
   │                                                │
   │ r2_url = "https://r2.../post_fire.png"         │
   └────────────────┬───────────────────────────────┘
                    │
8. UPDATE DATABASE
   ┌────────────────────────────────────────────────┐
   │ satellite_image = SatelliteImage(              │
   │   fire_event_id=fire_id,                       │
   │   satellite='Sentinel-2',                      │
   │   acquisition_date=image_date,                 │
   │   cloud_cover_pct=12.0,                        │
   │   r2_url=r2_url,                               │
   │   file_size_mb=0.5  # Solo thumbnail!          │
   │ )                                              │
   │                                                │
   │ fire_event.has_satellite_imagery = TRUE        │
   │ db.commit()                                    │
   └────────────────────────────────────────────────┘

Tiempo: 30-60 segundos
Ventaja GEE: No descarga 700MB, solo 500KB thumbnail!
```

---

## 🔐 Seguridad y Autenticación

### Modelo de Seguridad

**Niveles de Acceso:**

1. **Público (No autenticado)**
   - ✅ GET /fires (lista pública)
   - ✅ GET /certificates/verify/{number}
   - ❌ POST /audit/land-use
   - ❌ POST /certificates/request

2. **Usuario Registrado (API Key)**
   - ✅ Todo lo público
   - ✅ POST /audit/land-use (10/mes)
   - ✅ POST /certificates/request (10/mes)
   - ✅ POST /citizen/report

3. **Administrador**
   - ✅ Todo lo anterior
   - ✅ Revisar denuncias ciudadanas
   - ✅ Acceso a métricas

### 🔒 Nuevos Controles de Seguridad (v3.1)
- **API Key**: Header `X-API-Key` obligatorio para endpoints sensibles.
- **IP Rate Limiting**:
  - Límite: 10 requests/día por IP (para endpoints protegidos).
  - Acción: Bloqueo automático + Alerta Email al Admin.
- **Error Handling**:
  - Dev (DEBUG=True): Stack traces visibles.
  - Prod (DEBUG=False): Mensaje genérico "Internal Server Error".

---

## 🚨 Error Handling Strategy

### Retry Policies
- **API Layer**: Exponential backoff for external API calls (GEE, Open-Meteo)
  - Max retries: 3 attempts
  - Backoff: 1s, 2s, 4s
- **Celery Tasks**: Automatic retry with configurable delays
  ```python
  @task(bind=True, max_retries=3, default_retry_delay=60)
  def process_imagery(self, fire_id):
      try:
          # processing logic
      except TemporaryError as exc:
          raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
  ```

### Dead Letter Queue
Failed tasks after max retries are logged to `failed_tasks` table:
- Task name, arguments, error traceback
- Retry count and final failure timestamp
- Manual reprocessing capability via admin dashboard

### Alerting
- **Critical Failures**: Webhook to Discord/Slack
  - Database connection loss
  - GEE authentication failure
  - R2 storage unavailable
- **Warning Threshold**: Queue depth > 1000 tasks

---

## 🔐 Security Notes

### GEE Service Account
**⚠️ CRITICAL**: Service account credentials (`gee-service-account.json`) must be secured:
- **Development**: Store in `/secrets/` directory (outside project root)
- **Production**: Use environment variable `GEE_SERVICE_ACCOUNT_JSON` (base64 encoded)
- **Never commit** credentials to version control
- **Rotate keys** every 90 days

### API Rate Limiting
- **Per IP**: 100 requests/minute (Cloudflare)
- **Authenticated Users**: 500 requests/minute
- **Admin Users**: Unlimited

---

## 📈 Observability & Monitoring

### Metrics (Prometheus)
```yaml
# Key metrics to track
- api_request_duration_seconds (histogram)
- celery_queue_depth (gauge)
- database_connection_pool_size (gauge)
- gee_api_calls_total (counter)
- r2_upload_bytes_total (counter)
```

### Logging Strategy
- **Format**: Structured JSON logs
- **Levels**:
  - INFO: API requests, task completions
  - WARNING: Retry attempts, high queue depth
  - ERROR: Task failures, API errors
- **Destination**: CloudWatch Logs / Loki
- **Retention**: 30 days

### Distributed Tracing
- **Tool**: OpenTelemetry (optional for production)
- **Spans**: Track request → worker → GEE → database round-trip

---

## ⚖️ Resource Limits & Quotas

### Google Earth Engine
**⚠️ Important**: Despite "FREE ilimitado" label, GEE has quotas:
- **Requests**: 50,000/day (free tier)
- **Compute**: 10 concurrent operations
- **Implementation**: Rate limiter in `gee_service.py`:
  ```python
  # Max 1 request per second to stay under daily limit
  @sleep_and_retry
  @limits(calls=1, period=1)
  def fetch_sentinel_image(...):
      ...
  ```

### Supabase PostgreSQL
- **Storage**: 500MB (free tier)
- **Connections**: 60 concurrent
- **Monitoring**: Alert when storage > 80%

### Cloudflare R2
- **Storage**: 10GB (free tier)
- **Requests**: Unlimited (no egress fees)

---

## 🏥 Health Check Implementation

### Endpoint: `GET /health`
Checks all critical dependencies:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-28T14:45:00Z",
  "version": "3.0.0",
  "components": {
    "database": {
      "status": "up",
      "response_time_ms": 12
    },
    "redis": {
      "status": "up",
      "response_time_ms": 3
    },
    "gee": {
      "status": "authenticated",
      "last_check": "2025-01-28T14:40:00Z"
    },
    "r2": {
      "status": "accessible",
      "bucket": "wildfire-images"
    }
  }
}
```

**Status Codes**:
- `200`: All services healthy
- `503`: At least one service degraded

---

## 🔄 API Versioning Strategy

### Current Version: v1
- **Base Path**: `/api/v1/*`
- **Compatibility**: Backward compatible for minor changes

### Deprecation Policy
1. **Announce**: 90 days before deprecation (via API headers)
   ```
   Deprecation: version="2026-04-30"
   Link: <https://docs.forestguard.ar/migration-guide>; rel="deprecation"
   ```
2. **Sunset**: Remove deprecated endpoints 180 days after announcement
3. **Version Support**: Maintain N-1 versions (e.g., v1 + v2 simultaneously)

### Breaking Changes
Require new major version (e.g., `/api/v2/`):
- Response schema changes (removing fields)
- Authentication method changes
- Endpoint URL changes

---

## 📊 Métricas de Performance

| Endpoint | P50 Latency | P95 Latency | P99 Latency |
|----------|-------------|-------------|-------------|
| `GET /fires` | 150ms | 400ms | 800ms |
| `POST /audit/land-use` | 800ms | 1.8s | 3.5s |
| `POST /certificates/request` | 1.2s | 2.5s | 4.0s |
| `GET /health` | 10ms | 20ms | 50ms |

**Worker Performance:**
- Descarga FIRMS (10k records): ~10 min
- Clustering (1 day): ~30 sec
- Imagen GEE (1 fire): ~45 sec

---

## 🌐 Producción

### Estado Actual
- **Status**: ✅ LIVE EN PRODUCCIÓN
- **URL Pública**: https://forestguard.freedynamicdns.org
- **API Docs**: https://forestguard.freedynamicdns.org/docs
- **Health Check**: https://forestguard.freedynamicdns.org/health

### Infraestructura

**Provider**: Oracle Cloud (Always Free Tier)  
**Ubicación**: São Paulo (GRU)  
**VM Shape**: Ampere A1 Compute (ARM64)  
**Recursos**:  
- 1 OCPU (Ampere CPU core)
- 6 GB RAM
- 50 GB Boot Volume
- 10 TB Outbound Traffic/month (free)

**Stack de Producción**:
```
Internet
  │
  │ HTTPS (443)
  │ SSL: Let's Encrypt (auto-renewal)
  ↓
FreeDynamicDNS
  │
  ↓
Nginx (Reverse Proxy)
  │
  │ Proxy pass to :8000
  ↓
Gunicorn + Uvicorn Workers
  │
  │ 4 workers (FastAPI)
  ↓
Supabase PostgreSQL (External)
  │
  │ PostGIS queries
Cloudflare R2 (External)
```

### Monitoreo
- **Process Manager**: systemd
- **Logs**: journalctl -u forestguard -f
- **Uptime Monitoring**: Manual (planned: UptimeRobot)
- **Performance**: Nginx access logs
- **Docker Log Rotation**: Configured to prevent disk exhaustion (max-size: 10m, max-file: 3)

### Deployment Pipeline
```bash
# Actualizar código
cd /opt/forestguard
git pull origin main

# Reiniciar servicio
sudo systemctl restart forestguard

# Verificar status
sudo systemctl status forestguard
curl https://forestguard.freedynamicdns.org/health
```

---

## 📋 Checklist de Implementación Completa

- [x] Schema PostgreSQL v3.0
- [x] Modelos SQLAlchemy
- [x] Scripts de carga de datos
- [x] Configuración (config.py, .env)
- [x] Docker Compose
- [x] Makefile
- [x] **Integración Google Earth Engine**
- [x] **Endpoints FastAPI (fires, audit, certificates)**
- [ ] Endpoints faltantes (reports, monitoring, citizen)
- [ ] Tests unitarios
- [ ] Tests de integración
- [ ] Frontend (React + Leaflet)
- [ ] CI/CD (GitHub Actions)
- [ ] Documentación API (OpenAPI)
- [ ] Deploy a producción

**Progreso:** 80% completado 🎉

---

**Última actualización:** 2025-01-24  
**Versión:** 3.0  
**Status:** ✅ En Desarrollo Activo (Endpoints Core Implementados)