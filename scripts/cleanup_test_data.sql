-- =============================================================================
-- CLEANUP TEST DATA
-- =============================================================================
-- This script removes all test records from the database.
-- Test records are identified by the is_test flag set to true.
--
-- Tables cleaned:
--   - audit_logs
--   - fire_events
--   - fire_episodes
--   - satellite_images
--
-- Usage:
--   psql -h <host> -U <user> -d <database> -f scripts/cleanup_test_data.sql
--
-- Author: ForestGuard Team
-- Last Updated: 2026-02-11
-- =============================================================================

BEGIN;

-- Delete test records from audit_logs
DELETE FROM audit_logs
WHERE is_test = true;

-- Delete test records from satellite_images
DELETE FROM satellite_images
WHERE is_test = true;

-- Delete test records from fire_events
DELETE FROM fire_events
WHERE is_test = true;

-- Delete test records from fire_episodes
DELETE FROM fire_episodes
WHERE is_test = true;

-- Show cleanup summary
SELECT
    'audit_logs' as table_name,
    COUNT(*) as remaining_test_records
FROM audit_logs
WHERE is_test = true
UNION ALL
SELECT
    'satellite_images' as table_name,
    COUNT(*) as remaining_test_records
FROM satellite_images
WHERE is_test = true
UNION ALL
SELECT
    'fire_events' as table_name,
    COUNT(*) as remaining_test_records
FROM fire_events
WHERE is_test = true
UNION ALL
SELECT
    'fire_episodes' as table_name,
    COUNT(*) as remaining_test_records
FROM fire_episodes
WHERE is_test = true;

COMMIT;
