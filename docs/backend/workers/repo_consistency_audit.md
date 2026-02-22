# Auditoría de consistencia del repositorio vs flujo canónico (episode_creation_flow)

Fecha: 2026-02-16  
Alcance: workers/Celery, pipeline detecciones→eventos→episodios, persistencia/derivados, riesgos de performance/seguridad (sin cambios de implementación).

## 0) Fuente de verdad usada y supuestos

### Documentación canónica tomada como base
Se tomó como base principal `episode_creation_flow/1_tech_tasks_final.md` (archivo “final”), complementado por `episode_creation_flow/plan_episode_flow.md` y `episode_creation_flow/task_execution_log.md` para validar intención operativa y decisiones cerradas.

### Suposiciones a validar
1. **Top 20 + thumbnails obligatorias para carrusel**: el requerimiento aparece en el objetivo de esta auditoría, pero no está explicitado como regla rígida en `1_tech_tasks_final.md`. Se trata como requisito esperado del producto (a validar con PO).
2. **Enriquecimientos geográficos (provincia + áreas protegidas + %)**: hay soporte de datos/modelos y scripts, pero la canónica en `episode_creation_flow/` no define explícitamente en qué worker del pipeline deben ejecutarse.
3. **Parámetros de clustering de episodios**: se asume que FG-EP-22 aplica tanto a detecciones→eventos como a eventos→episodios (coherente con `plan_episode_flow.md`).

---

## 1) Estado esperado (resumen canónico en 24 bullets)

1. `fire_events` debe tener `last_seen_at` y backfill por `MAX(fire_detections.detected_at)` (FG-EP-20).  
2. Debe existir índice `idx_fire_events_last_seen_at` para recencia (FG-EP-20).  
3. `fire_events.status` canónico: `active|monitoring|extinct` (FG-EP-21).  
4. El backend no debe emitir ni esperar `controlled/extinguished` (FG-EP-21).  
5. `extinguished_at` debe migrar a `extinct_at` (FG-EP-21).  
6. Deben insertarse parámetros canónicos en `system_parameters` (FG-EP-22).  
7. Parámetros evento: `event_spatial_epsilon_meters=2000`, `event_temporal_window_hours=48`, `event_monitoring_window_hours=168` (FG-EP-22).  
8. Parámetros episodio: `episode_spatial_epsilon_meters=6000`, `episode_temporal_window_hours=96` (FG-EP-22).  
9. Workers/servicios deben leer estos parámetros (con fallback seguro) (FG-EP-22).  
10. `fire_episodes.end_date` solo debe setearse cuando `status='closed'` (FG-EP-23).  
11. Trigger/check deben enforzar semántica de `end_date` (FG-EP-23).  
12. Regla de negocio `fire_episode_events`: 1:N (un evento en un episodio a la vez) (FG-EP-24).  
13. Índice único recomendado para forzar 1:N en base (FG-EP-24).  
14. Pipeline detecciones→eventos debe persistir derivadas temporales (start/end/last_seen).  
15. Pipeline eventos→episodios debe resolver creación/absorción/merge de episodios.  
16. Cierre por merge/manual debe dejar episodio absorbido en `closed` con `end_date` válido.  
17. Workers deben operar con configuración idempotente/migraciones idempotentes cuando aplique.
18. Debe mantenerse consistencia de estados entre eventos y episodios.
19. Debe existir cobertura de tests de integración por FG-EP-20..24.
20. Debe existir smoke de registro de tasks Celery.
21. La fuente de recencia para actividad debe priorizar `last_seen_at`.
22. Debe evitarse drift de terminología legacy (`extinguished`, `controlled`).
23. Debe haber fallback seguro de parámetros fuera de producción.
24. Debe existir estrategia operacional para workers (colas/routing/beat) alineada al pipeline.

---

## 2) Matriz de requerimientos (esperado → señal observable en código)

| Requerimiento | Evidencia doc | Señal observable esperada en código |
|---|---|---|
| `fire_events.last_seen_at` + índice + uso en recencia | `1_tech_tasks_final.md` FG-EP-20 | Migración Alembic FG-EP-20 + servicios consultando `last_seen_at` |
| Estados canónicos evento (`active|monitoring|extinct`) | `1_tech_tasks_final.md` FG-EP-21 | Enum/schema + queries + workers sin estados legacy |
| Parámetros canónicos en `system_parameters` | `1_tech_tasks_final.md` FG-EP-22 | Migración + lectura desde servicios de clustering |
| `end_date` solo para `closed` | `1_tech_tasks_final.md` FG-EP-23 | Trigger/constraint + escrituras de episodios compatibles |
| Regla 1:N evento→episodio | `1_tech_tasks_final.md` FG-EP-24 | índice único + `assign_event` transaccional |
| Uso de parámetros canónicos en eventos y episodios | `plan_episode_flow.md` FG-EP-22 | `DetectionClusteringService` y `ClusteringService` leyendo `system_parameters` |
| Worker topology estable (ingestión, clustering, análisis) | `plan_episode_flow.md` y alcance solicitado | `workers/celery_app.py` con `include`, `task_routes`, beat consistente |
| Criterio de carrusel (thumbnails + límite) | Objetivo auditoría | endpoint/UI y servicio de imágenes en episodios con `slides_data` |
| Enriquecimientos geográficos | Objetivo auditoría | pipeline o tasks dedicadas para provincia/protected areas |

