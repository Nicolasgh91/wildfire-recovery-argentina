## Contenedores de workers y scheduler

Este documento describe los contenedores que ejecutan **Celery** y cómo se mapean las colas a cada worker.

Archivos clave:

- Configuración Celery: `workers/celery_app.py`
- Documentación de tasks: `docs/backend/workers/workers_documentation.md`
- Orquestación contenedores: `docker-compose.yml`

## Resumen de contenedores

| Contenedor              | Servicio Compose | Colas principales                          | Uso principal                                     |
|-------------------------|------------------|--------------------------------------------|--------------------------------------------------|
| `forestguard-worker-fast` | `worker-fast`   | `ingestion`, `clustering`, `reports`, `notification`, `default` | Tareas rápidas y de IO moderado                  |
| `forestguard-worker-gee`  | `worker-gee`    | `analysis`, `vae`, `gee` (via routing)     | Tareas GEE/VAE y análisis intensivo              |
| `forestguard-celery-beat` | `celery-beat`   | (no consume colas, las agenda)             | Scheduler de tareas periódicas                   |
| `forestguard-flower`      | `flower`        | (lee metadatos de todas las colas)         | Dashboard de monitorización Celery (profile debug) |

> Nota: la topología actual **consolida workers legacy** (`worker-ingestion`, `worker-clustering`, `worker-analysis`, `worker-reports`, `worker-vae`) en **dos contenedores**: `worker-fast` y `worker-gee`.

## `worker-fast` (`forestguard-worker-fast`)

- **Servicio Compose**: `worker-fast`
- **Imagen**: `ghcr.io/nicolasgh91/wildfire-recovery-argentina/worker:latest`
- **Dockerfile**: `Dockerfile.worker` (basado en `Dockerfile.base`)
- **Comando** (`docker-compose.yml`):
  - `celery -A workers.celery_app worker --loglevel=info --queues=ingestion,clustering,reports,notification,default --concurrency=1 --max-tasks-per-child=200`
- **Colas consumidas**:
  - `ingestion`
  - `clustering`
  - `reports`
  - `notification`
  - `default`

### Tareas típicas en `worker-fast`

Basado en `workers/celery_app.py` y `docs/backend/workers/workers_documentation.md`:

- **Ingesta de datos FIRMS**:
  - `workers.tasks.ingestion.download_firms_daily` → cola `ingestion`
  - Fuente: NASA FIRMS (API + CSV), salida: tablas de detecciones/incendios.
- **Clustering de detecciones y episodios**:
  - `workers.tasks.clustering.cluster_detections` → cola `clustering`
  - `workers.tasks.clustering_task.cluster_fire_episodes_pipeline` → cola `clustering`
  - Salida: grupos de detecciones (`fire_events`) y episodios (`fire_episodes`).
- **Generación de reportes**:
  - `workers.tasks.closure_report_task.generate_closure_reports` → cola `reports`
  - `workers.tasks.pdf_generation_task.*` → cola `reports`
  - Produce PDFs y reportes de cierre almacenados en storage.
- **Notificaciones**:
  - `workers.tasks.notification.*` → cola `notification`
- **Gestión de episodios y tareas varias (cola `default`)**:
  - `workers.tasks.episode_merge_task.*` → cola `default`
  - Otras tareas que no tienen routing explícito pueden caer en `default`.

### Dependencias

