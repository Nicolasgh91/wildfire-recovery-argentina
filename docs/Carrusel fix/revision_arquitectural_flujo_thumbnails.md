# Revisión arquitectural: flujo de thumbnails del carrusel

**Fecha:** 2026-02-25  
**Rol:** Arquitecto de software senior  
**Documento base:** `analisis_flujo_thumbnails_0bb3cc3a.plan.md`

---

## 1. Análisis crítico del plan propuesto

### 1.1 Contradicción fundamental: dos modelos de estado compiten

El plan identifica correctamente los GAP-1 y GAP-7, pero la solución propuesta ("heredar estado de eventos") **contradice directamente** el documento canónico `detailed_carousel_and_states_flow.md` y las tareas técnicas ya definidas en `carousel_technical_tasks.md`.

Documentación canónica vigente (tarea 1 de `carousel_technical_tasks.md`):

- Active: al menos 1 evento `active`
- Monitoring: no hay eventos `active`, pero no se superó la ventana de 720h desde `last_seen_at`
- Extinct: se superó la ventana de 720h sin actividad

El plan propone (GAP-1+7 TODO):

- Active: al menos 1 evento `active`
- Monitoring: al menos 1 evento `monitoring`, ninguno `active`
- Extinct: todos los eventos `extinct`

**Problema:** el modelo del plan elimina la ventana temporal y delega la transición `extinct` exclusivamente a los estados de eventos individuales. Esto genera un acoplamiento fuerte: si el worker `event_status_task` tiene un retraso o falla, los episodios quedan en `monitoring` indefinidamente. La documentación canónica tampoco es suficiente: si solo usa la ventana temporal sin verificar estados de eventos, un episodio podría declararse `extinct` mientras aún tiene eventos en `monitoring` (posible cuando `event_monitoring_window_hours > episode_temporal_window_hours`).

**Veredicto — modelo corregido con doble condición:**

- Active: al menos 1 evento `active`
- Monitoring: ningún evento `active` **Y** no se cumplen ambas condiciones de extinct
- Extinct: `now() - last_seen_at >= episode_temporal_window_hours` **Y** todos los eventos están `extinct`

La transición a `extinct` requiere la conjunción de ambas condiciones: la ventana temporal superada y la confirmación de que ningún evento sigue vivo. Esto combina las fortalezas de ambos modelos (ventana configurable + validación de estado real) y elimina los edge cases de cada uno por separado. `episode_temporal_window_hours = 720` sigue siendo configurable vía `system_parameters`.

### 1.2 GAP-2: `extinct_at` no existe en `fire_episodes`

El plan dice "setear `extinct_at = NOW()` en `update_episode_metrics`", pero el schema v5 confirma que `fire_episodes` **no tiene columna `extinct_at`**. Solo `fire_events` la tiene. Esto requiere una migración DDL que el plan no contempla.

### 1.3 GAP-3: el modelo `satellite_images` sin `episode_id` es un defecto de diseño real

El plan lo marca como "evaluar", pero es un problema concreto con impacto operacional:

- La cache se invalida cuando el evento representativo cambia (rotación natural en episodios activos)
- No hay forma de consultar "todas las imágenes de un episodio" sin hacer JOIN a través de `fire_episode_events`
- El `ON DELETE CASCADE` sobre `fire_event_id` puede destruir thumbnails válidos si un evento se absorbe en un merge

**Decisión recomendada:** agregar `episode_id` como FK nullable en `satellite_images`. Migrar datos existentes con un backfill. Cambiar la cache key a `episode_id + gee_system_index + vis_params`.

### 1.4 GAP-4: inconsistencia silenciosa entre generación y consulta

El API endpoint deprecated incluye `extinct` recientes (60 días) pero el carousel worker solo genera para `active/monitoring`. Esto produce un estado fantasma: la UI muestra tarjetas con `slides_data` stale o vacío para episodios que deberían tener imágenes frescas.

**Decisión recomendada:** el carousel worker debe generar thumbnails para episodios `extinct` cuyo `extinct_at < 30 días`. Alinear con la política de `episode_closer_task.py` (30 días para `closed`).

