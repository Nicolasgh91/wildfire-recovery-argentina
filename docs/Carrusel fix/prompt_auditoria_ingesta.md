# Auditoría: flujo de ingesta vs. código real

Usá como fuente de verdad el documento `flujo_ingesta_procesamiento.md` del proyecto. Tu trabajo es cruzar cada afirmación de ese documento contra el código real del repositorio y reportar inconsistencias.

## Alcance

Analizá estos archivos/directorios (buscá los que existan):

**Workers:**
- `workers/tasks/ingestion.py`
- `workers/tasks/clustering.py`
- `workers/tasks/clustering_task.py`
- `workers/tasks/carousel_task.py`

**Servicios:**
- `app/services/fire_service.py`
- `app/services/episode_service.py`
- `app/services/episode_flow_parameters.py`
- `app/services/imagery_service.py`
- `app/services/gee_service.py`

**Configuración:**
- `workers/celery_app.py`
- `celery_app.py` (raíz, si existe)
- `docker-compose.yml`

**Endpoints:**
- `app/api/routes/episodes.py`
- `app/api/v1/fires.py`
- `app/api/v1/imagery.py`

## Qué buscar

Para cada sección del documento, verificá:

1. **Ingesta:** ¿el worker realmente descarga de FIRMS? ¿calcula `h3_index`? ¿hay deduplicación implementada (hash, ON CONFLICT, o query previa)? ¿setea `is_processed=false` y `fire_event_id=null`?

2. **Clustering:** ¿lee `clustering_versions` con `is_active=true`? ¿setea `clustering_version_id` en `fire_events`? ¿actualiza `fire_detections.fire_event_id` e `is_processed` tras crear eventos?

3. **Episodios:** ¿existe el worker de agregación? ¿mantiene `fire_episode_events`? ¿hay lógica de fusión que registre en `episode_mergers`? ¿actualiza `last_seen_at`?

4. **Estados:** ¿`_resolve_episode_status` implementa las 3 reglas documentadas (active si hay evento activo, monitoring si dentro de ventana, extinct si fuera)? ¿la ventana usa `system_parameters` o está hardcodeada? ¿cuál es el valor actual del default en código?

5. **Carrusel:** ¿el endpoint de episodios activos filtra por `slides_data IS NOT NULL`? ¿el carousel worker está en cola `analysis` o `default`? ¿`docker-compose.yml` tiene variables GEE en `worker-analysis`?

6. **Celery:** ¿el beat schedule coincide con los horarios documentados (00:00, 01:00, 02:00, 03:00 UTC)? ¿hay dos `celery_app.py` con configuraciones divergentes?

## Formato del reporte

Generá un markdown con esta estructura:

```markdown
## Resultado de auditoría

### Consistencias confirmadas
- [lista de puntos donde código y documento coinciden]

### Inconsistencias encontradas
| # | Sección | Documento dice | Código dice | Archivo:línea | Severidad |
|---|---------|---------------|-------------|---------------|-----------|

### No verificable (código no encontrado)
- [lista de puntos donde el código no existe o no se pudo localizar]

### Recomendaciones
- [acciones concretas para resolver las inconsistencias]
```

Severidades: **crítico** (funcionalidad rota), **alto** (drift significativo), **medio** (inconsistencia menor), **bajo** (cosmético/documentación).

No supongas. Si un archivo no existe, reportalo. Si una función existe pero hace algo distinto a lo documentado, citá el fragmento de código relevante.
