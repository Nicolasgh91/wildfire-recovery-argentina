# Plan de corrección: inconsistencias del pipeline de ingesta

**Fecha:** 2026-02-24
**Origen:** `docs/Carrusel fix/auditoria_ingesta_vs_codigo.md`
**Objetivo:** Corregir las 9 inconsistencias detectadas, alinear documentación, y proveer tests + queries de validación para cada instancia del flujo.

---

## Resumen de tareas por prioridad

| ID | Prioridad | Tarea | Archivos afectados |
|----|-----------|-------|--------------------|
| T1 | CRÍTICO | Fix import roto del worker de ingesta | `workers/tasks/ingestion.py`, `scripts/maintenance/load_firms_incremental.py` |
| T2 | ALTO | Resolver cola `default` sin consumer | `workers/celery_app.py`, `docker-compose.yml` |
| T3 | ALTO | Resolver cola `notification` sin consumer | `workers/celery_app.py`, `docker-compose.yml` |
| T4 | ALTO | Eliminar drift de `celery_app.py` raíz | `celery_app.py` (raíz) |
| T5 | MEDIO | Actualizar documentación de deduplicación | `docs/Carrusel fix/flujo_ingesta_procesamiento.md` |
| T6 | MEDIO | Documentar worker-vae en el flujo | `docs/Carrusel fix/flujo_ingesta_procesamiento.md` |
| T7 | MEDIO | Alinear doc de estados de eventos | `docs/Carrusel fix/flujo_ingesta_procesamiento.md` |
| T8 | BAJO | Corregir campos del hash en documentación | `docs/Carrusel fix/flujo_ingesta_procesamiento.md` |
| T9 | BAJO | Documentar geo-enrichment en pipeline de episodios | `docs/Carrusel fix/flujo_ingesta_procesamiento.md` |

---

## T1 — CRÍTICO: Fix import roto del worker de ingesta

### Problema

`workers/tasks/ingestion.py:30` importa `from scripts.load_firms_incremental import run_incremental_pipeline`, pero el archivo `scripts/load_firms_incremental.py` fue borrado y movido a `scripts/maintenance/load_firms_incremental.py`. No existen `scripts/__init__.py` ni `scripts/maintenance/__init__.py`.

### Solución

Actualizar el import en el worker para que apunte a la nueva ubicación.

**Archivo:** `workers/tasks/ingestion.py`
```python
# ANTES (línea 30):
from scripts.load_firms_incremental import run_incremental_pipeline

# DESPUÉS:
from scripts.maintenance.load_firms_incremental import run_incremental_pipeline
```

Además, crear los `__init__.py` necesarios para que Python resuelva el módulo:

```
scripts/__init__.py              (archivo vacío)
scripts/maintenance/__init__.py  (archivo vacío)
```

Actualizar también la referencia en la string `"source"` (línea 47):

```python
# ANTES:
"source": "scripts.load_firms_incremental.run_incremental_pipeline",

# DESPUÉS:
"source": "scripts.maintenance.load_firms_incremental.run_incremental_pipeline",
```

### Test local

```bash
# 1. Verificar que el import resuelve sin error
python -c "from scripts.maintenance.load_firms_incremental import run_incremental_pipeline; print('OK:', run_incremental_pipeline)"

# 2. Verificar que el worker se carga sin ImportError
python -c "from workers.tasks.ingestion import download_firms_daily; print('OK:', download_firms_daily.name)"

# 3. Dry-run del pipeline (no modifica la BD)
python -m scripts.maintenance.load_firms_incremental --dry-run --days 1
```

### Query de validación

