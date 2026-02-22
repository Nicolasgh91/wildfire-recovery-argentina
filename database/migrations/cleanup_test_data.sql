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

-- Collect cleanup summary even if some tables don't exist
CREATE TEMP TABLE IF NOT EXISTS cleanup_summary (
    table_name text,
    remaining_test_records bigint
) ON COMMIT DROP;

DO $$
DECLARE
    cnt bigint;
BEGIN
    IF to_regclass('public.audit_logs') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'audit_logs'
             AND column_name = 'is_test'
       ) THEN
        DELETE FROM public.audit_logs WHERE is_test = true;
        EXECUTE 'SELECT COUNT(*) FROM public.audit_logs WHERE is_test = true' INTO cnt;
        INSERT INTO cleanup_summary VALUES ('audit_logs', cnt);
    END IF;

    IF to_regclass('public.satellite_images') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'satellite_images'
             AND column_name = 'is_test'
       ) THEN
        DELETE FROM public.satellite_images WHERE is_test = true;
        EXECUTE 'SELECT COUNT(*) FROM public.satellite_images WHERE is_test = true' INTO cnt;
        INSERT INTO cleanup_summary VALUES ('satellite_images', cnt);
    END IF;

    IF to_regclass('public.fire_events') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'fire_events'
             AND column_name = 'is_test'
       ) THEN
        DELETE FROM public.fire_events WHERE is_test = true;
        EXECUTE 'SELECT COUNT(*) FROM public.fire_events WHERE is_test = true' INTO cnt;
        INSERT INTO cleanup_summary VALUES ('fire_events', cnt);
    END IF;

    IF to_regclass('public.fire_episodes') IS NOT NULL
       AND EXISTS (
           SELECT 1
           FROM information_schema.columns
           WHERE table_schema = 'public'
             AND table_name = 'fire_episodes'
             AND column_name = 'is_test'
       ) THEN
        DELETE FROM public.fire_episodes WHERE is_test = true;
        EXECUTE 'SELECT COUNT(*) FROM public.fire_episodes WHERE is_test = true' INTO cnt;
        INSERT INTO cleanup_summary VALUES ('fire_episodes', cnt);
    END IF;
END $$;

SELECT
    table_name,
    remaining_test_records
FROM cleanup_summary
ORDER BY table_name;

COMMIT;
