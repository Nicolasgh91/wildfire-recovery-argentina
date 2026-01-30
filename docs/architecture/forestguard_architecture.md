# 🏗️ Wildfire Recoveries in Argentina - System Architecture

## Executive summary

Wildfire Recoveries implements a **hybrid API+Workers architecture** designed for:

1. **Fast responses** to user queries (< 2 sec)
2. **Heavy asynchronous processing** using Google Earth Engine
3. **Horizontal scalability** via independent workers
4. **$0 operating cost** using free tiers

---

## 📐 High-level architecture diagram (updated with GEE)
```
┌─────────────────────────────────────────────────────────────────┐
│                           END USER                              │
│  (Notaries, NGOs, Citizens, Prosecutors, Researchers)           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUDFLARE CDN                              │
│  - SSL/TLS Termination                                           │
│  - DDoS Protection                                               │
│  - Rate Limiting (100 req/min per IP)                           │
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
│  - REST API      │    │   - Forms            │
│  - Auth/RBAC     │    │   - Maps             │
│  - Validation    │    └──────────────────────┘
│  - Logging       │
│  - 🆕 Rate Limit │
│  - 🆕 Idempotency│
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
│  Limit: 500MB storage                                           │
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
│   - wildfire-images/ (Thumbnails, visualizations)               │
│   - wildfire-reports/ (PDFs, ZIPs)                              │
│   - wildfire-certificates/ (Legal certificates)                 │
│                                                                  │
│  Limit: 10GB storage                                            │
│  Egress: UNLIMITED ($0 cost)                                    │
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
│  │                  │  │  - FREE unlim.   │  │                │ │
│  └──────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                  │
│  🆕 Google Cloud Project: forest-guard-484400                    │
│     Service Account: gee-service-account@...iam.gserviceaccount.com │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ Project directory structure (updated)

```
wildfire-recoveries/
│
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # ✅ FastAPI Entry point
│   │
│   ├── api/                      # REST Endpoints
│   │   ├── __init__.py
│   │   ├── deps.py               # ✅ Dependencies (DB sessions)
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
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py             # ✅ Pydantic Settings (with GEE)
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
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── firms_service.py      # ✅ NASA FIRMS logic
│   │   ├── gee_service.py        # ✅ NEW: Google Earth Engine
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
│   │   ├── certificate_service.py # Certificate generation
│   │   └── pdf_composer.py       # PDF rendering engine
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
│   │   ├── imagery.py            # ✅ UPDATED: uses GEE
│   │   ├── climate.py            # enrich_with_climate
│   │   └── monitoring.py         # DEPRECATED: Merged into VAE
│   │
│   └── utils/
│       ├── __init__.py
│       ├── geo_utils.py          # H3 hexagons
│       └── retry.py              # Exponential backoff
│
├── scripts/                      # ✅ Data loading scripts
│   ├── load_firms_history.py    # ✅ Load NASA FIRMS
│   ├── load_protected_areas.py  # ✅ Load shapefiles
│   ├── cluster_fire_events.py   # ✅ DBSCAN Clustering
│   ├── seed_test_data.py        # Test data
│   └── validate_data.py         # Integrity checks
│
├── db/
│   ├── migrations/               # Alembic migrations
│   │   ├── env.py
│   │   ├── versions/
│   │   └── script.py.mako
│   │
│   └── schema_v3_final.sql       # ✅ Full Schema
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
├── docs/                         # ✅ Documentation
│   ├── architecture/             # 🆕 Architecture subfolder
│   │   ├── forestguard_use_cases.md # ✅ Full Use Cases
│   │   ├── forestguard_architecture.md # ✅ This file
│   │   ├── project_plan.md       # ✅ Plan
│   │   └── wildfire_branding.md  # ✅ Branding Guide
│   ├── manual_de_usuario.md      # ✅ User Guide
│   └── ...                       # ✅ Other docs
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
├── gee-service-account.json      # 🆕 GEE credentials (DO NOT COMMIT)
├── .env                          # ✅ Env variables (DO NOT COMMIT)
├── .env.example                  # ✅ Template
├── .gitignore                    # ✅
├── .dockerignore                 # ✅
├── docker-compose.yml            # ✅ Local orchestration
├── docker-compose.prod.yml       # Production orchestration
├── alembic.ini                   # ✅ Migrations config
├── Makefile                      # ✅ Simplified commands
├── pyproject.toml                # ✅ Poetry dependencies
├── requirements.txt              # ✅ Pip dependencies (with earthengine-api)
├── README.md                     # ✅ Main documentation
├── CONTRIBUTING.md               # Contribution guide
├── LICENSE                       # MIT License
└── CHANGELOG.md                  # Version history
```

---

## 🔄 Data flow: UC-01 Audit with GEE

**Example:** A notary verifies if a plot at `-27.4658, -58.8346` is prohibited.

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
3. FASTAPI VALIDATES REQUEST
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

Time: < 2 seconds
```

