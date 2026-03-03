## Contenedor `api` (`forestguard-api`)

Este servicio expone la API principal de Vestigia (ForestGuard) usando **FastAPI + Uvicorn**.

- **Servicio en Compose**: `api`
- **Nombre de contenedor**: `forestguard-api`
- **Archivo de definición**: `docker-compose.yml`
- **Imagen**: `ghcr.io/nicolasgh91/wildfire-recovery-argentina/api:latest`
- **Dockerfile**: `Dockerfile.api` (multi-stage sobre `Dockerfile.base`)

## Proceso y healthcheck

- **Proceso principal** (según `Dockerfile.api`):
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Puerto expuesto**:
  - Host: `8000` → contenedor: `8000`
- **Healthcheck** (`docker-compose.yml`):
  - `curl -f http://localhost:8000/health`

## Variables de entorno clave

Principales variables documentadas en `docker-compose.yml`:

- **Base de datos (Supabase/PostgreSQL + PostGIS)**:
  - `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- **Storage (backend activo: OCI)**:
  - `STORAGE_BACKEND` (por defecto `oci`)
  - `STORAGE_BUCKET_IMAGES`, `STORAGE_BUCKET_REPORTS`, `STORAGE_BUCKET_CERTIFICATES`
  - `STORAGE_PUBLIC_URL`
- **OCI Object Storage (S3-compatible)**:
  - `OCI_S3_ENDPOINT_URL`, `OCI_S3_ACCESS_KEY`, `OCI_S3_SECRET_KEY`
  - `OCI_REGION`, `OCI_PUBLIC_URL`
  - `OCI_CONFIG_FILE` (ruta del config de OCI dentro del contenedor)
- **Google Earth Engine (GEE)**:
  - `GEE_PROJECT_ID`
  - `GEE_SERVICE_ACCOUNT_EMAIL`
  - `GEE_PRIVATE_KEY_PATH` (normalmente `/run/secrets/gee-service-account.json`)
- **Celery / Redis**:
  - `CELERY_BROKER_URL` (`redis://redis:6379/0`)
  - `CELERY_RESULT_BACKEND` (`redis://redis:6379/1`)
- **Aplicación / entorno**:
  - `ENVIRONMENT` (por defecto `production`)
  - `DEBUG`
  - `SECRET_KEY`
- **Auth y Supabase**:
  - `API_KEY`
  - `ADMIN_API_KEY`
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`
  - `SUPABASE_JWT_SECRET`

## Volúmenes

- `./secrets` (o `GCP_CREDENTIALS_DIR`) → `/run/secrets:ro`  
  Contiene credenciales GCP/GEE.
- `~/.oci` → `/home/opc/.oci:ro`  
  Configuración de OCI para acceso a Object Storage.

## Funcionalidad de negocio (en alto nivel)

El contenedor `api` orquesta la lógica de negocio principal:

- **Gestión de incendios y episodios**:
  - Endpoints para listar, filtrar y detallar detecciones (`fire_events`) y episodios (`fire_episodes`).
- **Monitoreo de vegetación / VAE (UC-F12)**:
  - Endpoints que leen y exponen la información generada por los workers (`vegetation_monitoring`, métricas de recuperación y destrucción).
- **Carrusel satelital (UC-F08)**:
  - Endpoints que sirven el carrusel de eventos/episodios para la home del frontend.
- **Reportes y assets HD/PDF (UC-F11, UC-F10)**:
  - Endpoints para generar y descargar reportes de cierre, PDFs y assets de alta resolución.
- **Verificación de terreno / auditoría**:
  - Endpoints más avanzados ligados a verificación manual y auditoría.

Buena parte de esta lógica se implementa en servicios bajo `app/services/` como:

- `imagery_service` (imágenes satelitales, NDVI, etc.)
- `gee_service` (wrappers sobre GEE)
- `vae_service` (interfaz UC-F12 / VAE)

## Flujos de datos

### Entrada

- Requests HTTP desde:
  - `frontend` (`forestguard-frontend`) a través de `nginx`.
  - Clientes externos (API pública, según configuración de auth y despliegue).

### Salida

- **Respuestas HTTP (JSON)**:
  - Datos de incendios, episodios, métricas de vegetación, reportes, etc.
- **Base de datos**:
  - Escritura y actualización de:
    - Detecciones (`fire_events`)
    - Episodios (`fire_episodes`, tablas asociadas)
    - Monitoreo de vegetación (`vegetation_monitoring`)
    - Metadatos de reportes y assets.
- **Storage OCI**:
  - Lectura/escritura de:
    - Imágenes satelitales procesadas.
    - Reportes PDF.
    - Certificados.
- **Colas Celery (Redis)**:
  - Encolado de tareas hacia `worker-fast` y `worker-gee` para:
    - Ingesta FIRMS.
    - Clustering.
    - Generación de reportes y PDFs.
    - Análisis de recuperación y destrucción (UC-F12).
    - Actualización de carrousel y enriquecimiento geográfico.

## Relación con workers

El contenedor `api` **no ejecuta Celery**, pero:

- Usa `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` apuntando al servicio `redis`.
- Encola tareas definidas en:
  - `workers.tasks.ingestion`
  - `workers.tasks.clustering` / `clustering_task`
  - `workers.tasks.recovery` / `destruction`
  - `workers.tasks.carousel_task`
  - `workers.tasks.closure_report_task`
  - `workers.tasks.notification`
  - `workers.tasks.export_task`
  - `workers.tasks.pdf_generation_task`
  - `workers.tasks.cleanup_assets_task`
- Las colas son consumidas por:
  - `worker-fast` (tareas rápidas: ingesta, clustering, reports, notificaciones, default).
  - `worker-gee` (tareas GEE/VAE/analysis).

Para más detalle de mapping **cola → worker → tasks**, ver `docs/containers/workers.md` y `docs/backend/workers/workers_documentation.md`.