---

## 3) Mapeo de implementación actual

### 3.1 Celery / workers / routing / beat
- App Celery principal: `workers/celery_app.py`.
- Incluye tasks de `workers/tasks/*` vía `include=[...]`.
- Rutas de colas declaradas para tareas principales (`ingestion`, `clustering`, `analysis`, `notification`).
- Beat schedule diario configurado para ingestión, clustering de detecciones, clustering de episodios, carrusel y closure reports.
- Cola por defecto declarada como `default`.

### 3.2 Pipeline detecciones → eventos
- Task: `workers.tasks.clustering.cluster_detections`.
- Servicio: `app/services/detection_clustering_service.py`.
- Implementa ST-DBSCAN con ventana espaciotemporal; crea `fire_events`; asigna `fire_detections.fire_event_id`; marca procesadas.
- Lee parámetros canónicos para **eventos** desde `system_parameters`.

### 3.3 Pipeline eventos → episodios
- Task: `workers.tasks.clustering_task.cluster_fire_episodes`.
- Servicio: `app/services/clustering_service.py`.
- Carga eventos, encuentra episodios candidatos por distancia + ventana temporal, crea episodio si no hay match, mergea si hay múltiples, reasigna evento y recalcula métricas.

### 3.4 Persistencia/derivados
- `EpisodeService` gestiona creación, asignación, merge y recálculo de métricas/estado.
- Trigger de `end_date` y unicidad 1:N aparecen implementados vía migraciones FG-EP-23/24.
- `ImageryService` actualiza `fire_episodes.slides_data` y `last_gee_image_id`; usa `gee_candidate` y prioridad.

### 3.5 Config y dependencias externas
- Config global: `app/core/config.py` (Pydantic Settings).
- Broker/result backend Celery: `app/core/celery_runtime.py`.
- DB session: `app/db/session.py`.
- Storage backend: `app/services/storage_service.py` (gcs/r2/local).

---

## 4) Comparación esperado vs actual (hallazgos)

### Hallazgo FG-EP-CHECK-01
**Tipo**: mismatch  
**Esperado (doc)**: parámetros canónicos FG-EP-22 deben usarse en workers de clustering de episodios (`episode_spatial_epsilon_meters`, `episode_temporal_window_hours`).  
**Actual (código)**: `ClusteringService` toma epsilon y ventana temporal desde `clustering_versions` (`epsilon_km`, `temporal_window_hours`) sin leer `system_parameters` canónicos.  
**Evidencia**: `app/services/clustering_service.py` (`_get_active_version`, cálculo `epsilon_meters = version.epsilon_km * 1000.0`, y uso de `version.temporal_window_hours`).  
**Impacto**: drift de comportamiento entre evento y episodio; cambios canónicos en `system_parameters` no impactan clustering de episodios.  
**Severidad**: **alta**.  
**Fix propuesto**: resolver parámetros de episodio vía `load_canonical_episode_flow_parameters` con fallback; usar `clustering_versions` solo para versionado/metadata o como fallback secundario explícito.  
**Tests sugeridos**: unit test que fuerce valores en `system_parameters` y verifique query de candidatos con epsilon/ventana esperados; integración con fixture de eventos límite.

### Hallazgo FG-EP-CHECK-02
**Tipo**: drift  
**Esperado (doc)**: backend no debe emitir/esperar estados legacy (`controlled`, `extinguished`).  
**Actual (código)**: `EpisodeService._resolve_episode_status` todavía interpreta `controlled` como `monitoring`.  
**Evidencia**: `app/services/episode_service.py` (`if "monitoring" in event_statuses or "controlled" in event_statuses`).  
**Impacto**: mantiene acoplamiento a datos legacy; dificulta detectar regresiones de normalización FG-EP-21.  
**Severidad**: **media**.  
**Fix propuesto**: eliminar rama `controlled`; en su lugar, validar/normalizar upstream y loggear estado desconocido.  
**Tests sugeridos**: unit test de resolución de estado que falle ante valores no canónicos.

