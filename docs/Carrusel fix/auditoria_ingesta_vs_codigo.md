# Auditoría: flujo de ingesta vs. código real

**Fecha:** 2026-02-24  
**Fuente de verdad analizada:** `docs/Carrusel fix/flujo_ingesta_procesamiento.md`  
**Método:** Cruce manual de cada afirmación del documento contra el código real del repositorio.

> **Nota de vigencia (2026-03)**  
> Este archivo se mantiene como **auditoría histórica**. Las conclusiones relevantes ya se reflejan en:
> - `docs/core-flows/core-ingesta/core-ingesta-design.md` (diseño actual)  
> - `docs/core-flows/core-pipeline-e2e/core-pipeline-design.md` (visión global)  
> Ante discrepancias, priorizar esos documentos y el código fuente.

---

> Nota 2026-03: varias secciones de este documento se refieren a una topología de workers  
> con contenedores separados (`worker-ingestion`, `worker-clustering`, `worker-analysis`, `worker-reports`, `worker-vae`).  
> El estado actual usa `worker-fast` y `worker-gee` como workers consolidados.  
> Para el mapeo actualizado de colas → contenedores consultar `docs/containers/workers.md`.  
> El análisis de consistencia código ↔ flujo sigue siendo útil como auditoría histórica.

## Consistencias confirmadas

- **Ingesta (worker):** El worker `download_firms_daily` en `workers/tasks/ingestion.py` descarga de FIRMS delegando a `scripts.load_firms_incremental.run_incremental_pipeline`. El script calcula `h3_index` (resolución 8, `compute_h3_index` en línea 194), genera `detection_hash` SHA-256 (líneas 170-191) con los campos documentados, setea `is_processed = FALSE` y `fire_event_id = NULL` (líneas 520-521). Cola: `ingestion`. Schedule: `crontab(hour=0, minute=0)` = 00:00 UTC.
- **Clustering (worker):** El worker `cluster_detections` en `workers/tasks/clustering.py` delega a `DetectionClusteringService.run_clustering()`. Este servicio lee `clustering_versions` con `is_active = true` (líneas 111-136 de `detection_clustering_service.py`), setea `clustering_version_id` en `fire_events` (líneas 344-347), actualiza `fire_detections.fire_event_id` e `is_processed = true` (líneas 431-441). Cola: `clustering`. Schedule: 01:00 UTC.
- **Episodios (worker):** El worker `cluster_fire_episodes_pipeline` en `clustering_task.py` ejecuta la agregación a episodios vía `ClusteringService`. Mantiene `fire_episode_events` (vía `EpisodeService.assign_event()`). Existe lógica de fusión que registra en `episode_mergers` (`EpisodeService.merge_episodes()`, líneas 336-364 de `episode_service.py`). Actualiza `last_seen_at`. Schedule: 02:00 UTC.
- **Fusión de episodios:** `merge_episodes()` en `episode_service.py` (líneas 304-364) reasigna eventos del episodio absorbido al absorbente, registra en `episode_mergers`, y setea `status = 'closed'` en el episodio absorbido. Coincide con lo documentado.
- **Estados (episodios):** `_resolve_episode_status` en `episode_service.py` (líneas 139-185) implementa las 3 reglas: (1) active si algún evento activo, (2) extinct si `elapsed >= ventana`, (3) monitoring en otro caso. La ventana lee de `system_parameters` vía `_get_episode_window_hours()` con fallback a 720 horas (30 días).
- **Estados (eventos):** `resolve_fire_status` en `fire_service.py` (líneas 139-159) implementa las reglas para eventos: active si reciente, monitoring si dentro de ventana (168h default), extinct si fuera. Lee `event_monitoring_window_hours` de `system_parameters`.
- **Parámetros canónicos:** `episode_flow_parameters.py` carga 5 parámetros canónicos de `system_parameters` con defaults documentados: `event_spatial_epsilon_meters` (2000), `event_temporal_window_hours` (48), `event_monitoring_window_hours` (168), `episode_spatial_epsilon_meters` (6000), `episode_temporal_window_hours` (720).
- **Carrusel (endpoint):** El endpoint `GET /fire-episodes?mode=active` (`episodes.py` líneas 143-148) filtra con `slides_data IS NOT NULL`, `jsonb_array_length > 0`, `gee_candidate = true`, y `status IN ('active', 'monitoring')`. Coincide con lo documentado.
- **Carrusel (worker):** El carousel worker (`carousel_task.py`) está en cola `analysis`. `docker-compose.yml` tiene variables GEE (`GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH`) en `worker-analysis` (líneas 247-250).
- **Celery Beat:** El beat schedule en `workers/celery_app.py` coincide con los horarios documentados: 00:00 UTC (ingestion), 01:00 UTC (clustering), 02:00 UTC (episodes pipeline), 03:00 UTC (carousel), 04:00 UTC (cleanup), 08:00 UTC (closure reports).

