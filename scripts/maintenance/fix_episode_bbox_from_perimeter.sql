-- =============================================================================
-- FORESTGUARD — Retroactive Episode BBox Fix
-- =============================================================================
--
-- One-time migration: Recalculates all fire_episodes bounding boxes using
-- the actual perimeter geometries of their associated fire_events, instead
-- of the (incorrect) centroid-based values.
--
-- Root cause: episode_service.update_episode_metrics() was using
-- ST_X(fe.centroid) instead of ST_XMin(fe.perimeter) for bbox calculation.
--
-- Safe to run: only updates rows where perimeter data exists.
-- Idempotent: can be re-run without side effects.
--
-- Usage:
--   psql $DATABASE_URL -f scripts/maintenance/fix_episode_bbox_from_perimeter.sql
--
-- Author: ForestGuard Team
-- Date: 2026-03-05
-- =============================================================================

BEGIN;

UPDATE fire_episodes ep
SET
    bbox_minx = sub.minx,
    bbox_miny = sub.miny,
    bbox_maxx = sub.maxx,
    bbox_maxy = sub.maxy,
    updated_at = NOW()
FROM (
    SELECT
        fee.episode_id,
        MIN(ST_XMin(fe.perimeter::geometry)) AS minx,
        MIN(ST_YMin(fe.perimeter::geometry)) AS miny,
        MAX(ST_XMax(fe.perimeter::geometry)) AS maxx,
        MAX(ST_YMax(fe.perimeter::geometry)) AS maxy
    FROM fire_episode_events fee
    JOIN fire_events fe ON fe.id = fee.event_id
    WHERE fe.perimeter IS NOT NULL
    GROUP BY fee.episode_id
) sub
WHERE ep.id = sub.episode_id;

-- Report how many episodes were updated
DO $$
DECLARE
    affected_count INTEGER;
BEGIN
    GET DIAGNOSTICS affected_count = ROW_COUNT;
    RAISE NOTICE 'Updated % episode bounding boxes from perimeter geometries.', affected_count;
END $$;

COMMIT;