### 1.5 GAP-5: `slides_data` sin limpieza es deuda técnica aceptable a corto plazo

Con OCI Object Storage y URLs directas (no presignadas), las URLs no expiran. Prioridad baja. Documentar como deuda técnica con ticket pendiente.

### 1.6 Problema no identificado: atomicidad del rollback parcial

El plan documenta que si no se generan los 3 slides se hace ROLLBACK, pero no aclara qué pasa con los archivos ya subidos a OCI. Un rollback de DB no borra assets de storage. Esto genera huérfanos en el bucket.

### 1.7 Problema no identificado: ausencia de idempotencia en re-ejecución manual

Si `generate_carousel` se ejecuta dos veces el mismo día (manual + beat), puede duplicar imágenes en storage porque el cleanup previo borra por `fire_event_id` del representativo actual, no por `episode_id`.

---

## 2. Diagrama de flujo corregido

```
+------------------------------------------------------------------+
|                    PIPELINE DIARIO (BEAT)                         |
+------------------------------------------------------------------+
|                                                                  |
|  00:00 UTC  ingestion.py (FIRMS download)                        |
|      |                                                           |
|      v                                                           |
|  01:00 UTC  clustering.py (ST-DBSCAN -> fire_events)             |
|      |                                                           |
|      v                                                           |
|  01:30 UTC  event_status_task.py (active/monitoring/extinct)     |
|      |                                                           |
|      v                                                           |
|  01:45 UTC  geo_enrichment.py (provincia, departamento)          |
|      |                                                           |
|      v                                                           |
|  02:00 UTC  clustering_task.py (episode aggregation)             |
|      |                                                           |
|      +---> update_episode_metrics()                              |
|      |         |                                                 |
|      |         +---> _resolve_episode_status()                   |
|      |         |         |                                       |
|      |         |         +--[al menos 1 evento active]           |
|      |         |         |       => episode.status = 'active'    |
|      |         |         |                                       |
|      |         |         +--[elapsed >= 720h desde last_seen_at  |
|      |         |         |   Y todos los eventos extinct]        |
|      |         |         |       => episode.status = 'extinct'   |
|      |         |         |       => episode.extinct_at = NOW()   |
|      |         |         |                                       |
|      |         |         +--[cualquier otro caso]                |
|      |         |                 => episode.status = 'monitoring'|
|      |         |                                                 |
|      |         +---> recalcular gee_candidate, gee_priority      |
|      |                                                           |
|      v                                                           |
|  03:00 UTC  carousel_task.py                                     |
|      |                                                           |
|      +---> Redis distributed lock (30min TTL)                    |
|      |                                                           |
|      +---> _fetch_priority_episodes()                            |
|      |         SELECT FROM fire_episodes                         |
|      |         WHERE status IN ('active','monitoring')           |
|      |           OR (status = 'extinct'                          |
|      |               AND extinct_at > NOW() - INTERVAL '30d')   |
|      |         AND gee_candidate = true                          |
|      |         ORDER BY gee_priority DESC, start_date DESC       |
|      |         LIMIT batch_size                                  |
|      |                                                           |
|      +---> FOR EACH episode:                                     |
|      |       |                                                   |
|      |       +---> buscar evento representativo                  |
|      |       |       (mas reciente active/monitoring)             |
|      |       |                                                   |
|      |       +---> cache check (episode_id + scene + vis)        |
|      |       |       si 3 vis cached con misma imagen => SKIP    |
|      |       |                                                   |
|      |       +---> GEE: buscar Sentinel-2                        |
|      |       |       thresholds: 10% -> 20% -> 30% -> 50%       |
|      |       |       ventana: 7d, fallback 30d                   |
|      |       |                                                   |
|      |       +---> verificar last_gee_image_id                   |
|      |       |       si misma imagen => SKIP                     |
|      |       |                                                   |
|      |       +---> limpiar satellite_images previas              |
|      |       |       (por episode_id, tipo 'carousel')           |
|      |       |                                                   |
|      |       +---> FOR EACH vis (SWIR, RGB, NBR):                |
|      |       |       download 768x576 bicubic                    |
|      |       |       apply_watermark()                           |
|      |       |       upload -> carousel/{episode_id}/{vis}_{d}   |
|      |       |       INSERT satellite_images                     |
|      |       |                                                   |
|      |       +---> si 3/3 slides OK:                             |
|      |       |       UPDATE fire_episodes.slides_data            |
|      |       |       UPDATE last_gee_image_id, last_update_sat   |
|      |       |       COMMIT                                      |
|      |       |                                                   |
|      |       +---> si < 3 slides:                                |
|      |               ROLLBACK DB                                 |
|      |               cleanup_orphan_assets(episode_id)           |
|      |                                                           |
|      v                                                           |
|  04:00 UTC  cleanup_assets_task.py (assets expirados)            |
|      |                                                           |
|      v                                                           |
|  05:00 UTC  episode_closer_task.py                               |
|               WHERE status = 'extinct'                           |
|               AND extinct_at < NOW() - INTERVAL '30d'            |
|               => status = 'closed'                               |
|               => slides_data = '[]'                              |
+------------------------------------------------------------------+

+------------------------------------------------------------------+
|                    API / FRONTEND                                 |
+------------------------------------------------------------------+
|                                                                  |
|  GET /fire-episodes?mode=active                                  |
|      WHERE (status IN ('active','monitoring')                    |
|             OR (status = 'extinct'                               |
|                 AND extinct_at > NOW() - INTERVAL '30d'))        |
|      AND gee_candidate = true                                    |
|      AND slides_data IS NOT NULL                                 |
|      AND jsonb_array_length(slides_data) > 0                     |
|      ORDER BY gee_priority DESC                                  |
+------------------------------------------------------------------+
```