```sql
-- Verificar que la ingesta dejó registros recientes (ejecutar después de un run real)
SELECT
    DATE(detected_at) AS fecha,
    satellite,
    COUNT(*) AS detecciones,
    COUNT(*) FILTER (WHERE is_processed = false) AS pendientes,
    COUNT(*) FILTER (WHERE fire_event_id IS NULL) AS sin_evento
FROM fire_detections
WHERE detected_at >= NOW() - INTERVAL '3 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

---

## T2 — ALTO: Resolver cola `default` sin consumer

### Problema

El task `cleanup-expired-assets` se programa en el beat schedule con cola `default` (vía `task_default_queue`), pero ningún worker en `docker-compose.yml` consume esa cola. El task nunca se ejecuta en producción.

### Solución

Reasignar `cleanup_expired_assets` a la cola `analysis` (tiene baja concurrencia, apropiada para limpieza).

**Archivo:** `workers/celery_app.py` — agregar routing explícito en `task_routes`:

```python
# En task_routes, agregar:
'workers.tasks.cleanup_assets_task.cleanup_expired_assets': {'queue': 'analysis'},
```

**Archivo:** `workers/celery_app.py` — actualizar el beat schedule entry:

```python
'cleanup-expired-assets': {
    'task': 'workers.tasks.cleanup_assets_task.cleanup_expired_assets',
    'schedule': crontab(hour=4, minute=0),  # 04:00 UTC
    'options': {'queue': 'analysis'}  # <-- cambiar de 'default' a 'analysis'
},
```

**Archivo:** `workers/tasks/cleanup_assets_task.py` — agregar cola explícita al decorador:

```python
@celery_app.task(
    name="workers.tasks.cleanup_assets_task.cleanup_expired_assets",
    queue="analysis",  # <-- agregar
)
```

### Test local

```bash
# Verificar que el task se routea correctamente
python -c "
from workers.celery_app import celery_app
route = celery_app.amqp.router.route({}, 'workers.tasks.cleanup_assets_task.cleanup_expired_assets')
print('Queue:', route.get('queue', 'default'))
"
```

### Query de validación

```sql
-- Verificar que el cleanup no dejó assets huérfanos (post-ejecución)
SELECT COUNT(*) AS assets_expirados
FROM investigation_assets
WHERE expires_at IS NOT NULL
  AND expires_at < NOW();
```

---

## T3 — ALTO: Resolver cola `notification` sin consumer

### Problema

El task `send_contact_email` se routea a cola `notification` en `task_routes`, pero ningún worker consume esa cola.

### Solución

Reasignar a la cola `reports` (worker existente con baja carga) o agregar `notification` al comando del worker de reports.

**Opción recomendada:** Agregar `notification` al worker-reports.

**Archivo:** `docker-compose.yml` — worker-reports:

```yaml
# ANTES:
command: celery -A workers.celery_app worker --loglevel=info --queues=reports --concurrency=2

# DESPUÉS:
command: celery -A workers.celery_app worker --loglevel=info --queues=reports,notification --concurrency=2
```

### Test local

```bash
# Verificar que el task se routea correctamente
python -c "
from workers.celery_app import celery_app
route = celery_app.amqp.router.route({}, 'workers.tasks.notification.send_contact_email')
print('Queue:', route.get('queue', 'default'))
"
```

---

## T4 — ALTO: Eliminar drift de `celery_app.py` raíz

### Problema

`celery_app.py` en la raíz tiene configuración divergente: solo 3 beat entries, includes incompletos y routing parcial. `docker-compose.yml` usa `workers.celery_app`, por lo que el archivo raíz no se usa en producción pero confunde en desarrollo local.

### Solución

Reemplazar `celery_app.py` (raíz) con un re-export que delegue a la configuración canónica:

```python
"""
Celery Configuration — Proxy to canonical workers.celery_app
============================================================
This file exists for backward compatibility with scripts and local
development that invoke ``celery -A celery_app``.

The single source of truth is ``workers/celery_app.py``.
"""