---

## 🛰️ Async flow: Image download with GEE

**Trigger:** New fire_event created without images

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
   │ # Search Sentinel-2 L2A images                 │
   │ collection = ee.ImageCollection(               │
   │   'COPERNICUS/S2_SR_HARMONIZED'                │
   │ )                                              │
   │ .filterBounds(fire_area)                       │
   │ .filterDate(fire_date - 30, fire_date + 30)    │
   │ .filter(ee.Filter.lt(                          │
   │   'CLOUDY_PIXEL_PERCENTAGE', 20                │
   │ ))                                             │
   │                                                │
   │ # Get best image (least clouds)                │
   │ image = collection.sort(                       │
   │   'CLOUDY_PIXEL_PERCENTAGE'                    │
   │ ).first()                                      │
   │                                                │
   │ → Image found: 12% clouds                      │
   └────────────────┬───────────────────────────────┘
                    │
5. 🆕 CALCULATE NDVI (SERVER-SIDE IN GEE)
   ┌────────────────────────────────────────────────┐
   │ # Calculate NDVI in GEE (DO NOT download img)  │
   │ nir = image.select('B8')                       │
   │ red = image.select('B4')                       │
   │ ndvi = nir.subtract(red).divide(               │
   │   nir.add(red)                                 │
   │ ).rename('NDVI')                               │
   │                                                │
   │ # Statistics over the area                     │
   │ stats = ndvi.reduceRegion(                     │
   │   reducer=ee.Reducer.mean(),                   │
   │   geometry=fire_area,                          │
   │   scale=10                                     │
   │ )                                              │
   │                                                │
   │ ndvi_mean = 0.72 ← Calculated in GEE           │
   └────────────────┬───────────────────────────────┘
                    │
6. 🆕 GENERATE VISUALIZATION URL
   ┌────────────────────────────────────────────────┐
   │ # Create RGB for visualization                 │
   │ rgb = image.select(['B4', 'B3', 'B2'])         │
   │                                                │
   │ # Get download URL (thumbnail only)            │
   │ url = rgb.getDownloadURL({                     │
   │   'region': fire_bbox,                         │
   │   'scale': 20,  # 20m (lighter)                │
   │   'format': 'PNG'                              │
   │ })                                             │
   │                                                │
   │ → Temporary GEE URL                            │
   └────────────────┬───────────────────────────────┘
                    │
7. DOWNLOAD THUMBNAIL & UPLOAD TO R2
   ┌────────────────────────────────────────────────┐
   │ # Download small thumbnail from GEE            │
   │ response = requests.get(url)                   │
   │ # Size: ~500KB (vs 700MB full image!)          │
   │                                                │
   │ # Upload to Cloudflare R2                      │
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
   │   file_size_mb=0.5  # Only thumbnail!          │
   │ )                                              │
   │                                                │
   │ fire_event.has_satellite_imagery = TRUE        │
   │ db.commit()                                    │
   └────────────────────────────────────────────────┘