---

## 3. Tareas técnicas de corrección

### T-01: migración DDL — agregar `extinct_at` a `fire_episodes`

**Archivo:** nueva migración SQL  
**Esfuerzo:** 0.5h  
**Dependencias:** ninguna  

```sql
ALTER TABLE public.fire_episodes
  ADD COLUMN IF NOT EXISTS extinct_at TIMESTAMP WITH TIME ZONE;

-- Backfill: episodios ya extinct sin fecha
UPDATE fire_episodes
SET extinct_at = updated_at
WHERE status = 'extinct' AND extinct_at IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_fire_episodes_extinct_at ON fire_episodes (extinct_at)
  WHERE status = 'extinct';
```

**Criterios de aceptación:**
- La columna existe y acepta NULL
- Episodios previamente `extinct` tienen `extinct_at` poblado
- El índice parcial está creado

### T-02: migración DDL — agregar `episode_id` a `satellite_images`

**Archivo:** nueva migración SQL  
**Esfuerzo:** 1h  
**Dependencias:** ninguna  

```sql
ALTER TABLE public.satellite_images
  ADD COLUMN IF NOT EXISTS episode_id UUID
  REFERENCES fire_episodes(id) ON DELETE SET NULL;

-- Backfill desde fire_episode_events
UPDATE satellite_images si
SET episode_id = fee.episode_id
FROM fire_episode_events fee
WHERE si.fire_event_id = fee.event_id
  AND si.episode_id IS NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS
  idx_satellite_images_episode_id ON satellite_images (episode_id)
  WHERE episode_id IS NOT NULL;
```

**Criterios de aceptación:**
- FK a `fire_episodes` con `ON DELETE SET NULL` (no CASCADE)
- Imágenes existentes tienen `episode_id` poblado donde hay relación
- Índice parcial creado

### T-03: refactorizar `_resolve_episode_status` con modelo canónico

**Archivo:** `app/services/episode_service.py`, método `_resolve_episode_status`  
**Esfuerzo:** 1.5h  
**Dependencias:** T-01  

Implementar las tres reglas canónicas con doble condición para extinct:

1. Si `"active" in event_statuses` → retornar `"active"`
2. Si `elapsed_since_last_seen >= episode_temporal_window_hours` **Y** todos los eventos están `extinct` → retornar `"extinct"`
3. Cualquier otro caso → retornar `"monitoring"`