- **Internas**:
  - Base de datos (mismas `DB_*` que `api`).
  - Redis (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
  - Storage OCI (envs `STORAGE_*`, `OCI_*`).
  - Scripts bajo `./scripts` montados en `/app/scripts`.
- **Externas**:
  - NASA FIRMS (`FIRMS_API_KEY`) para ingestión.

## `worker-gee` (`forestguard-worker-gee`)

- **Servicio Compose**: `worker-gee`
- **Imagen**: `ghcr.io/nicolasgh91/wildfire-recovery-argentina/worker:latest`
- **Dockerfile**: `Dockerfile.worker`
- **Comando** (`docker-compose.yml`):
  - `celery -A workers.celery_app worker --loglevel=info --queues=analysis,vae --concurrency=1 --max-tasks-per-child=50 --soft-time-limit=600 --time-limit=900`
- **Colas consumidas**:
  - `analysis`
  - `vae`
  - Tareas enrutadas a `gee` en `workers/celery_app.py` acaban en estas colas según configuración.

### Tareas típicas en `worker-gee`

- **Recuperación de vegetación (UC-F12)**:
  - `workers.tasks.recovery.analyze_recovery`
  - `workers.tasks.recovery.batch_recovery_monthly`
  - `workers.tasks.recovery.batch_recovery_recent`
  - `workers.tasks.recovery.batch_episode_recovery_analysis`
  - Colas: `gee` / `analysis` / `vae` según task.
  - Datos: `fire_events`, `fire_episodes`, `vegetation_monitoring`.
- **Destrucción / cambio de uso**:
  - `workers.tasks.destruction.batch_destruction_detection`
  - Colas: `gee` / `vae`.
- **Carousel satelital y enriquecimiento geográfico**:
  - `workers.tasks.carousel_task.generate_carousel` (colas `gee` y `analysis`).
  - `workers.tasks.geo_enrichment.*` (cola `analysis`).
  - `workers.tasks.exploration_hd_task.*` (cola `analysis`).
- **Mantenimiento y limpieza**:
  - `workers.tasks.cleanup_assets_task.cleanup_expired_assets` (cola `analysis`).

### Dependencias

- **Internas**:
  - Base de datos (mismas `DB_*` que `api`).
  - Redis (broker/backend).
  - Storage OCI (envs `STORAGE_*`, `OCI_*`).
- **Externas**:
  - Google Earth Engine / VAE:
    - `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH`.

## `celery-beat` (`forestguard-celery-beat`)

- **Servicio Compose**: `celery-beat`
- **Imagen**: `ghcr.io/nicolasgh91/wildfire-recovery-argentina/worker:latest`
- **Dockerfile**: `Dockerfile.worker`
- **Comando**:
  - `celery -A workers.celery_app beat --loglevel=info -s /tmp/celerybeat-schedule`
- **Rol**:
  - No ejecuta tareas en sí mismo.
  - Programa tareas recurrentes que terminan en colas atendidas por `worker-fast` y `worker-gee`.

### Principales entradas de `beat_schedule`

Según `workers/celery_app.py`:

- `download-firms-daily` → `workers.tasks.ingestion.download_firms_daily` → cola `ingestion`
- `cluster-daily` → `workers.tasks.clustering.cluster_detections` → cola `clustering`
- `cluster-episodes-daily` → `workers.tasks.clustering_task.cluster_fire_episodes_pipeline` → cola `clustering`
- `carousel-daily` → `workers.tasks.carousel_task.generate_carousel` → cola `gee`
- `closure-reports-daily` → `workers.tasks.closure_report_task.generate_closure_reports` → cola `reports`
- `cleanup-expired-assets` → `workers.tasks.cleanup_assets_task.cleanup_expired_assets` → cola `analysis`
- `close-extinct-episodes-daily` → `workers.tasks.episode_closer_task.close_extinct_episodes` → cola `analysis`
- `recovery-monthly` / `recovery-weekly-recent` → tareas de `workers.tasks.recovery` → cola `gee`
- `vae-recovery-monthly`, `vae-destruction-monthly`, `vae-episodes-weekly` → tareas UC-F12 (`recovery`/`destruction`) → cola `gee`

### Cómo verificar que `celery-beat` funciona

- Contenedor debe estar en estado **`Up`**:  
  `docker compose ps celery-beat`
- Logs deben mostrar ejecución periódica de tareas:  
  `docker compose logs -f celery-beat`
- En Flower (si está levantado), se ven tareas periódicas encoladas a las colas correspondientes.

## `flower` (`forestguard-flower`)

- **Servicio Compose**: `flower`
- **Imagen**: `ghcr.io/nicolasgh91/wildfire-recovery-argentina/worker:latest`
- **Dockerfile**: `Dockerfile.worker`
- **Profile**: `debug`
- **Comando**:
  - `celery -A workers.celery_app flower --port=5555`
- **Healthcheck**:
  - HTTP GET a `http://localhost:5555/healthcheck`

### Uso

- Levantar dashboard:

```bash
docker compose --profile debug up -d flower
```

- Acceder a la UI:
  - `http://localhost:5555`

Flower se conecta al mismo **broker Redis** y **backend** que los workers:

- `CELERY_BROKER_URL=redis://redis:6379/0`
- `CELERY_RESULT_BACKEND=redis://redis:6379/1`

## Mapeo cola → tasks → contenedores

Resumen de enrutamiento (simplificado, basado en `workers/celery_app.py`):

- **`ingestion`**:
  - `workers.tasks.ingestion.*`
  - Consumido por: `worker-fast`
- **`clustering`**:
  - `workers.tasks.clustering.*`
  - `workers.tasks.clustering_task.*`
  - Consumido por: `worker-fast`
- **`gee` / `vae` / `analysis` (GEE/VAE)**:
  - `workers.tasks.recovery.*`
  - `workers.tasks.destruction.*`
  - `workers.tasks.carousel_task.generate_carousel`
  - `workers.tasks.geo_enrichment.*`
  - `workers.tasks.exploration_hd_task.*`
  - `workers.tasks.cleanup_assets_task.*`
  - Consumido por: `worker-gee`
- **`reports`**:
  - `workers.tasks.closure_report_task.*`
  - `workers.tasks.pdf_generation_task.*`
  - Consumido por: `worker-fast`
- **`notification`**:
  - `workers.tasks.notification.*`
  - Consumido por: `worker-fast`
- **`default`**:
  - `workers.tasks.episode_merge_task.*`
  - Otras tasks sin routing explícito.
  - Consumido por: `worker-fast`

> Para un inventario detallado de cada task (parámetros, retornos, casos de uso), ver `docs/backend/workers/workers_documentation.md`.

