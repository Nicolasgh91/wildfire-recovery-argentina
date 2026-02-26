-- =============================================================================
-- vegetation_monitoring: cloud_cover_pct y recovery_status
-- =============================================================================
-- Fecha: 2026-02-26
-- Motivo: Fase 2 GEE (hoja_de_ruta_ndvi_gee_v2.md). El worker analyze_recovery
--         obtiene nubosidad y clasificación de recuperación; se persisten aquí
--         para que GET /monitoring/recovery/{id} pueda devolverlos sin recalcular.
--
-- Cómo aplicar:
--   1. Ejecutar este script en Supabase SQL Editor (o psql) sobre la BD.
--   2. Desplegar/reiniciar workers para que el UPSERT use las nuevas columnas.
--
-- Referencia: docs/ndvi/deuda_tecnica_ndvi_chart.md (Fase 2).
-- =============================================================================

-- Porcentaje de nubes de la imagen usada para el NDVI (0–100).
ALTER TABLE vegetation_monitoring
  ADD COLUMN IF NOT EXISTS cloud_cover_pct real;

COMMENT ON COLUMN vegetation_monitoring.cloud_cover_pct IS
  'Porcentaje de nubosidad (CLOUDY_PIXEL_PERCENTAGE) de la imagen GEE usada para ndvi_mean.';

-- Estado de recuperación clasificado (full_recovery, moderate_recovery, etc.).
ALTER TABLE vegetation_monitoring
  ADD COLUMN IF NOT EXISTS recovery_status character varying(50);

COMMENT ON COLUMN vegetation_monitoring.recovery_status IS
  'Clasificación: full_recovery, advanced_recovery, moderate_recovery, early_recovery, stalled, not_started.';
