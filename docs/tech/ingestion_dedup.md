# Ingestion dedup (UC-F08R)
Fecha: 2026-02-05

## Entrypoints relevantes
- `scripts/load_firms_incremental.py`: ingesta diaria NRT (cron). Es el flujo productivo real.
- `workers/tasks/ingestion.py`: task Celery conectado al pipeline real (`run_incremental_pipeline`).
- `scripts/load_firms_history.py`: ingesta histórica (batch), sin deduplicación.

## Criterio canónico de deduplicación (recomendado)
`detection_hash` (sha256 estable) construido con:
- `satellite`
- `instrument`
- `detected_at` en UTC (ISO-8601)
- `latitude` (5 decimales)
- `longitude` (5 decimales)
- `fire_radiative_power` (2 decimales)
- `confidence_normalized`

Recomendación de esquema:
- Columna `fire_detections.detection_hash text`
- `UNIQUE (detection_hash)`
- Inserción con `ON CONFLICT DO NOTHING`

## Implementación actual (2026-02-05)
`load_firms_incremental.py`:
- Genera `detected_at` a partir de `acq_date + acq_time` (UTC) y lo usa como fuente de verdad temporal.
- Calcula `detection_hash` con el criterio canónico.
- Dedup primario:
  - Si existe la columna `detection_hash`, busca hashes existentes por `acquisition_date` y filtra en memoria.
  - Si no existe, cae a hash legacy (MD5) basado en `lat|lon|acq_date|acq_time|satellite`.
- Inserta siempre `is_processed = false` y `fire_event_id = NULL`.
- Calcula `h3_index` si la columna existe y la librería `h3` está instalada.

`load_firms_history.py`:
- No deduplica (asume carga única por año).
- Usa `detected_at` y marca `is_processed = false`, `fire_event_id = NULL`.

## Concurrencia / riesgos
- Sin `UNIQUE (detection_hash)`, la deduplicación es **best-effort** (dos jobs simultáneos pueden duplicar).
- La solución robusta es aplicar la migración con `detection_hash` único y usar `ON CONFLICT DO NOTHING`.

## Pendientes recomendados
- Backfill de `detection_hash` para históricos si se activa la constraint única.
- Revisar parámetros de Celery Beat (days, dry_run) si se quiere ajustar la ventana de ingesta.

