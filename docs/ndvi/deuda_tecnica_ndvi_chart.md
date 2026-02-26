# Deuda técnica y notas — NDVI / GEE

Documento de referencia para decisiones y deuda técnica relacionada con el chart NDVI y la hoja de ruta GEE (no modifica la hoja de ruta).

---

## Fase 1 — Endpoint solo BD (GEE)

- **GET /monitoring/recovery/{id}** ya no llama GEE en ningún caso: lee de `fire_events` y `vegetation_monitoring`; si no hay filas, llama `_enqueue_recovery_if_not_pending(id)` y devuelve `pending` con mensaje.
- **Cola "gee":** el encolado desde el GET usa `queue="gee"` y `countdown=5`. La cola `"gee"` debe ser consumida por workers; en Fase 2 se configuran `task_routes` y `beat_schedule` en `celery_app.py` (raíz) para enrutar `analyze_recovery` y batches a `"gee"`. Hasta entonces, si no hay worker consumiendo `"gee"`, las tareas encoladas desde el GET quedarán en esa cola hasta que Fase 2 esté desplegada.
- **Trigger admin:** `POST /monitoring/recovery/trigger` usa `queue="gee"` (Fase 2 completada).

---

## Fase 2 — Worker GEE incremental

- **analyze_recovery:** Máximo 2 requests GEE por ejecución (baseline si no existe + mes actual). Lee baseline desde `vegetation_monitoring` si ya existe; si no, llama `_get_baseline_ndvi` (propaga `BaselineNotAvailableError` → worker retorna `{"status": "pending", "reason": "no_baseline_image"}` sin reintentar). Usa `_get_current_ndvi_with_cloud` para el mes actual. UPSERT con `ON CONFLICT (fire_event_id, monitoring_date)`.
- **Cola `gee`:** Todas las tareas recovery, destruction y generate_carousel enrutadas a `"gee"`. Beat: `recovery-monthly` (día 2 de cada mes, 02:00 UTC), `recovery-weekly-recent` (lunes 03:00 UTC).
- **cloud_cover_pct y recovery_status:** Añadidas en migración `2026_02_26_vegetation_monitoring_cloud_recovery_status.sql`. El worker persiste ambos y el GET `/monitoring/recovery/{id}` los devuelve en `monitoring_data`. Ejecutar esa migración en la BD antes de desplegar el worker actualizado.

---

## Fase 3 — Índices y recovery_snapshot en fire_events

- **G3-1:** Migración `2026_02_26_fase3_vm_indexes_fire_events_recovery_snapshot.sql`: índice `idx_vm_event_date (fire_event_id, monitoring_date DESC)`, índice parcial `idx_vm_event_latest` (últimos 3 meses), constraint `uq_vm_event_date` si no existe.
- **G3-2:** Misma migración: columnas en `fire_events` (`recovery_status`, `recovery_percentage`, `last_monitoring_date`), función `sync_fire_event_recovery_snapshot()` y trigger `trg_sync_recovery_snapshot` en `vegetation_monitoring`. El snapshot se actualiza solo cuando el nuevo `monitoring_date` es más reciente. Backfill opcional al final para datos ya existentes.
- **Orden de aplicación:** ejecutar antes `2026_02_26_vegetation_monitoring_cloud_recovery_status.sql` (vegetation_monitoring debe tener `recovery_status` para el trigger y el backfill).
