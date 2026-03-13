-- =============================================================================
-- VAE Schema Hardening — Delta sobre 2026_02_23 (F1-04 + F1-05)
-- =============================================================================
-- Fecha: 2026-03-12
-- Referencia: vae_module_specification.md, vae_p0_technical_tasks.md F1
--
-- NOTA: La migración 2026_02_23_uc_f12_vae_monitoring.sql ya aplicó:
--   F1-01 UNIQUE, F1-02 índices, F1-03 FK + NOT NULL, y RLS (auth + service_role).
-- Este script agrega solo:
--   F1-04 Columnas nuevas (confidence_score, pending_reason, latest_recovery_*)
--   F1-05 Política anon_read_vegetation (lectura pública para badge/NDVI)
-- =============================================================================

-- =============================================================================
-- F1-04: Nuevas columnas (idempotente con IF NOT EXISTS)
-- =============================================================================

ALTER TABLE land_use_changes
  ADD COLUMN IF NOT EXISTS confidence_score real;

ALTER TABLE vegetation_monitoring
  ADD COLUMN IF NOT EXISTS pending_reason varchar(50);

ALTER TABLE fire_events
  ADD COLUMN IF NOT EXISTS latest_recovery_status varchar,
  ADD COLUMN IF NOT EXISTS latest_recovery_pct real;

-- =============================================================================
-- F1-05: Política de lectura anónima en vegetation_monitoring
-- =============================================================================
-- Permite que usuarios no autenticados vean badge y gráfico NDVI (decisión D-08).

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'vegetation_monitoring'
      AND policyname = 'anon_read_vegetation'
  ) THEN
    CREATE POLICY anon_read_vegetation ON vegetation_monitoring
      FOR SELECT TO anon USING (true);
  END IF;
END
$$;

-- =============================================================================
-- VERIFICACIÓN POST-MIGRACIÓN (ejecutar y revisar resultados)
-- =============================================================================
-- Constraints UNIQUE (deben existir si 2026_02_23 está aplicada):
--   SELECT conname FROM pg_constraint
--   WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u';
--   SELECT conname FROM pg_constraint
--   WHERE conrelid = 'land_use_changes'::regclass AND contype = 'u';
--
-- Índices (vegetation_monitoring: idx_vm_event_date, idx_vm_event_months;
--          land_use_changes: idx_luc_event_date en 2026_02_23):
--   SELECT indexname FROM pg_indexes
--   WHERE tablename = 'vegetation_monitoring' AND indexname LIKE 'idx_vm_%';
--   SELECT indexname FROM pg_indexes
--   WHERE tablename = 'land_use_changes' AND indexname LIKE 'idx_luc%';
--
-- Columnas nuevas (F1-04):
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'land_use_changes' AND column_name = 'confidence_score';
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'vegetation_monitoring' AND column_name = 'pending_reason';
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name = 'fire_events' AND column_name IN ('latest_recovery_status','latest_recovery_pct');
--
-- Políticas RLS (esperado: 3 en vegetation_monitoring, 2 en land_use_changes):
--   SELECT tablename, policyname, roles FROM pg_policies
--   WHERE tablename IN ('vegetation_monitoring', 'land_use_changes')
--   ORDER BY tablename, policyname;
-- =============================================================================