from workers.celery_app import celery_app  # noqa: F401
```

### Test local

```bash
# Verificar que ambos entry-points cargan la misma app con el mismo schedule
python -c "
from celery_app import celery_app as root_app
from workers.celery_app import celery_app as workers_app
assert root_app is workers_app, 'Apps are different objects!'
print('OK: same Celery app instance')
print('Beat entries:', len(root_app.conf.beat_schedule))
"
```

---

## T5 — MEDIO: Actualizar documentación de deduplicación

### Problema

Sección 1.2 del flujo dice "ON CONFLICT DO NOTHING con constraint UNIQUE de detection_hash". La implementación real usa query previa de hashes + filtro en Python.

### Cambio en `docs/Carrusel fix/flujo_ingesta_procesamiento.md`

Reemplazar la fila de deduplicación en la tabla de la sección 1.2:

```markdown
| Deduplicación | Por llave compuesta (`satellite`, `instrument`, `detected_at`, `latitude`, `longitude`, `fire_radiative_power`, `confidence_normalized`). Estrategia: hash SHA-256 persistido como `detection_hash`. Pre-filtrado en Python: se consultan hashes existentes para las fechas del batch y se descartan duplicados antes de insertar. |
```

### Query de validación

```sql
-- Verificar que no hay duplicados en fire_detections
SELECT detection_hash, COUNT(*) AS cnt
FROM fire_detections
WHERE detection_hash IS NOT NULL
GROUP BY detection_hash
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;

-- Verificar integridad de hashes recientes
SELECT
    COUNT(*) AS total,
    COUNT(detection_hash) AS con_hash,
    COUNT(*) - COUNT(detection_hash) AS sin_hash
FROM fire_detections
WHERE detected_at >= NOW() - INTERVAL '7 days';
```

---

## T6 — MEDIO: Documentar worker-vae en el flujo

### Cambio en `docs/Carrusel fix/flujo_ingesta_procesamiento.md`

En la sección 5.5 (tabla de infraestructura docker-compose), agregar una fila:

```markdown
| `worker-vae` | `forestguard-worker-vae` | `vae` |
```

En la sección 5.1 (tabla de Workers Celery), verificar que Recovery y Destruction mencionan cola `vae` (ya lo hacen).

---

## T7 — MEDIO: Alinear documentación de estados de eventos

### Cambio en `docs/Carrusel fix/flujo_ingesta_procesamiento.md`

En sección 4.1, tabla de estados de Fire Event, corregir la descripción de "Active":

```markdown
| 🟢 Activo | `active` | Estado inicial al crear el evento. Mientras `last_seen_at` o `end_date` esté dentro de la ventana de monitoreo, se mantiene activo | Fuego con calor activo detectado |
```

Y agregar nota aclaratoria:

```markdown
**Nota:** `resolve_fire_status` en `fire_service.py` usa el status persistido si existe. Solo recalcula si el evento no tiene status guardado: compara la edad del evento (`now - last_seen_at`) contra la ventana de monitoreo. Si el evento es reciente (edad negativa, timestamp futuro), se considera activo.
```

### Test de validación (test unitario existente)

```bash
# Ejecutar el test existente del resolver de estados de episodios
pytest tests/unit/test_episode_status_resolver.py -v
```

### Query de validación

```sql
-- Verificar coherencia de estados de eventos
SELECT
    status,
    COUNT(*) AS total,
    MIN(COALESCE(last_seen_at, end_date, start_date)) AS oldest_reference,
    MAX(COALESCE(last_seen_at, end_date, start_date)) AS newest_reference,
    COUNT(*) FILTER (
        WHERE COALESCE(last_seen_at, end_date, start_date) < NOW() - INTERVAL '168 hours'
        AND status = 'active'
    ) AS activos_vencidos
FROM fire_events
GROUP BY status
ORDER BY status;

-- Verificar coherencia de estados de episodios
SELECT
    status,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0) AS con_slides,
    COUNT(*) FILTER (WHERE gee_candidate = true) AS gee_candidates
FROM fire_episodes
GROUP BY status
ORDER BY status;
```

---

## T8 — BAJO: Corregir campos del hash en documentación

### Cambio en `docs/Carrusel fix/flujo_ingesta_procesamiento.md`

En sección 1.2, corregir la llave compuesta:

```markdown
| Deduplicación | Por llave compuesta (`satellite`, `instrument`, `detected_at`, `latitude`, `longitude`, `fire_radiative_power`, `confidence_normalized`). Estrategia: hash SHA-256 ... |
```

(Ya incluido en T5)

---

## T9 — BAJO: Documentar geo-enrichment en pipeline de episodios

### Cambio en `docs/Carrusel fix/flujo_ingesta_procesamiento.md`

En sección 3.3, actualizar la tabla del worker:

```markdown
| Worker responsable | `cluster_fire_episodes_pipeline` (task beat: `cluster-episodes-daily`). Ejecuta una cadena Celery: (1) `cluster_fire_episodes` → (2) `enrich_recent_fire_events` (geo-enrichment: provincia, departamento) |
```

---

## Tests de ejecución local — flujo completo end-to-end

### Prerequisitos

```bash
# Instalar dependencias de test (si no están)
pip install pytest pytest-asyncio httpx

