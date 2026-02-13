# Plan Secuencial FG-EP-20..24 con Gates, Tests y Deuda Técnica

## Resumen
- Skill usage: no aplica ningún skill listado para esta tarea.
- Vamos a ejecutar FG-EP-20 a FG-EP-24 en orden estricto, sin avanzar de tarea hasta cumplir implementación + tests + tests en verde + documentación/deuda técnica.
- Fuente ejecutable de migraciones: Alembic (`database/alembic/versions`).
- Artefacto espejo solicitado: SQL package en `episode_creation_flow/migrations/episode_refactor_v4_corrections/`.
- Decisiones ya fijadas por vos: renombrar `extinguished_at -> extinct_at`, usar trigger para `end_date`, enforzar 1:N con `UNIQUE`, incluir scripts clave, compatibilidad API de corte limpio (sin `extinguished_at`), y arreglar primero fallas baseline.

## Regla de Gate por tarea
1. Implementación completa de la tarea.
2. Tests unitarios/integración de la tarea creados o actualizados.
3. Tests de la tarea en verde.
4. Registro en `episode_creation_flow/technical_debt.md` con timestamp ISO, contexto, síntoma, causa, impacto, propuesta y prioridad.
5. Recién ahí se avanza a la siguiente tarea.

## Fase 0 (antes de FG-EP-20)
1. Crear `episode_creation_flow/technical_debt.md` con la estructura exacta pedida.
2. Corregir baseline preexistente: `tests/integration/test_fire_episodes_modes.py` hoy falla por `307` en `/api/v1/fire-episodes` (redirect por slash).
3. Ajuste de ruta para eliminar redirect y dejar estable `200/400` en modo test/API.
4. Crear estructura espejo SQL:
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/README.md`
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/001_add_fire_events_last_seen_at.sql`
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/002_normalize_fire_events_status.sql`
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/003_system_parameters_canonical.sql`
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/004_enforce_episode_end_date_trigger.sql`
- `episode_creation_flow/migrations/episode_refactor_v4_corrections/005_enforce_fire_episode_events_1n.sql`
5. Registrar en deuda técnica el hallazgo baseline 307 y su fix.

## FG-EP-20: `fire_events.last_seen_at`
1. Migración Alembic nueva (down_revision: `a1b2c3d4e5f6`):
- `ADD COLUMN IF NOT EXISTS fire_events.last_seen_at timestamptz`.
- `CREATE INDEX IF NOT EXISTS idx_fire_events_last_seen_at ON fire_events (last_seen_at DESC)`.
- Backfill por `MAX(fire_detections.detected_at)` por `fire_event_id`.
2. Backend/pipeline:
- `app/models/fire.py`: agregar `last_seen_at`.
- `app/services/detection_clustering_service.py`: al insertar evento setear `last_seen_at = end_date`.
- `scripts/cluster_fire_events_parallel.py`: idem para inserción legacy.
- `app/services/fire_service.py` y `app/services/export_service.py`: usar `COALESCE(last_seen_at, end_date)` para recencia/actividad cuando aplique.
3. Tests FG-EP-20:
- Unit: resolución de estado/recencia usa `last_seen_at` cuando existe.
- Integration: columna e índice existen y backfill no deja nulo en eventos con detecciones.
4. Registrar hallazgos y evidencia en `technical_debt.md`.

## FG-EP-21: normalización de `fire_events.status`
1. Migración Alembic:
- Data migration: `controlled -> monitoring`, `extinguished -> extinct`.
- Normalizar nulos/valores vacíos a `active` para no dejar fuera de set canónico.
- Reemplazo robusto de `CHECK` dinámico vía `pg_constraint` y creación de `fire_events_status_check` canónico.
- Renombrar columna `extinguished_at` a `extinct_at` (idempotente).
2. Backend/API/scripts:
- `app/models/fire.py`: `extinct_at`.
- `app/schemas/fire.py`: enum canónico `active|monitoring|extinct`; remover `controlled/extinguished`; response con `extinct_at`.
- `app/services/fire_service.py`: remover estados legacy y mapear cualquier legado interno a canónico.
- `app/services/export_service.py`: igual.
- `app/services/closure_report_service.py`: query y lógica con `status='extinct'` + `extinct_at`.
- `app/services/episode_service.py`: normalizar input legacy a canónico al calcular estado.
- `workers/tasks/closure_report_task.py`: textos/logs canónicos.
- Scripts clave: `scripts/aggregate_fire_episodes.py` y `scripts/diagnose_episodes.py` migrados a terminología canónica.
3. Tests FG-EP-21:
- Unit: no se emiten/esperan `controlled` ni `extinguished`.
- Integration DB: no quedan filas fuera de `active|monitoring|extinct`.
- Integration DB: inserción con status legacy falla por constraint.
- Update de tests afectados (`test_closure_report_service`, etc.).
4. Registrar deuda/hallazgos.

## FG-EP-22: parámetros canónicos en `system_parameters`
1. Migración Alembic idempotente:
- Insertar `event_spatial_epsilon_meters=2000`.
- Insertar `event_temporal_window_hours=48`.
- Insertar `event_monitoring_window_hours=168`.
- Insertar `episode_spatial_epsilon_meters=6000`.
- Insertar `episode_temporal_window_hours=96`.
- Formato acorde al modelo real (`param_key`, `param_value` JSONB).
2. Backend/workers/scripts:
- `app/services/detection_clustering_service.py`: leer `event_spatial_epsilon_meters` y `event_temporal_window_hours` con fallback actual.
- `app/services/clustering_service.py`: leer `episode_spatial_epsilon_meters` y `episode_temporal_window_hours` con fallback actual.
- `app/services/fire_service.py` y `app/services/export_service.py`: usar `event_monitoring_window_hours` para ventana de recencia con fallback.
- Scripts clave (`aggregate_fire_episodes.py`) leen parámetros equivalentes con fallback seguro.
3. Tests FG-EP-22:
- Unit: resolución de parámetros desde DB y fallback sin romper.
- Integration: keys existen y son consultables.
4. Registrar deuda/hallazgos.

## FG-EP-23: semántica `fire_episodes.end_date` con trigger
1. Migración Alembic:
- `CREATE OR REPLACE FUNCTION enforce_episode_end_date()`.
- Trigger `BEFORE INSERT OR UPDATE OF status, end_date`.
- Regla: si `status='closed'` y `end_date` nulo, auto set (preferir `last_seen_at` y fallback `now()`); si `status!='closed'`, forzar `end_date=NULL`.
- Limpieza previa de datos inconsistentes para evitar conflictos.
2. Código:
- Ajustar puntos de escritura en `app/services/episode_service.py` para convivir con trigger sin comportamientos contradictorios.
3. Tests FG-EP-23:
- Integration: no se persiste `end_date` con estado no `closed`.
- Integration: al cerrar con `end_date` nulo, trigger lo completa.
4. Registrar deuda/hallazgos.

## FG-EP-24: regla 1:N en `fire_episode_events`
1. Migración Alembic:
- Crear `UNIQUE INDEX IF NOT EXISTS ux_fire_episode_events_event_id ON fire_episode_events(event_id)`.
- Nota de corrección técnica: la columna real es `event_id` (no `fire_event_id`).
2. Backend/tests/documentación:
- `app/services/episode_service.py`: asegurar reasignación atómica para no violar índice.
- Integration test nuevo: falla si un mismo evento intenta quedar en 2 episodios.
- Documentar 1:N explícitamente en:
  - `episode_creation_flow/1_tech_tasks_final.md`
  - `scripts/scripts_readme.md` (reemplazar lenguaje N:M)
  - `docs/tech/clustering_analysis.md` (regla operativa 1:N).
3. Registrar deuda/hallazgos.

## Cambios importantes de API/interfaces/types
- `FireStatus` canónico en `app/schemas/fire.py`: `active|monitoring|extinct`.
- Cambio de contrato: `extinguished_at` deja de existir en schemas/responses; nuevo campo `extinct_at`.
- `/api/v1/fire-episodes` queda sin redirect indeseado (baseline fix).

## Suite de validación por etapa
1. Baseline:
- `pytest tests/integration/test_fire_episodes_modes.py -q`
2. FG-EP-20:
- tests unit/integration de `last_seen_at` + recencia.
3. FG-EP-21:
- tests de estados canónicos + constraints + closure report adaptado.
4. FG-EP-22:
- tests de lectura de `system_parameters` y fallback.
5. FG-EP-23:
- tests de trigger `end_date`.
6. FG-EP-24:
- tests de unicidad 1:N.
7. Final:
- corrida consolidada de todos los tests tocados en una sola ejecución.

## Supuestos y defaults explícitos
- Los archivos canónicos mencionados en `1_tech_tasks_final.md` y no presentes en disco (`0_master_plan.md`, `0_episode_generation_flow.md`, `1_arquitectura_final.md`) se consideran no disponibles; se implementa con las fuentes existentes.
- Alembic es la fuente de verdad ejecutable; el paquete SQL es espejo documental.
- Se incluyen scripts clave además de app/workers para evitar regresión de estados legacy.
- Se admite cambio breaking de API para `extinct_at` según tu decisión.
