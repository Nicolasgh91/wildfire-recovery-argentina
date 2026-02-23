-- =============================================================================
-- UC-F12: VAE Monitoring — Schema Hardening & RLS
-- =============================================================================
-- Run this script in Supabase SQL Editor
-- Date: 2026-02-23
-- Tasks:
--   1. UNIQUE constraints for worker idempotency (CT-UCF12-07)
--   2. NOT NULL on is_potential_violation
--   3. FK constraint on monitoring_record_id
--   4. Performance indexes
--   5. RLS policies for vegetation_monitoring and land_use_changes
-- =============================================================================

-- =============================================================================
-- 1. UNIQUE CONSTRAINTS (idempotency for workers)
-- =============================================================================

-- Allows workers to use INSERT ... ON CONFLICT (fire_event_id, monitoring_date)
ALTER TABLE vegetation_monitoring
  ADD CONSTRAINT uq_vm_event_date
  UNIQUE (fire_event_id, monitoring_date);

-- Allows workers to use INSERT ... ON CONFLICT (fire_event_id, change_detected_at)
ALTER TABLE land_use_changes
  ADD CONSTRAINT uq_luc_event_date
  UNIQUE (fire_event_id, change_detected_at);

-- =============================================================================
-- 2. NOT NULL on is_potential_violation
-- =============================================================================

-- Backfill any existing NULL values first
UPDATE land_use_changes
SET is_potential_violation = false
WHERE is_potential_violation IS NULL;

ALTER TABLE land_use_changes
  ALTER COLUMN is_potential_violation SET NOT NULL;

-- =============================================================================
-- 3. FK constraint on monitoring_record_id
-- =============================================================================

ALTER TABLE land_use_changes
  ADD CONSTRAINT land_use_changes_monitoring_record_id_fkey
  FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id);

-- =============================================================================
-- 4. Performance indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_vm_event_date
  ON vegetation_monitoring (fire_event_id, monitoring_date);

CREATE INDEX IF NOT EXISTS idx_luc_event_date
  ON land_use_changes (fire_event_id, change_detected_at);

CREATE INDEX IF NOT EXISTS idx_vm_event_months
  ON vegetation_monitoring (fire_event_id, months_after_fire DESC);

-- =============================================================================
-- 5. RLS POLICIES
-- =============================================================================

-- Enable RLS on both tables
ALTER TABLE vegetation_monitoring ENABLE ROW LEVEL SECURITY;
ALTER TABLE land_use_changes ENABLE ROW LEVEL SECURITY;

-- vegetation_monitoring: authenticated users can read
CREATE POLICY auth_read_vegetation ON vegetation_monitoring
  FOR SELECT TO authenticated USING (true);

-- vegetation_monitoring: only service_role can write (workers use service key)
CREATE POLICY system_write_vegetation ON vegetation_monitoring
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- land_use_changes: authenticated users can read
CREATE POLICY auth_read_land_use ON land_use_changes
  FOR SELECT TO authenticated USING (true);

-- land_use_changes: only service_role can write (workers use service key)
CREATE POLICY system_write_land_use ON land_use_changes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