Time: 30-60 seconds
GEE Advantage: Does not download 700MB, only 500KB thumbnail!
```

---

## 🔐 Security and authentication

### Security model

**Access Levels:**

1. **Public (Unauthenticated)**
   - ✅ GET /fires (public list)
   - ✅ GET /certificates/verify/{number}
   - ❌ POST /audit/land-use
   - ❌ POST /certificates/request

2. **Registered User (API Key)**
   - ✅ All public
   - ✅ POST /audit/land-use (10/month)
   - ✅ POST /certificates/request (10/month)
   - ✅ POST /citizen/report

3. **Administrator**
   - ✅ All of the above
   - ✅ Review citizen reports
   - ✅ Access metrics

### 🔒 Security Controls (v3.2)
- **RBAC (Role Based Access Control)**:
  - **Admin**: Full access (`X-API-Key` matching `ADMIN_API_KEY`).
  - **User**: Protected access (`X-API-Key` matching `API_KEY`).
  - **Public**: Limited access to open endpoints.
- **Smart Rate Limiting**:
  - **Authenticated (User)**: 1000 requests/day per Key.
  - **Anonymous (IP)**: 10 requests/day per IP.
  - **Admin**: Unlimited.
- **Secret Scanning**:
  - CI pipeline (`.github/workflows/security.yml`) scans for leaked credentials using Gitleaks.
- **Error Handling**:
  - Prod (DEBUG=False): Generic "Internal Server Error" message.
- **Audit Logging**:
  - Centralized `audit_events` table (Append-Only) for critical actions.
  - Integration: `AuditLogger` tracks report submissions access.
- **Row Level Security (RLS)**:
  - Standardized policies (`audit_and_rls.sql`):
    - `audit_events`: Admin Read Only.
    - `fire_events`: Public Read / Admin Write.

---

## 🔄 Idempotency

To prevent duplicate resource creation (e.g., certificates, reports) during retries or network timeouts, critical `POST` endpoints support **idempotency keys**.

- **Mechanism**: Client sends `X-Idempotency-Key` header (UUID).
- **Behavior**:
  - **First Request**: Server processes request, saves response to DB, returns 200/201.
  - **Retry (same key)**: Server returns cached response *immediately* without re-processing.
  - **Conflict**: If same key is used with *different* body, returns `409 Conflict`.
- **TTL**: Keys expire after **24 hours**.

**Protected Endpoints:**
- `POST /api/v1/certificates/issue`
- `POST /api/v1/reports/judicial`
- `POST /api/v1/reports/historical`

---

## 🚨 Error handling strategy

### Retry policies
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

### Dead letter queue
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

## 🔐 Security notes

### GEE service account
**⚠️ CRITICAL**: Service account credentials (`gee-service-account.json`) must be secured:
- **Development**: Store in `/secrets/` directory (outside project root)
- **Production**: Use environment variable `GEE_SERVICE_ACCOUNT_JSON` (base64 encoded)
- **Never commit** credentials to version control
- **Rotate keys** every 90 days

### API rate limiting
- **Anonymous/IP**: 10 requests/day (Strict limit for public/scraping protection)
- **Authenticated Users**: 1000 requests/day (High limit for legitimate use)
- **Admin Users**: Unlimited

---

## 📈 Observability & monitoring

### Metrics (Prometheus)
```yaml
# Key metrics to track
- api_request_duration_seconds (histogram)
- celery_queue_depth (gauge)
- database_connection_pool_size (gauge)
- gee_api_calls_total (counter)
- r2_upload_bytes_total (counter)
```

### Logging strategy
- **Format**: Structured JSON logs
- **Levels**:
  - INFO: API requests, task completions
  - WARNING: Retry attempts, high queue depth
  - ERROR: Task failures, API errors
- **Destination**: CloudWatch Logs / Loki
- **Retention**: 30 days

### Distributed tracing
- **Tool**: OpenTelemetry (optional for production)
- **Spans**: Track request → worker → GEE → database round-trip

---

## ⚖️ Resource limits & quotas

### Google Earth Engine
**⚠️ Important**: Despite "FREE unlimited" label, GEE has quotas:
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

## 🏥 Health check implementation

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

**Status codes**:
- `200`: All services healthy
- `503`: At least one service degraded

---

## 🔄 API versioning strategy

### Current version: v1
- **Base Path**: `/api/v1/*`
- **Compatibility**: Backward compatible for minor changes

### Deprecation policy
1. **Announce**: 90 days before deprecation (via API headers)
   ```
   Deprecation: version="2026-04-30"
   Link: <https://docs.forestguard.ar/migration-guide>; rel="deprecation"
   ```
2. **Sunset**: Remove deprecated endpoints 180 days after announcement
3. **Version Support**: Maintain N-1 versions (e.g., v1 + v2 simultaneously)

### Breaking changes
Require new major version (e.g., `/api/v2/`):
- Response schema changes (removing fields)
- Authentication method changes
- Endpoint URL changes

---

## 📊 Performance metrics & SLOs

**Enforced SLOs (Middleware checks):**
- **Listing Fires**: < 400ms
- **Health Check**: < 200ms
- **Audit Analysis**: < 1.5s

| Endpoint | P50 Latency | P95 Latency | P99 Latency |
|----------|-------------|-------------|-------------|
| `GET /fires` | 150ms | 400ms | 800ms |
| `POST /audit/land-use` | 800ms | 1.8s | 3.5s |
| `POST /certificates/request` | 1.2s | 2.5s | 4.0s |
| `GET /health` | 10ms | 20ms | 50ms |

**Worker performance:**
- FIRMS Download (10k records): ~10 min
- Clustering (1 day): ~30 sec
- GEE Image (1 fire): ~45 sec

---

## 🌐 Production

### Current status
- **Status**: ✅ LIVE IN PRODUCTION
- **Public URL**: https://forestguard.freedynamicdns.org
- **API Docs**: https://forestguard.freedynamicdns.org/docs
- **Health Check**: https://forestguard.freedynamicdns.org/health

### Infrastructure

**Provider**: Oracle Cloud (Always Free Tier)  
**Location**: São Paulo (GRU)  
**VM Shape**: Ampere A1 Compute (ARM64)  
**Resources**:  
- 1 OCPU (Ampere CPU core)
- 6 GB RAM
- 50 GB Boot Volume
- 10 TB Outbound Traffic/month (free)

**Production stack**:
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

### Monitoring
- **Process Manager**: systemd
- **Logs**: journalctl -u forestguard -f
- **Uptime Monitoring**: Manual (planned: UptimeRobot)
- **Performance**: Nginx access logs
- **Docker Log Rotation**: Configured to prevent disk exhaustion (max-size: 10m, max-file: 3)

### Deployment pipeline
```bash
# Update code
cd /opt/forestguard
git pull origin main

# Restart service
sudo systemctl restart forestguard

# Verify status
sudo systemctl status forestguard
curl https://forestguard.freedynamicdns.org/health
```

---

## 📋 Full implementation checklist

- [x] Schema PostgreSQL v3.0
- [x] SQLAlchemy Models
- [x] Data loading scripts
- [x] Configuration (config.py, .env)
- [x] Docker Compose
- [x] Makefile
- [x] **Google Earth Engine Integration**
- [x] **FastAPI Endpoints (fires, audit, certificates, citizen)**
- [x] Missing endpoints (reports, monitoring)
- [x] Unit tests (Security, Deprecation)
- [x] Integration tests (Regression)
- [ ] Frontend (React + Leaflet)
- [x] CI/CD (GitHub Actions)
- [x] API Documentation (OpenAPI)
- [x] **Idempotency Implementation**
- [ ] Deploy to production

**Progress:** 82% completed 🎉

---

**Last updated:** 2026-01-29  
**Version:** 3.0  
**Status:** ✅ Active Development (Core Endpoints Implemented)
