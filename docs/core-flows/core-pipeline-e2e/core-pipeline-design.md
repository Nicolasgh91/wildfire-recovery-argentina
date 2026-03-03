## Core Pipeline End‑to‑End — Diseño técnico

### 1. Vista general

El pipeline diario canónico sigue esta secuencia (ver también `docs/INDEX.md` y `uc-f12-data-flow-diagram-776569.md`):

1. Ingesta FIRMS → `fire_detections`.
2. Clustering detecciones → `fire_events`.
3. Actualización de estados de eventos (`active`/`monitoring`/`extinct`).
4. Geo‑enrichment y cruce con áreas protegidas.
5. Agrupación de eventos → `fire_episodes`.
6. Generación de thumbnails (carrusel) y assets derivados.
7. Análisis VAE (recuperación/destrucción) y rellenado de tablas de monitoreo.
8. Exposición vía API y consumo desde frontend.

### 2. Implementación en código

- **Ingesta**:
  - `scripts/maintenance/load_firms_incremental.py` (pipeline incremental).
  - `workers/tasks/ingestion.py` (task `download_firms_daily`, cola `ingestion`).
- **Clustering detecciones → eventos**:
  - `app/services/detection_clustering_service.py` (`run_clustering`).
  - `workers/tasks/clustering.py` (`cluster_detections`, cola `clustering`).
- **Estados de eventos**:
  - Lógica canónica en `app/services/fire_service.py` y `episode_flow_parameters.py`.
  - Script de soporte `scripts/run_pipeline_manual.py` ejecuta un paso dedicado (`step3_event_statuses`) usando SQL directo para forzar el estado según ventanas configuradas.
- **Geo‑enrichment**:
  - `workers/tasks/geo_enrichment.py` (`enrich_recent_fire_events`, cola `analysis`).
  - Usado tanto desde Celery Beat como en `scripts/run_pipeline_manual.py` (`step4_geo_enrichment`).
- **Episodios**:
  - `app/services/clustering_service.py` (`run_clustering` para episodios).
  - `workers/tasks/clustering_task.py` (`cluster_fire_episodes_pipeline`, cola `clustering`).
- **Carrusel y assets**:
  - `app/services/imagery_service.py` + `gee_service.py` + `storage_service.py`.
  - `workers/tasks/carousel_task.py` (`generate_carousel`, cola `gee`).
  - Pipeline de assets detallado en `docs/assets-generation/tareas-tecnicas-assets-pipeline.md`.
- **VAE / monitoreo NDVI**:
  - `app/services/vae_service.py`.
  - `workers/tasks/recovery.py`, `workers/tasks/destruction.py`.
  - `workers/tasks/recovery.batch_*` y schedule en `workers/celery_app.py` (cola `gee`).

### 3. Orquestación automática (Celery Beat)

Según `workers/celery_app.py`:

- `download-firms-daily` → 00:00 ART, cola `ingestion`.
- `cluster-daily` → 01:00 ART, cola `clustering`.
- `cluster-episodes-daily` → 02:00 ART, cola `clustering`.
- `carousel-daily` → 00:00 ART, cola `gee`.
- `cleanup-expired-assets` → 04:00 ART, cola `analysis`.
- `close-extinct-episodes-daily` → 05:00 ART, cola `analysis`.
- Tareas UC‑F12 (recovery/destruction/episodes) en colas `gee` según configuración de beat.

### 4. Ejecución manual del pipeline

`scripts/run_pipeline_manual.py` implementa una versión “lineal” del pipeline para debugging:

1. Muestra estado inicial (`fire_detections`/`fire_events`/`fire_episodes`).
2. Corre:
   - `step1_ingestion()` → llama `run_incremental_pipeline()`.
   - `step2_clustering(days_back)` → `DetectionClusteringService.run_clustering`.
   - `step3_event_statuses()` → actualiza estados con SQL basado en parámetros canónicos.
   - `step4_geo_enrichment(...)` → `enrich_recent_fire_events.apply(...).get()`.
   - `step5_episodes(days_back)` → `ClusteringService.run_clustering` (episodios).
3. Muestra estado tras cada fase y un resumen final.

Es la herramienta recomendada para validar cambios en el pipeline end‑to‑end en entornos de prueba.

### 5. Estado de la documentación E2E

- `docs/Carrusel fix/flujo_ingesta_procesamiento.md`:
  - **Estado**: PARCIAL/HISTÓRICO.
  - El flujo conceptual sigue siendo válido, pero la topología de workers descrita es previa a la consolidación actual en colas `ingestion`/`clustering`/`analysis`/`gee`.
- `docs/assets-generation/tareas-tecnicas-assets-pipeline.md`:
  - **Estado**: DISEÑO.
  - Especifica etapas y dependencias del pipeline de assets; se debe leer junto con este documento y `imagery_service.py` para obtener la imagen actual.
- `docs/flujo-deploy.md` y `docs/infrastructure/deployment/DEPLOYMENT.md`:
  - **Estado**: OK.
  - Describen cómo se despliega la app y cómo se levantan los workers que ejecutan este pipeline.

Este archivo es ahora la referencia central para entender cómo se conectan todas las piezas (scripts, workers y cron) en el pipeline de datos de punta a punta.

