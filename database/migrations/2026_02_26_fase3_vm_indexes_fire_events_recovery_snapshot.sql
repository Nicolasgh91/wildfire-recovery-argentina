-- =============================================================================
-- Fase 3: Índices en vegetation_monitoring + recovery_snapshot en fire_events
-- =============================================================================
-- Fuente: docs/ndvi/hoja_de_ruta_ndvi_gee_v2.md (G3-1, G3-2)
--         docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md §4.1, §4.2
--
-- G3-1: Índices y UNIQUE para queries rápidas e idempotencia del UPSERT.
-- G3-2: Columnas de snapshot en fire_events + trigger para GET /fires/:id
--       sin query a vegetation_monitoring (requisito de Fase 5).
--
-- Cómo aplicar:
--   1. Aplicar antes 2026_02_26_vegetation_monitoring_cloud_recovery_status.sql
--      (vegetation_monitoring debe tener recovery_status para el trigger y backfill).
--   2. Ejecutar este script en Supabase SQL Editor (o psql).
-- Si ya aplicaste 2026_02_23_uc_f12_vae_monitoring.sql, el UNIQUE y idx_vm_event_date
-- pueden existir; el script usa IF NOT EXISTS / DROP IF EXISTS donde aplica.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- G3-1: vegetation_monitoring — índice y UNIQUE
-- -----------------------------------------------------------------------------

-- Índice para ORDER BY monitoring_date DESC (GET /recovery/{id})
-- Reemplaza el índice anterior si existía sin DESC (p. ej. de 2026_02_23).
DROP INDEX IF EXISTS idx_vm_event_date;
CREATE INDEX idx_vm_event_date
  ON vegetation_monitoring (fire_event_id, monitoring_date DESC);

-- Índice parcial "últimos 3 meses" omitido: en PostgreSQL el predicado debe ser IMMUTABLE,
-- y current_date no lo es. El índice idx_vm_event_date basta para queries por evento.

-- UNIQUE para idempotencia del UPSERT del worker (ON CONFLICT (fire_event_id, monitoring_date))
-- Si ya existe por 2026_02_23, omitir este bloque.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'vegetation_monitoring'::regclass
      AND conname = 'uq_vm_event_date'
  ) THEN
    ALTER TABLE vegetation_monitoring
      ADD CONSTRAINT uq_vm_event_date
      UNIQUE (fire_event_id, monitoring_date);
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- G3-2: fire_events — columnas recovery_snapshot + trigger
-- -----------------------------------------------------------------------------

ALTER TABLE fire_events
  ADD COLUMN IF NOT EXISTS recovery_status VARCHAR(50) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS recovery_percentage NUMERIC(5,2) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS last_monitoring_date DATE DEFAULT NULL;

COMMENT ON COLUMN fire_events.recovery_status IS
  'Snapshot del último recovery_status en vegetation_monitoring (actualizado por trigger).';
COMMENT ON COLUMN fire_events.recovery_percentage IS
  'Snapshot del último recovery_percentage en vegetation_monitoring (actualizado por trigger).';
COMMENT ON COLUMN fire_events.last_monitoring_date IS
  'Fecha del último registro en vegetation_monitoring (actualizado por trigger).';

-- Función que sincroniza el snapshot en fire_events al insertar/actualizar vegetation_monitoring.
-- Solo actualiza si el nuevo monitoring_date es más reciente (o no hay fecha aún).
CREATE OR REPLACE FUNCTION sync_fire_event_recovery_snapshot()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE fire_events
  SET
    recovery_status = NEW.recovery_status,
    recovery_percentage = NEW.recovery_percentage,
    last_monitoring_date = NEW.monitoring_date::date
  WHERE id = NEW.fire_event_id
    AND (last_monitoring_date IS NULL OR last_monitoring_date < NEW.monitoring_date::date);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: después de INSERT o UPDATE en vegetation_monitoring
DROP TRIGGER IF EXISTS trg_sync_recovery_snapshot ON vegetation_monitoring;
CREATE TRIGGER trg_sync_recovery_snapshot
  AFTER INSERT OR UPDATE OF recovery_status, recovery_percentage, monitoring_date
  ON vegetation_monitoring
  FOR EACH ROW
  EXECUTE FUNCTION sync_fire_event_recovery_snapshot();

-- Opcional: backfill de fire_events que ya tengan filas en vegetation_monitoring
-- (el trigger solo se dispara en nuevos INSERT/UPDATE; datos históricos se pueden re-sincronizar)
UPDATE fire_events fe
SET
  recovery_status = vm.recovery_status,
  recovery_percentage = vm.recovery_percentage,
  last_monitoring_date = vm.monitoring_date::date
FROM (
  SELECT DISTINCT ON (fire_event_id)
    fire_event_id,
    recovery_status,
    recovery_percentage,
    monitoring_date
  FROM vegetation_monitoring
  ORDER BY fire_event_id, monitoring_date DESC
) vm
WHERE fe.id = vm.fire_event_id
  AND (fe.recovery_status IS DISTINCT FROM vm.recovery_status
       OR fe.recovery_percentage IS DISTINCT FROM vm.recovery_percentage
       OR fe.last_monitoring_date IS DISTINCT FROM vm.monitoring_date::date);
