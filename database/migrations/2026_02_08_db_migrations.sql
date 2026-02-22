-- =============================================================================
-- FORESTGUARD PRODUCTION DATABASE MIGRATIONS (FIXED)
-- =============================================================================
-- Run this script in Supabase SQL Editor
-- Date: 2026-02-08
-- Tasks: PERF-001 (Geospatial Indices) - FEAT-001 already completed
-- =============================================================================
-- NOTA: H3 extension no disponible en Supabase, omitido
-- NOTA: user_saved_filters ya existe en el schema

-- =============================================================================
-- PERF-001: Geospatial & Performance Indices
-- =============================================================================

-- Spatial index on fire event centroid (GIST) - USA 'centroid' que es USER-DEFINED
CREATE INDEX IF NOT EXISTS idx_fire_events_centroid_gist 
ON fire_events USING GIST (centroid);

-- Spatial index on fire event perimeter (GIST)
CREATE INDEX IF NOT EXISTS idx_fire_events_perimeter_gist 
ON fire_events USING GIST (perimeter);

-- Composite index for common fire list query (province + date range)
CREATE INDEX IF NOT EXISTS idx_fire_events_province_dates 
ON fire_events (province, start_date DESC, end_date DESC);

-- Index for statistics queries (is_significant filtering)
CREATE INDEX IF NOT EXISTS idx_fire_events_significant_dates 
ON fire_events (is_significant, start_date DESC) 
WHERE is_significant = true;

-- Index for status filtering (active fires)
CREATE INDEX IF NOT EXISTS idx_fire_events_status 
ON fire_events (status) 
WHERE status = 'active';

-- Detection location index for clustering
CREATE INDEX IF NOT EXISTS idx_fire_detections_location_gist 
ON fire_detections USING GIST (location);

-- Detection date index for time-series queries
CREATE INDEX IF NOT EXISTS idx_fire_detections_detected_at 
ON fire_detections (detected_at DESC);

-- Protected area spatial index - USA 'boundary' (no 'geometry')
CREATE INDEX IF NOT EXISTS idx_protected_areas_boundary_gist 
ON protected_areas USING GIST (boundary);

-- Fire episode indices for fast lookup
CREATE INDEX IF NOT EXISTS idx_fire_episodes_status 
ON fire_episodes (status) 
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_fire_episodes_dates 
ON fire_episodes (start_date DESC, end_date DESC);

-- Fire detections by event
CREATE INDEX IF NOT EXISTS idx_fire_detections_event_id 
ON fire_detections (fire_event_id);

-- Climate data location index
CREATE INDEX IF NOT EXISTS idx_climate_data_location_gist 
ON climate_data USING GIST (location);

-- user_saved_filters index (tabla ya existe)
CREATE INDEX IF NOT EXISTS idx_user_saved_filters_user_id 
ON user_saved_filters (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_saved_filters_unique_default 
ON user_saved_filters (user_id) 
WHERE is_default = true;

-- =============================================================================
-- VERIFICATION QUERIES
-- =============================================================================

-- Check new indices exist
SELECT indexname, tablename 
FROM pg_indexes 
WHERE tablename IN ('fire_events', 'fire_detections', 'user_saved_filters', 'protected_areas', 'fire_episodes', 'climate_data')
AND schemaname = 'public'
ORDER BY tablename, indexname;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================
SELECT '✅ PERF-001: All geospatial indices created successfully!' AS status;