La regla 3 cubre los siguientes escenarios:
- Hay eventos en `monitoring` pero ninguno `active` (monitoreo estándar)
- Se superó la ventana temporal pero aún hay eventos en `monitoring` (protección contra desincronización de workers)
- Todos los eventos están `extinct` pero no se superó la ventana (periodo de gracia para detección de cicatrices)

**Criterios de aceptación:**
- No existe lógica de ventana temporal hardcodeada
- Se lee `episode_temporal_window_hours` desde `system_parameters` (fallback 720)
- `last_seen_at` se usa como referencia temporal (no `updated_at`)
- La transición a `extinct` requiere **ambas** condiciones: ventana superada Y todos los eventos extinct
- Manejo de timezone correcto (`tzinfo=timezone.utc`)

### T-04: setear `extinct_at` automáticamente en `update_episode_metrics`

**Archivo:** `app/services/episode_service.py`, método `update_episode_metrics`  
**Esfuerzo:** 0.5h  
**Dependencias:** T-01, T-03  

En la sección donde se persiste el nuevo status (línea ~529+), agregar:

```python
if new_status == "extinct" and (old_status != "extinct"):
    episode.extinct_at = datetime.now(timezone.utc)
elif new_status in ("active", "monitoring"):
    episode.extinct_at = None  # reactivación limpia
```

**Criterios de aceptación:**
- Transición a `extinct` setea `extinct_at = NOW()`
- Reactivación (extinct → active/monitoring) limpia `extinct_at`
- No se sobreescribe `extinct_at` si el episodio ya era `extinct`

### T-05: ampliar `_fetch_priority_episodes` para incluir `extinct` recientes

**Archivo:** `app/services/imagery_service.py`, método `_fetch_priority_episodes`  
**Esfuerzo:** 1h  
**Dependencias:** T-01, T-04  

Modificar la query SQL:

```sql
WHERE (status IN ('active', 'monitoring')
       OR (status = 'extinct'
           AND extinct_at > NOW() - INTERVAL '30 days'))
  AND gee_candidate = true
```

**Criterios de aceptación:**
- Episodios `extinct` con menos de 30 días reciben thumbnails
- El intervalo es configurable vía `system_parameters` (parámetro `carousel_extinct_grace_days`, fallback 30)
- La query mantiene el ORDER BY por `gee_priority DESC`

### T-06: migrar cache key de `fire_event_id` a `episode_id`

**Archivo:** `app/services/gee_scene_cache.py`, `app/services/imagery_service.py`  
**Esfuerzo:** 1.5h  
**Dependencias:** T-02  

Cambiar `find_cached_scene()` para buscar por `episode_id` en lugar de `fire_event_id`. Actualizar `_process_episode()` para:
- Pasar `episode_id` al insertar en `satellite_images`
- Limpiar imágenes previas por `episode_id` (no por `fire_event_id`)

**Criterios de aceptación:**
- Rotación de evento representativo no invalida la cache
- DELETE previo usa `WHERE episode_id = :eid AND image_type = 'carousel'`
- Nuevos INSERT incluyen `episode_id`

### T-07: limpieza de assets huérfanos en rollback parcial

**Archivo:** `app/services/imagery_service.py`, método `_process_episode`  
**Esfuerzo:** 1h  
**Dependencias:** ninguna  

Después del ROLLBACK de DB, agregar limpieza de assets ya subidos a OCI:

```python
except Exception:
    db.rollback()
    for uploaded_key in uploaded_keys:
        try:
            storage_service.delete(uploaded_key)
        except Exception:
            logger.warning(f"Orphan asset: {uploaded_key}")
    raise
```

**Criterios de aceptación:**
- Fallo parcial (1-2 de 3 slides) no deja PNGs huérfanos en OCI
- Los errores de limpieza se loguean pero no ocultan el error original

### T-08: alinear endpoint API con política de visibilidad del carousel

