# Task Execution Log (episode creation flow)

## Convenciones
- Un bloque por tarea cerrada (Phase 0, FG-EP-20, ...).
- Incluir exactamente: sanity checks SQL, comandos ejecutados, evidencia.
- Registrar fecha/hora ISO por bloque.

## Template
### <TASK-ID> - <TÍTULO>
- Fecha/hora (ISO): <yyyy-mm-ddThh:mm:ssZ>

Sanity checks SQL
- <sql 1>
- <sql 2>
- <sql 3 opcional>

Comandos ejecutados
- `<comando 1>`
- `<comando 2>`

Evidencia
- <resultado clave 1>
- <resultado clave 2>

---
### FG-EP-24 - Regla 1:N en `fire_episode_events` + reasignación transaccional
- Fecha/hora (ISO): 2026-02-13T21:52:10Z

Sanity checks SQL
- `SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' AND tablename='fire_episode_events' AND indexname='ux_fire_episode_events_event_id';`
- `SELECT COUNT(*) FROM (SELECT event_id FROM public.fire_episode_events GROUP BY event_id HAVING COUNT(*) > 1) t;`
- `SELECT COUNT(*) FROM public.fire_episode_events;`

Comandos ejecutados
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini revision -m "fg_ep_24_enforce_fire_episode_events_1n"` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` (desde `database/`)
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_episode_flow_parameters.py tests/unit/test_fire_status_canonical.py tests/unit/test_detection_clustering_service.py tests/unit/test_closure_report_service.py tests/unit/test_fire_service.py tests/integration/test_fg_ep_20_last_seen_at.py tests/integration/test_fg_ep_21_fire_events_status.py tests/integration/test_fg_ep_22_system_parameters.py tests/integration/test_fg_ep_23_episode_end_date_trigger.py tests/integration/test_fg_ep_24_episode_event_uniqueness.py tests/integration/test_fire_episodes_modes.py -q`
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre `TEST_DATABASE_URL`)

Evidencia
- Migración aplicada local: `488c97acc011 -> af536f2a144a`.
- Índice único creado: `episode_event_unique_index_count=1`.
- Integridad 1:N verificada en DB: `duplicate_event_ids=0`.
- Reasignación `EpisodeService.assign_event` validada sin ruta silenciosa (`DELETE + INSERT` en una transacción).
- Tests FG-EP-24 + regresión completa FG-EP-20..23/baseline: `30 passed`.

---
### FG-EP-23 - Enforzar semántica de `fire_episodes.end_date` con trigger
- Fecha/hora (ISO): 2026-02-13T21:47:46Z

Sanity checks SQL
- `SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_enforce_episode_end_date' AND tgrelid='public.fire_episodes'::regclass AND NOT tgisinternal);`
- `SELECT COUNT(*) FROM public.fire_episodes WHERE status <> 'closed' AND end_date IS NOT NULL;`
- `SELECT COUNT(*) FROM public.fire_episodes WHERE status = 'closed' AND end_date IS NULL;`

Comandos ejecutados
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini revision -m "fg_ep_23_enforce_fire_episodes_end_date_trigger"` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` (desde `database/`)
- `.\.venv\Scripts\python.exe -m pytest tests/integration/test_fg_ep_23_episode_end_date_trigger.py tests/integration/test_fire_episodes_modes.py tests/integration/test_fg_ep_22_system_parameters.py tests/integration/test_fg_ep_21_fire_events_status.py tests/integration/test_fg_ep_20_last_seen_at.py tests/unit/test_episode_flow_parameters.py -q`
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre `TEST_DATABASE_URL`)

Evidencia
- Migración aplicada local: `7196f62a30d4 -> 488c97acc011`.
- Sanity: `episode_end_date_trigger_exists=True`, `non_closed_with_end_date=0`, `closed_without_end_date=0`.
- Trigger valida `COALESCE(NEW.end_date, NEW.last_seen_at, now())` para `status='closed'` y fuerza `NULL` en no-closed.
- Tests FG-EP-23 + regresión secuencial: `18 passed`.

---
### FG-EP-22 - Parámetros canónicos en `system_parameters` + política fallback/prod
- Fecha/hora (ISO): 2026-02-13T21:44:12Z

Sanity checks SQL
- `SELECT param_key, param_value FROM public.system_parameters WHERE param_key IN ('event_spatial_epsilon_meters','event_temporal_window_hours','event_monitoring_window_hours','episode_spatial_epsilon_meters','episode_temporal_window_hours') ORDER BY param_key;`
- `SELECT COUNT(*) FROM public.system_parameters WHERE param_key IN ('event_spatial_epsilon_meters','event_temporal_window_hours','event_monitoring_window_hours','episode_spatial_epsilon_meters','episode_temporal_window_hours');`
- `SELECT COUNT(*) FROM public.system_parameters WHERE param_key IN (...) AND param_value IS NULL;`