# Verificar conexión a BD
python -c "
from app.db.session import SessionLocal
db = SessionLocal()
result = db.execute('SELECT 1').scalar()
print('DB OK:', result)
db.close()
"
```

### Test 1: Import chain completo (post-T1)

```bash
python -c "
# Verificar toda la cadena de imports del pipeline
from workers.tasks.ingestion import download_firms_daily
from workers.tasks.clustering import cluster_detections
from workers.tasks.clustering_task import cluster_fire_episodes_pipeline
from workers.tasks.carousel_task import generate_carousel
from workers.tasks.cleanup_assets_task import cleanup_expired_assets
from workers.tasks.episode_merge_task import merge_episodes
from workers.tasks.notification import send_contact_email
print('Todos los imports OK')
print('Tasks registrados:', [
    download_firms_daily.name,
    cluster_detections.name,
    cluster_fire_episodes_pipeline.name,
    generate_carousel.name,
    cleanup_expired_assets.name,
    merge_episodes.name,
    send_contact_email.name,
])
"
```

### Test 2: Verificar routing de colas (post-T2, T3)

```bash
python -c "
from workers.celery_app import celery_app

tasks_to_check = {
    'workers.tasks.ingestion.download_firms_daily': 'ingestion',
    'workers.tasks.clustering.cluster_detections': 'clustering',
    'workers.tasks.clustering_task.cluster_fire_episodes_pipeline': 'clustering',
    'workers.tasks.carousel_task.generate_carousel': 'analysis',
    'workers.tasks.cleanup_assets_task.cleanup_expired_assets': 'analysis',
    'workers.tasks.notification.send_contact_email': 'notification',
    'workers.tasks.episode_merge_task.merge_episodes': 'clustering',
}

# Verificar que ningún task va a cola 'default' sin consumer
queues_with_consumer = {'ingestion', 'clustering', 'analysis', 'vae', 'reports', 'notification'}

for task_name, expected_queue in tasks_to_check.items():
    route = celery_app.conf.task_routes.get(task_name, {})
    actual_queue = route.get('queue', expected_queue)
    status = 'OK' if actual_queue in queues_with_consumer else 'FAIL (sin consumer)'
    print(f'  {task_name.split(\".\")[-1]:40s} → {actual_queue:15s} [{status}]')
"
```

### Test 3: Verificar beat schedule (post-T4)

```bash
python -c "
from workers.celery_app import celery_app

print('Beat schedule entries:')
for name, entry in sorted(celery_app.conf.beat_schedule.items()):
    task = entry['task'].split('.')[-1]
    schedule = entry['schedule']
    queue = entry.get('options', {}).get('queue', 'default')
    print(f'  {name:30s} → {task:40s} cola={queue:15s} schedule={schedule}')
"
```

### Test 4: Dry-run del pipeline de ingesta (post-T1)

```bash
# Requiere FIRMS_API_KEY y DATABASE_URL configurados
python -m scripts.maintenance.load_firms_incremental --dry-run --days 1
```

### Test 5: Verificar consistencia del celery_app raíz (post-T4)

```bash
python -c "
from celery_app import celery_app as root
from workers.celery_app import celery_app as canonical
assert root is canonical, 'ERROR: celery_app.py raíz no delega a workers.celery_app'
print('OK: celery_app.py raíz es proxy de workers.celery_app')
"
```

---

## Queries de validación del flujo de datos completo

### Q1 — Estado general del pipeline

```sql
-- Dashboard de salud del pipeline: últimas 72 horas
SELECT
    'fire_detections' AS tabla,
    COUNT(*) AS total_72h,
    COUNT(*) FILTER (WHERE is_processed = false AND fire_event_id IS NULL) AS pendientes_clustering,
    COUNT(*) FILTER (WHERE is_processed = true AND fire_event_id IS NOT NULL) AS asignadas_a_evento,
    COUNT(*) FILTER (WHERE is_processed = true AND fire_event_id IS NULL) AS ruido