**Archivo:** `app/api/routes/episodes.py`  
**Esfuerzo:** 0.5h  
**Dependencias:** T-01, T-05  

Reemplazar la condición del endpoint activo:

```sql
WHERE (status IN ('active', 'monitoring')
       OR (status = 'extinct'
           AND extinct_at > NOW() - INTERVAL '30 days'))
  AND gee_candidate = true
  AND slides_data IS NOT NULL
  AND jsonb_array_length(slides_data) > 0
```

**Criterios de aceptación:**
- API y carousel worker usan la misma política de visibilidad
- El endpoint deprecated se marca con `@deprecated` en docstring
- Episodios `extinct` recientes con slides aparecen en el feed

### T-09: sincronizar `system_parameters` en producción

**Archivo:** script SQL o migración  
**Esfuerzo:** 0.5h  
**Dependencias:** ninguna  

```sql
INSERT INTO system_parameters (param_key, param_value, description)
VALUES
  ('episode_temporal_window_hours', '720',
   'Ventana de inactividad para transición a extinct (30 días)'),
  ('carousel_extinct_grace_days', '30',
   'Días post-extinct donde el episodio sigue recibiendo thumbnails')
ON CONFLICT (param_key)
DO UPDATE SET param_value = EXCLUDED.param_value;
```

**Criterios de aceptación:**
- Parámetros existen en producción
- `episode_flow_parameters.py` los lee correctamente

### T-10: actualizar documentación de workers

**Archivo:** `docs/flujo_ingesta_procesamiento.md`  
**Esfuerzo:** 0.5h  
**Dependencias:** ninguna  

Actualizar tabla de workers con:

| Worker | UTC | Queue |
|--------|-----|-------|
| event_status_task | 01:30 | clustering |
| geo_enrichment | 01:45 | clustering |
| episode_closer_task | 05:00 | default |

**Criterios de aceptación:**
- La tabla incluye todos los workers activos con horarios reales
- No hay discrepancias con `celery_app.py` beat_schedule

---

## 4. Orden de ejecución (dependencias)

```
T-09 (params DB)         T-10 (docs)        T-07 (orphan cleanup)
     |                       |                      |
     v                       v                      v
T-01 (extinct_at DDL) ---> T-03 (resolve_status) ---> T-04 (auto extinct_at)
     |                                                      |
     v                                                      v
T-02 (episode_id DDL) ---> T-06 (cache key)          T-05 (fetch extinct)
                                                            |
                                                            v
                                                      T-08 (API align)
```

Paralelizables: T-07, T-09, T-10 pueden ejecutarse en cualquier orden.  
Ruta crítica: T-01 → T-03 → T-04 → T-05 → T-08.

---

## 5. Tests de regresión

### 5.1 Unit tests — `_resolve_episode_status`