### Hallazgo FG-EP-CHECK-03
**Tipo**: riesgo  
**Esperado (runtime robusto)**: arranque Celery no debe depender de inicialización frágil en import-time.  
**Actual (código)**: `workers/celery_app.py` importa módulos que usan `SessionLocal`, y `SessionLocal` crea engine con `settings.DATABASE_URL` en import-time. Si falta `DATABASE_URL`, el worker puede caer al iniciar.  
**Evidencia**: `app/db/session.py` (`create_engine(settings.DATABASE_URL, ...)`) + tasks que importan `SessionLocal`.  
**Impacto**: falla de bootstrap de workers/beat en despliegues con variables incompletas o orden de carga incorrecto.  
**Severidad**: **bloqueante** (operativa).  
**Fix propuesto**: validación explícita temprana de `DATABASE_URL` con mensaje claro y/o lazy init de engine; añadir smoke test de import Celery sin side-effects críticos.  
**Tests sugeridos**: smoke `python -c "from workers.celery_app import celery_app; celery_app.loader.import_default_modules()"` con matriz de env mínima/máxima.

### Hallazgo FG-EP-CHECK-04
**Tipo**: riesgo  
**Esperado**: un único path canónico para task `workers.tasks.clustering.cluster_detections`.  
**Actual**: existe una implementación real en `workers/tasks/clustering.py`, pero también un módulo legacy `app/services/clustering.py` con la **misma task name** y lógica stub (`eps_meters=500`, resultados mock).  
**Evidencia**: comparación entre `workers/tasks/clustering.py` y `app/services/clustering.py`.  
**Impacto**: riesgo de colisión de task registry si se importa el módulo legacy por error (drift silencioso de pipeline).  
**Severidad**: **alta**.  
**Fix propuesto**: remover o renombrar tasks legacy en `app/services/*`; mantener una única definición por task name.  
**Tests sugeridos**: smoke de registry que valide unicidad de nombres (`workers.tasks.*`) y módulo origen esperado.

### Hallazgo FG-EP-CHECK-05
**Tipo**: missing  
**Esperado (pipeline productivo)**: ingestión debe alimentar detecciones reales para sostener el flujo detecciones→eventos→episodios.  
**Actual**: `workers.tasks.ingestion.download_firms_daily` es stub (retorna contadores 0, TODO explícito).  
**Evidencia**: `workers/tasks/ingestion.py` (“Stub implementation - integrate with load_firms_incremental.py”).  
**Impacto**: pipeline no se autoalimenta en producción sólo con Celery/Beat; depende de procesos externos/manuales.  
**Severidad**: **alta**.  
**Fix propuesto**: integrar script/servicio de ingestión real, con idempotencia por lote y deduplicación por clave natural de detección.  
**Tests sugeridos**: integración de ingestión sobre fixture CSV + validación de upsert/deduplicación.

### Hallazgo FG-EP-CHECK-06
**Tipo**: drift  
**Esperado (objetivo auditoría)**: criterio canónico de carrusel con límite operacional claro (ej. top 20) y thumbnails obligatorias.  
**Actual**: API de episodios y fires usan default `limit=20`, pero `ImageryService` usa `DEFAULT_BATCH_SIZE=15` y parámetro dinámico `carousel_batch_size`; no hay una única fuente canónica de límite para generación/publicación.  
**Evidencia**: `app/api/routes/episodes.py` (`limit=20`), `app/api/v1/fires.py` (`limit=20`), `app/services/imagery_service.py` (`DEFAULT_BATCH_SIZE = 15`).  
**Impacto**: posible desalineación entre cantidad generada y cantidad mostrada; puede producir items sin refresh o “huecos” de calidad.  
**Severidad**: **media**.  
**Fix propuesto**: definir parámetro canónico único (`carousel_home_limit`) usado por generación y lectura; documentar precedencia.  
**Tests sugeridos**: test de contrato API+servicio verificando consistencia de límite efectivo.

### Hallazgo FG-EP-CHECK-07
**Tipo**: missing / suposición a validar  
**Esperado (objetivo auditoría)**: enriquecimiento geográfico dentro del pipeline operativo (provincia + áreas protegidas y % afectado).  
**Actual**: hay soporte de datos y scripts (`cross_fire_protected_areas.py`, endpoints y schemas), pero no se observa task Celery dedicada ni encadenamiento explícito post-clustering para refrescar intersecciones/provincias en el pipeline principal.  
**Evidencia**: `workers/celery_app.py` no incluye task de enriquecimiento geográfico; scripts existen fuera del ciclo Celery.  
**Impacto**: riesgo de datos desactualizados para UI/estadísticas legales si no se ejecutan scripts externos con cadencia consistente.  
**Severidad**: **media**.  
**Fix propuesto**: definir task `geo_enrichment` idempotente (incremental) y programarla en beat tras clustering.  
**Tests sugeridos**: integración DB con evento nuevo + enriquecimiento + verificación de provincia/intersecciones.