FROM fire_detections
WHERE detected_at >= NOW() - INTERVAL '72 hours'

UNION ALL

SELECT
    'fire_events',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'active'),
    COUNT(*) FILTER (WHERE status = 'monitoring'),
    COUNT(*) FILTER (WHERE status = 'extinct')
FROM fire_events
WHERE created_at >= NOW() - INTERVAL '72 hours'

UNION ALL

SELECT
    'fire_episodes',
    COUNT(*),
    COUNT(*) FILTER (WHERE status = 'active'),
    COUNT(*) FILTER (WHERE status = 'monitoring'),
    COUNT(*) FILTER (WHERE status = 'extinct')
FROM fire_episodes
WHERE created_at >= NOW() - INTERVAL '72 hours';
```

### Q2 — Verificar deduplicación (T5)

```sql
-- Duplicados por detection_hash
SELECT detection_hash, COUNT(*) AS cnt
FROM fire_detections
WHERE detection_hash IS NOT NULL
GROUP BY detection_hash
HAVING COUNT(*) > 1
LIMIT 10;

-- Cobertura de hashes
SELECT
    COUNT(*) AS total,
    COUNT(detection_hash) AS con_hash,
    ROUND(100.0 * COUNT(detection_hash) / NULLIF(COUNT(*), 0), 1) AS pct_hash
FROM fire_detections
WHERE detected_at >= NOW() - INTERVAL '30 days';
```

### Q3 — Verificar clustering_version_id en eventos

```sql
-- Eventos sin versión de clustering asignada
SELECT
    COUNT(*) AS total_eventos,
    COUNT(clustering_version_id) AS con_version,
    COUNT(*) - COUNT(clustering_version_id) AS sin_version
FROM fire_events
WHERE created_at >= NOW() - INTERVAL '30 days';

-- Versión activa actual
SELECT id, version_name, epsilon_km, min_points, temporal_window_hours, algorithm, is_active
FROM clustering_versions
WHERE is_active = true;
```

### Q4 — Verificar relación episodios-eventos

```sql
-- Episodios sin eventos asociados (huérfanos)
SELECT e.id, e.status, e.event_count, e.created_at
FROM fire_episodes e
LEFT JOIN fire_episode_events fee ON fee.episode_id = e.id
WHERE fee.episode_id IS NULL
  AND e.status NOT IN ('closed')
ORDER BY e.created_at DESC
LIMIT 20;

-- Eventos sin episodio asociado
SELECT fe.id, fe.status, fe.start_date, fe.total_detections
FROM fire_events fe
LEFT JOIN fire_episode_events fee ON fee.event_id = fe.id
WHERE fee.event_id IS NULL
  AND fe.created_at >= NOW() - INTERVAL '30 days'
ORDER BY fe.start_date DESC
LIMIT 20;
```

### Q5 — Verificar fusiones de episodios

```sql
-- Últimas fusiones registradas
SELECT
    em.merged_at,
    em.reason,
    em.absorbed_episode_id,
    ea.status AS absorbed_status,
    em.absorbing_episode_id,
    eb.status AS absorbing_status,
    em.notes
FROM episode_mergers em
JOIN fire_episodes ea ON ea.id = em.absorbed_episode_id
JOIN fire_episodes eb ON eb.id = em.absorbing_episode_id
ORDER BY em.merged_at DESC
LIMIT 10;

-- Episodios absorbidos que NO quedaron en 'closed'
SELECT em.absorbed_episode_id, e.status, em.merged_at
FROM episode_mergers em
JOIN fire_episodes e ON e.id = em.absorbed_episode_id
WHERE e.status != 'closed';
```

### Q6 — Verificar estados coherentes

```sql
-- Eventos marcados como 'active' pero cuya última actividad excede la ventana de 168h
SELECT id, status, last_seen_at, end_date,
       EXTRACT(HOURS FROM NOW() - COALESCE(last_seen_at, end_date, start_date)) AS horas_desde_actividad
