-- ============================================================================
-- MIGRATION: Add CU-15/CU-16 satellite carousel fields to fire_events
-- Version: 2026.01.31
-- ============================================================================

ALTER TABLE fire_events
    ADD COLUMN IF NOT EXISTS status VARCHAR(20)
        DEFAULT 'active'
        CHECK (status IN ('active', 'controlled', 'monitoring', 'extinguished')),
    ADD COLUMN IF NOT EXISTS extinguished_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_gee_image_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS last_update_sat TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS slides_data JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS has_historic_report BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_fire_events_status
    ON fire_events (status);

CREATE INDEX IF NOT EXISTS idx_fire_events_status_historic
    ON fire_events (status, has_historic_report)
    WHERE status = 'extinguished';

CREATE INDEX IF NOT EXISTS idx_fire_events_last_update_sat
    ON fire_events (last_update_sat DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_fire_events_extinguished_at
    ON fire_events (extinguished_at DESC NULLS LAST);

-- Backfill status based on end_date for existing records
UPDATE fire_events
SET status = CASE
    WHEN end_date >= NOW() THEN 'active'
    WHEN end_date >= NOW() - INTERVAL '3 days' THEN 'controlled'
    WHEN end_date >= NOW() - INTERVAL '14 days' THEN 'monitoring'
    ELSE 'extinguished'
END
WHERE status IS NULL;

-- Backfill extinguished_at for historical records
UPDATE fire_events
SET extinguished_at = end_date
WHERE status = 'extinguished' AND extinguished_at IS NULL;

COMMENT ON COLUMN fire_events.status IS
'Fire status: active, controlled, monitoring, extinguished.';

COMMENT ON COLUMN fire_events.slides_data IS
'JSON array of slide objects for CU-15/CU-16 carousels.';

COMMENT ON COLUMN fire_events.last_gee_image_id IS
'GEE system:index of last processed Sentinel-2 image.';

COMMENT ON COLUMN fire_events.has_historic_report IS
'True if CU-16 historic report has been generated.';