Comandos ejecutados
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini revision -m "fg_ep_22_insert_canonical_system_parameters"` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` (desde `database/`)
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_episode_flow_parameters.py tests/integration/test_fg_ep_22_system_parameters.py tests/unit/test_detection_clustering_service.py tests/unit/test_fire_service.py tests/integration/test_fg_ep_21_fire_events_status.py tests/integration/test_fg_ep_20_last_seen_at.py tests/integration/test_fire_episodes_modes.py -q`
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre `TEST_DATABASE_URL`)

Evidencia
- Migración aplicada local: `dcdc9d71a209 -> 7196f62a30d4`.
- Sanity: `canonical_keys_found=5`, `canonical_keys_missing=[]`.
- Valores presentes en DB para las 5 claves canónicas con formato JSONB (`{"value": ...}`).
- Política fallback/prod validada por unit tests (`dev/test` fallback permitido; `production` lanza error explícito si faltan tabla/keys): batería en verde `20 passed`.

---
### FG-EP-21 - Normalización canónica de `fire_events.status`
- Fecha/hora (ISO): 2026-02-13T21:37:58Z

Sanity checks SQL
- `SELECT COUNT(*) FROM public.fire_events WHERE status IN ('controlled', 'extinguished');`
- `SELECT COUNT(*) FROM public.fire_events WHERE status IS NOT NULL AND status NOT IN ('active','monitoring','extinct');`
- `SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='public.fire_events'::regclass AND conname='fire_events_status_check';`

Comandos ejecutados
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini revision -m "fg_ep_21_normalize_fire_events_status"` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` (desde `database/`)
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_fire_status_canonical.py tests/integration/test_fg_ep_21_fire_events_status.py tests/unit/test_closure_report_service.py tests/unit/test_fire_service.py tests/unit/test_detection_clustering_service.py tests/integration/test_fg_ep_20_last_seen_at.py tests/integration/test_fire_episodes_modes.py -q`
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre `TEST_DATABASE_URL`)

Evidencia
- Migración aplicada local: `a158030ab842 -> dcdc9d71a209`.
- Sanity: `legacy_status_rows=0`, `non_canonical_status_rows=0`, `status_columns=[('extinct_at',)]`.
- Constraint activo: `fire_events_status_check` con set `active|monitoring|extinct`.
- Tests de FG-EP-21 + regresión FG-EP-20/baseline: `19 passed`.

---
### FG-EP-20 - `fire_events.last_seen_at` + backfill + sync por detección
- Fecha/hora (ISO): 2026-02-13T21:30:35Z

Sanity checks SQL
- `SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='fire_events' AND column_name='last_seen_at');`
- `SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' AND tablename='fire_events' AND indexname='idx_fire_events_last_seen_at';`
- `SELECT COUNT(*) FROM public.fire_events e WHERE EXISTS (SELECT 1 FROM public.fire_detections d WHERE d.fire_event_id = e.id) AND e.last_seen_at IS NULL;`

Comandos ejecutados
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini heads` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini revision -m "fg_ep_20_add_fire_events_last_seen_at"` (desde `database/`)
- `..\.venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head` (desde `database/`)
- `.\.venv\Scripts\python.exe -m pytest tests/unit/test_detection_clustering_service.py tests/integration/test_fg_ep_20_last_seen_at.py tests/unit/test_fire_service.py tests/integration/test_fire_episodes_modes.py -q`
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre `TEST_DATABASE_URL`)

Evidencia
- Migración aplicada local: `a1b2c3d4e5f6 -> a158030ab842`.
- Sanity: `last_seen_column_exists=True`, `last_seen_index_count=1`, `events_with_detections_and_null_last_seen=0`, `sync_trigger_exists=True`.
- Tests FG-EP-20 y regresión mínima: `10 passed`.

---
### Phase 0 - Precondiciones y baseline tests
- Fecha/hora (ISO): 2026-02-13T21:20:47Z

Sanity checks SQL
- `SELECT COUNT(*) FROM fire_episodes;`
- `SELECT COUNT(*) FROM fire_episodes WHERE end_date IS NOT NULL AND end_date >= NOW() - INTERVAL '60 days';`

Comandos ejecutados
- `.\.venv\Scripts\python.exe -m pytest tests/integration/test_fire_episodes_modes.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests/integration/test_fire_episodes_modes.py -q` (re-ejecuciones tras fix)
- `@'...python/sql...'@ | .\.venv\Scripts\python.exe -` (sanity SQL sobre TEST_DATABASE_URL)

Evidencia
- `tests/integration/test_fire_episodes_modes.py`: 3 passed.
- `fire_episodes_total=1858` y `fire_episodes_recent60=50` en base de test.
- Eliminado redirect 307 para `GET /api/v1/fire-episodes` con alias de ruta sin slash.

---
