-- Add indexes for fire listing performance (UC-13)
-- Date: 2026-01-31

CREATE INDEX IF NOT EXISTS idx_fire_events_end_date
  ON fire_events (end_date);

CREATE INDEX IF NOT EXISTS idx_fire_protected_area_intersections_fire_event_id
  ON fire_protected_area_intersections (fire_event_id);