---

## Inconsistencias encontradas

| # | Sección | Documento dice | Código dice | Archivo:línea | Severidad |
|---|---------|---------------|-------------|---------------|-----------|
| 1 | Ingesta (Worker) | El worker importa `from scripts.load_firms_incremental` | El archivo real está en `scripts/maintenance/load_firms_incremental.py`, no en `scripts/load_firms_incremental.py`. El archivo original fue borrado (`D` en git status). | `workers/tasks/ingestion.py:30` | **crítico** — El import va a fallar en runtime. El worker de ingesta está roto si este cambio se despliega sin un `__init__.py` que reexporte o sin revertir el borrado. |
| 2 | Infra (5.5) | `cleanup-expired-assets` en cola `default` | El beat schedule pone cleanup en cola `default`, pero ningún container en `docker-compose.yml` consume la cola `default`. Lo mismo aplica a `episode_merge_task` (routed a `default`). | `workers/celery_app.py:154`, `docker-compose.yml` | **alto** — Los tasks encolados en `default` nunca se ejecutarían en producción porque ningún worker consume esa cola. |
| 3 | Celery (5.4) | `celery_app.py` (raíz) es configuración alternativa con drift potencial | El archivo raíz existe y tiene configuración divergente: solo 3 beat entries (`download-firms-daily`, `cluster-daily`, `vae-recovery-weekly`) vs. 8+ en `workers/celery_app.py`. El `docker-compose.yml` usa `-A workers.celery_app` así que la raíz no se usa en producción, pero el drift es significativo. | `celery_app.py` (raíz) vs `workers/celery_app.py` | **alto** — Si alguien ejecuta Celery con el archivo raíz (ej: dev local), tendrá un schedule incompleto y routing parcial. Fuente de errores silenciosos. |
| 4 | Ingesta (1.2) | Deduplicación con `ON CONFLICT DO NOTHING` sobre constraint UNIQUE de `detection_hash` | La deduplicación real es por query previa (`get_existing_hashes`) que carga hashes existentes y filtra en Python antes de insertar. No usa `ON CONFLICT DO NOTHING` ni constraint UNIQUE en DB. | `scripts/maintenance/load_firms_incremental.py:397-472` | **medio** — Funcionalidad equivalente pero mecanismo distinto al documentado. Menos atómico: si dos instancias corren en paralelo, podrían insertar duplicados. |
| 5 | Infra (5.5) | El documento lista 5 servicios worker: ingestion, clustering, analysis, reports, beat | `docker-compose.yml` tiene 6 workers: ingestion, clustering, analysis, **vae**, reports, beat. El worker `worker-vae` consume cola `vae` separada (no documentado en el flujo). | `docker-compose.yml:278-342` | **medio** — El worker `worker-vae` no está documentado en la sección 5.5. |
| 6 | Estados (4.1) | Para eventos: "Active = al menos una detección reciente dentro de la ventana de monitoreo" | `resolve_fire_status` en `fire_service.py` no verifica detecciones recientes. Solo mira el timestamp de referencia (`last_seen_at` o `end_date`) relativo a `now`. El estado `active` se retorna cuando `fire.status` ya es `active` (líneas 140-144) o cuando `age < 0` (línea 152-153). No hay una "ventana de activo" separada. | `app/services/fire_service.py:139-159` | **medio** — El mecanismo real es: si ya tiene status guardado, lo usa; si no, calcula basado en edad vs. ventana de monitoring. `active` es el estado inicial al crear el evento. |
| 7 | Ingesta (1.2) | Deduplicación por llave compuesta de 6 campos: `satellite`, `instrument`, `detected_at`, `latitude`, `longitude`, `fire_radiative_power` | El hash SHA-256 real incluye también `confidence` como séptimo campo: `satellite\|instrument\|detected_at\|lat\|lon\|frp\|confidence`. | `scripts/maintenance/load_firms_incremental.py:170-191` | **bajo** — El hash es más restrictivo que lo documentado (incluye un campo extra). |
| 8 | Episodios (3.3) | Worker responsable es un task genérico `cluster-episodes-daily` | El task real se llama `workers.tasks.clustering_task.cluster_fire_episodes_pipeline` y además encadena un paso de geo-enrichment después del clustering de episodios (vía Celery canvas `chain`). | `workers/tasks/clustering_task.py:47-85`, `workers/celery_app.py:137-142` | **bajo** — El nombre de beat entry `cluster-episodes-daily` es correcto; el doc simplifica omitiendo el pipeline chain con geo_enrichment. |
| 9 | Carrusel (4.2) | El endpoint de episodios activos filtra `gee_candidate = true` | El endpoint `list_fire_episodes` en modo `active` filtra `gee_candidate == True` (línea 144). Pero el endpoint legacy `/active` (deprecated) **no** filtra por `gee_candidate` — solo por `slides_data IS NOT NULL` y status. | `app/api/routes/episodes.py:143-148` vs `325-340` | **bajo** — Solo afecta el endpoint deprecated que se eliminará el 2026-05-22. |