FROM fire_events
WHERE status = 'active'
  AND COALESCE(last_seen_at, end_date, start_date) < NOW() - INTERVAL '168 hours'
ORDER BY horas_desde_actividad DESC
LIMIT 20;

-- Episodios activos sin eventos activos (inconsistencia de estado)
SELECT e.id, e.status AS episode_status,
       ARRAY_AGG(DISTINCT fe.status) AS event_statuses
FROM fire_episodes e
JOIN fire_episode_events fee ON fee.episode_id = e.id
JOIN fire_events fe ON fe.id = fee.event_id
WHERE e.status = 'active'
GROUP BY e.id, e.status
HAVING NOT ('active' = ANY(ARRAY_AGG(fe.status)));
```

### Q7 — Verificar carrusel (slides_data)

```sql
-- Episodios activos/monitoring sin slides (candidatos a carrusel pendiente)
SELECT id, status, gee_candidate, gee_priority, last_seen_at
FROM fire_episodes
WHERE status IN ('active', 'monitoring')
  AND gee_candidate = true
  AND (slides_data IS NULL OR jsonb_array_length(slides_data) = 0)
ORDER BY gee_priority DESC NULLS LAST
LIMIT 20;

-- Distribución de slides por estado
SELECT
    status,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0) AS con_slides,
    COUNT(*) FILTER (WHERE gee_candidate = true) AS gee_candidates
FROM fire_episodes
GROUP BY status
ORDER BY status;
```

### Q8 — Verificar system_parameters

```sql
-- Parámetros canónicos del pipeline
SELECT param_key, param_value
FROM system_parameters
WHERE param_key IN (
    'event_spatial_epsilon_meters',
    'event_temporal_window_hours',
    'event_monitoring_window_hours',
    'episode_spatial_epsilon_meters',
    'episode_temporal_window_hours',
    'h3_resolution',
    'carousel_home_limit',
    'carousel_batch_size'
)
ORDER BY param_key;
```

### Q9 — Verificar colas huérfanas (post-T2, T3)

```sql
-- Si usás pgbouncer/pg_stat_activity, verificar que no hay tasks atascados.
-- Esta query es solo de contexto; la validación real es via Flower o Celery inspect.
```

```bash
# Verificar colas activas y tasks pendientes via CLI
celery -A workers.celery_app inspect active_queues
celery -A workers.celery_app inspect reserved
```

---

## Orden de ejecución recomendado

```
1. T1 (CRÍTICO) — Fix import ingesta
   └── Test 1 + Test 4 (dry-run)
   └── Q1 (después de un run real)

2. T4 (ALTO) — Proxy celery_app raíz
   └── Test 5

3. T2 (ALTO) — Reasignar cola cleanup
   └── Test 2 + Test 3

4. T3 (ALTO) — Agregar notification a worker-reports
   └── Test 2

5. T5-T9 (MEDIO/BAJO) — Actualizar documentación
   └── Q2-Q8 (validación post-deploy)

6. Ejecutar suite de tests existente
   └── pytest tests/unit/ -v
   └── Q6 (coherencia de estados)
```

---

## Checklist de validación post-deploy

- [ ] `python -c "from workers.tasks.ingestion import download_firms_daily"` no arroja error
- [ ] `python -c "from celery_app import celery_app; from workers.celery_app import celery_app as w; assert celery_app is w"`
- [ ] `celery -A workers.celery_app inspect active_queues` muestra `ingestion`, `clustering`, `analysis`, `vae`, `reports`, `notification`
- [ ] `pytest tests/unit/test_episode_status_resolver.py -v` pasa
- [ ] `pytest tests/unit/test_carousel_worker.py -v` pasa
- [ ] Q1 muestra detecciones recientes con `pendientes_clustering = 0` (después del clustering diario)
- [ ] Q2 muestra `cnt = 0` (sin duplicados por hash)
- [ ] Q6 muestra 0 filas (sin eventos activos vencidos)
- [ ] Q7 muestra episodios gee_candidate con slides generados