```python
# test_episode_status.py

class TestResolveEpisodeStatus:
    """Validar las reglas canónicas con doble condición para extinct."""

    def test_active_when_any_event_active(self):
        """Al menos 1 evento active => episodio active."""
        statuses = ["active", "monitoring", "extinct"]
        result = _resolve_episode_status(statuses, last_seen_at=now(), window=720)
        assert result == "active"

    def test_monitoring_when_no_active_within_window(self):
        """Sin eventos active, dentro de ventana => monitoring."""
        statuses = ["monitoring", "extinct"]
        last_seen = now() - timedelta(hours=100)  # < 720h
        result = _resolve_episode_status(statuses, last_seen, window=720)
        assert result == "monitoring"

    def test_extinct_requires_both_conditions(self):
        """Extinct solo si ventana superada Y todos eventos extinct."""
        statuses = ["extinct", "extinct"]
        last_seen = now() - timedelta(hours=721)
        result = _resolve_episode_status(statuses, last_seen, window=720)
        assert result == "extinct"

    def test_monitoring_all_extinct_but_within_window(self):
        """Todos extinct pero dentro de ventana => monitoring (periodo de gracia)."""
        statuses = ["extinct", "extinct"]
        last_seen = now() - timedelta(hours=500)  # < 720h
        result = _resolve_episode_status(statuses, last_seen, window=720)
        assert result == "monitoring"

    def test_monitoring_window_exceeded_but_event_still_monitoring(self):
        """Ventana superada pero hay evento monitoring => monitoring (doble condición)."""
        statuses = ["monitoring", "extinct"]
        last_seen = now() - timedelta(hours=800)  # > 720h
        result = _resolve_episode_status(statuses, last_seen, window=720)
        assert result == "monitoring"

    def test_monitoring_window_exceeded_event_still_active(self):
        """Ventana superada pero hay evento active => active (regla 1 prevalece)."""
        statuses = ["active", "extinct"]
        last_seen = now() - timedelta(hours=800)
        result = _resolve_episode_status(statuses, last_seen, window=720)
        assert result == "active"

    def test_active_single_event(self):
        """Episodio con un solo evento active."""
        result = _resolve_episode_status(["active"], now(), 720)
        assert result == "active"

    def test_empty_events_returns_extinct(self):
        """Sin eventos (edge case) => extinct (no hay eventos no-extinct)."""
        result = _resolve_episode_status([], now() - timedelta(hours=800), 720)
        assert result == "extinct"

    def test_empty_events_within_window_returns_monitoring(self):
        """Sin eventos pero dentro de ventana => monitoring."""
        result = _resolve_episode_status([], now() - timedelta(hours=100), 720)
        assert result == "monitoring"

    def test_timezone_naive_last_seen_raises(self):
        """last_seen_at sin timezone debe fallar explícitamente."""
        with pytest.raises((TypeError, ValueError)):
            _resolve_episode_status(["monitoring"], datetime(2026, 1, 1), 720)
```

### 5.2 Unit tests — `update_episode_metrics` (extinct_at)

```python
class TestExtinctAtAutomation:
    """Validar seteo automático de extinct_at."""

    def test_transition_to_extinct_sets_extinct_at(self):
        """monitoring -> extinct debe setear extinct_at."""
        episode = make_episode(status="monitoring", extinct_at=None)
        update_episode_metrics(episode, new_status="extinct")
        assert episode.extinct_at is not None
        assert episode.extinct_at.tzinfo is not None

    def test_reactivation_clears_extinct_at(self):
        """extinct -> active debe limpiar extinct_at."""
        episode = make_episode(status="extinct", extinct_at=now())
        update_episode_metrics(episode, new_status="active")
        assert episode.extinct_at is None

    def test_already_extinct_preserves_extinct_at(self):
        """extinct -> extinct no sobreescribe extinct_at."""
        original_time = now() - timedelta(days=5)
        episode = make_episode(status="extinct", extinct_at=original_time)
        update_episode_metrics(episode, new_status="extinct")
        assert episode.extinct_at == original_time
```

### 5.3 Integration tests — carousel worker

```python
class TestCarouselFetchPriority:
    """Validar selección de candidatos incluyendo extinct recientes."""

    def test_includes_active_episodes(self, db):
        ep = create_episode(db, status="active", gee_candidate=True)
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id in [r.id for r in results]

    def test_includes_monitoring_episodes(self, db):
        ep = create_episode(db, status="monitoring", gee_candidate=True)
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id in [r.id for r in results]

    def test_includes_recent_extinct(self, db):
        ep = create_episode(db, status="extinct", gee_candidate=True,
                           extinct_at=now() - timedelta(days=15))
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id in [r.id for r in results]

    def test_excludes_old_extinct(self, db):
        ep = create_episode(db, status="extinct", gee_candidate=True,
                           extinct_at=now() - timedelta(days=45))
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id not in [r.id for r in results]

    def test_excludes_closed(self, db):
        ep = create_episode(db, status="closed", gee_candidate=True)
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id not in [r.id for r in results]

    def test_excludes_non_gee_candidate(self, db):
        ep = create_episode(db, status="active", gee_candidate=False)
        results = _fetch_priority_episodes(db, batch_size=10)
        assert ep.id not in [r.id for r in results]
```

### 5.4 Integration tests — cache por `episode_id`