### Hallazgo FG-EP-CHECK-08
**Tipo**: riesgo  
**Esperado**: idempotencia y aislamiento adecuados en tasks encadenadas.  
**Actual**: en `workers/tasks/destruction.py` y `workers/tasks/recovery.py` hay patrones de subtasks con `.apply_async(...).get()` dentro de task Celery, lo que bloquea workers y puede provocar deadlocks/throughput bajo según pool/concurrency.  
**Evidencia**: `workers/tasks/destruction.py` (`generate_destruction_report` llama `.get()` en subtasks).  
**Impacto**: degradación de performance, acople fuerte a disponibilidad de workers/colas y riesgo de timeouts.  
**Severidad**: **media**.  
**Fix propuesto**: migrar a canvas (`chain/group/chord`) o diseño async non-blocking; persistir estado intermedio.  
**Tests sugeridos**: test de task orchestration con worker test mode validando no-bloqueo.

---

## 5) Chequeos de integridad de runtime (estático, sin desplegar)

### 5.1 Registro de tasks Celery
Se verificó de forma estática que la app Celery carga tasks esperadas al forzar `import_default_modules()`.

Resultado: **OK con observación**: sin `import_default_modules()`, el listado inicial no refleja tasks incluidas; con import forzado aparecen tasks `workers.tasks.*` esperadas.

### 5.2 Múltiples `celery_app` / conflictos
- No se detectó una segunda instancia `Celery(...)` activa en árbol `workers/app`.
- Sí se detectan módulos legacy en `app/services/` con definición de tasks y nombres que colisionan con workers actuales.

### 5.3 Consistencia colas producer/consumer
- Colas declaradas en `task_routes` (`ingestion`, `clustering`, `analysis`, `notification`) son usadas por tareas principales.
- Existen tasks `shared_task` secundarias sin ruta explícita, que caerán en `default` si se encolan por nombre sin `queue`.

### 5.4 Dependencias en import-time
- Riesgo confirmado por diseño en DB/session/config al importar workers si faltan env críticas.

---

## 6) Recomendaciones de performance y seguridad (observacional)

### Performance
1. Evitar `.get()` de subtasks dentro de workers; usar primitives de Celery canvas.
2. Estandarizar batch limits entre generación de carrusel y endpoints de consumo.
3. Añadir métricas de cardinalidad de candidatos en clustering de episodios (ya hay `candidate_metrics`, falta exportarlas a monitoreo).
4. Evaluar índices para filtros temporales usados en candidatos de episodios (`start_date`, `last_seen_at`, estado no-closed + geoespacial).

### Seguridad/robustez
1. Endurecer arranque de workers ante env incompleta con mensajes accionables (no stacktrace críptica).
2. Revisar singleton global en `StorageService` para evitar contaminación de estado entre tests/procesos largos.
3. Asegurar que tasks de correo/notificaciones saniticen payloads y limiten retries para evitar loops.
4. Añadir verificación de integridad de config storage (backend + credenciales + buckets) al startup de worker de imagery.

---

## 7) Set mínimo propuesto de tests/observabilidad

### Tests automatizables
1. **Unit** agrupamiento episodio: bordes de distancia/tiempo, empate entre candidatos, multi-provincia.
2. **Integración DB** detecciones→evento→episodio: crear detecciones fixture, correr tasks/servicios, verificar asignación y métricas.
3. **Smoke Celery**: import app + `import_default_modules()` + assert de registro de tasks críticas.
4. **Contrato de parámetros**: mutar `system_parameters` y validar que ambos servicios (detecciones y episodios) usan valores actualizados.
5. **Thumbnails obligatorias**: endpoint Home sólo retorna episodios/fuegos con `slides_data` válido.
6. **1:N**: intento de doble asignación de `event_id` a dos episodios debe fallar o reasignar atómicamente.

### Observabilidad recomendada
- `task_duration_seconds{task_name}`
- `task_failures_total{task_name,error_type}`
- `episodes_created_total`, `episodes_updated_total`, `episodes_merged_total`
- `clustering_candidate_count_p95`
- `carousel_processed_total`, `carousel_updated_total`, `carousel_errors_total`
- `geo_enrichment_lag_hours`

---

## 8) Resumen ejecutivo

El repositorio muestra una base fuerte alineada a FG-EP-20..24 (migraciones y estructura principal), pero persisten divergencias importantes en **consistencia de parámetros canónicos entre pipelines**, **riesgos operativos de arranque/import-time**, y **drift de módulos legacy con task names duplicados**. Los bloqueantes/altas se pueden resolver en PRs pequeños, manteniendo bajo riesgo si se prioriza primero bootstrap/registry y luego comportamiento funcional.