---

## No verificable (código no encontrado)

- **`scripts/load_firms_incremental.py` (ruta original):** El archivo fue borrado del repositorio (git status muestra `D scripts/load_firms_incremental.py`). El worker de ingesta referencia esta ruta en su import. El archivo real está en `scripts/maintenance/load_firms_incremental.py`. No se verificó si hay un `scripts/__init__.py` o symlink que resuelva el import.
- **Constraint UNIQUE sobre `detection_hash`:** No se verificó el schema SQL real de la tabla `fire_detections` para confirmar si existe un constraint UNIQUE sobre `detection_hash`. El documento lo recomienda pero el código de inserción no lo usa (deduplicación por query previa).
- **Task `closure_report_task`:** El archivo `workers/tasks/closure_report_task.py` fue mencionado en el documento (sección 5.1) pero no fue leído en esta auditoría. Su existencia se confirma indirectamente por el beat schedule.
- **`app/api/routes/monitoring.py`:** Listado en la sección 5.3 del documento como endpoint de recovery NDVI. No fue verificado en esta auditoría.

---

## Recomendaciones

| Prioridad | Acción | Detalle |
|-----------|--------|---------|
| **CRÍTICO** | Fix import ingesta | Resolver el import roto en `workers/tasks/ingestion.py` línea 30. Opciones: (a) revertir el borrado de `scripts/load_firms_incremental.py`, (b) actualizar el import a `scripts.maintenance.load_firms_incremental`, o (c) crear un `scripts/load_firms_incremental.py` que reexporte desde maintenance. |
| **ALTO** | Cola `default` sin consumer | Agregar un worker que consuma la cola `default` en `docker-compose.yml`, o reasignar los tasks `cleanup-expired-assets` y `episode_merge_task` a colas existentes (ej: `analysis` o `reports`). |
| **ALTO** | Resolver drift de `celery_app.py` raíz | Eliminar `celery_app.py` de la raíz o sincronizar su configuración con `workers/celery_app.py`. Mientras exista, es fuente de confusión y errores en desarrollo local. |
| **MEDIO** | Documentar worker-vae | Agregar el servicio `worker-vae` a la sección 5.5 del documento de flujo. |
| **MEDIO** | Alinear documentación de deduplicación | Actualizar la sección 1.2 para reflejar que la deduplicación real es por query previa de hashes en Python, no por `ON CONFLICT DO NOTHING`. Considerar migrar a `ON CONFLICT` para atomicidad. |
| **BAJO** | Corregir campos del hash | Documentar que el `detection_hash` incluye `confidence` además de los 6 campos listados. |