```python
class TestCacheByEpisodeId:
    """Validar que la cache usa episode_id, no fire_event_id."""

    def test_cache_hit_same_episode_different_event(self, db):
        """Rotación de evento representativo no invalida cache."""
        ep = create_episode(db)
        event_a = create_event(db)
        event_b = create_event(db)
        link_event_to_episode(db, event_a, ep)
        link_event_to_episode(db, event_b, ep)

        # Crear satellite_images para event_a con episode_id
        create_sat_image(db, event_a.id, ep.id, vis="SWIR", scene="S2A_20260101")
        create_sat_image(db, event_a.id, ep.id, vis="RGB", scene="S2A_20260101")
        create_sat_image(db, event_a.id, ep.id, vis="NBR", scene="S2A_20260101")

        # Cache check por episode_id debe dar HIT
        cached = find_cached_scene(db, episode_id=ep.id, scene="S2A_20260101")
        assert len(cached) == 3

    def test_cleanup_by_episode_id(self, db):
        """Limpieza de imágenes previas usa episode_id."""
        ep = create_episode(db)
        old_img = create_sat_image(db, event_id=uuid4(), episode_id=ep.id)

        cleanup_previous_images(db, episode_id=ep.id)
        assert db.query(SatelliteImage).filter_by(id=old_img.id).first() is None
```

### 5.5 Integration test — rollback con limpieza de storage

```python
class TestRollbackCleansStorage:
    """Validar que rollback parcial limpia assets de OCI."""

    def test_partial_failure_cleans_uploaded_assets(self, db, mock_storage):
        """Si solo 2/3 slides se generan, los 2 subidos se borran."""
        mock_storage.upload_bytes.side_effect = [
            "carousel/ep1/swir_20260101.png",  # OK
            "carousel/ep1/rgb_20260101.png",   # OK
            StorageError("upload failed"),      # FAIL
        ]

        with pytest.raises(ProcessingError):
            _process_episode(db, episode, mock_storage)

        # Verificar que se intentó borrar los 2 assets subidos
        assert mock_storage.delete.call_count == 2
        deleted_keys = [c.args[0] for c in mock_storage.delete.call_args_list]
        assert "carousel/ep1/swir_20260101.png" in deleted_keys
        assert "carousel/ep1/rgb_20260101.png" in deleted_keys
```

### 5.6 Regression test — API alineado con carousel worker

```python
class TestAPICarouselAlignment:
    """El API debe retornar exactamente los mismos episodios que el worker genera."""

    def test_api_includes_extinct_with_slides(self, client, db):
        ep = create_episode(db, status="extinct", gee_candidate=True,
                           extinct_at=now() - timedelta(days=10),
                           slides_data=[{"type": "rgb"}, {"type": "swir"}, {"type": "nbr"}])
        resp = client.get("/fire-episodes?mode=active")
        ids = [e["id"] for e in resp.json()]
        assert str(ep.id) in ids

    def test_api_excludes_extinct_without_slides(self, client, db):
        ep = create_episode(db, status="extinct", gee_candidate=True,
                           extinct_at=now() - timedelta(days=10),
                           slides_data=[])
        resp = client.get("/fire-episodes?mode=active")
        ids = [e["id"] for e in resp.json()]
        assert str(ep.id) not in ids
```

---

## 6. Resumen de esfuerzo estimado

| Tarea | Esfuerzo | Prioridad |
|-------|----------|-----------|
| T-01: DDL extinct_at | 0.5h | Crítica |
| T-02: DDL episode_id en satellite_images | 1h | Alta |
| T-03: Refactor _resolve_episode_status | 1.5h | Crítica |
| T-04: Auto extinct_at | 0.5h | Crítica |
| T-05: Fetch extinct recientes | 1h | Alta |
| T-06: Cache key por episode_id | 1.5h | Alta |
| T-07: Orphan cleanup | 1h | Media |
| T-08: API alignment | 0.5h | Alta |
| T-09: System parameters | 0.5h | Crítica |
| T-10: Documentación workers | 0.5h | Baja |
| **Total** | **8.5h** | |
