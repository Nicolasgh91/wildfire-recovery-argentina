-- Migration: 012_align_fire_pipeline_uc_f08r.sql

BEGIN;

-- 1.1 Add h3_index to fire_detections
ALTER TABLE IF EXISTS public.fire_detections
    ADD COLUMN IF NOT EXISTS h3_index bigint;

CREATE INDEX IF NOT EXISTS idx_fire_detections_h3_detected_at
    ON public.fire_detections (h3_index, detected_at);

CREATE INDEX IF NOT EXISTS idx_fire_detections_detected_at_h3
    ON public.fire_detections (detected_at, h3_index);

-- 1.2 Normalize is_processed (default false, no NULLs)
ALTER TABLE IF EXISTS public.fire_detections
    ALTER COLUMN is_processed SET DEFAULT false;

UPDATE public.fire_detections
   SET is_processed = false
 WHERE is_processed IS NULL;

-- 1.3 Add clustering_version_id to fire_events
ALTER TABLE IF EXISTS public.fire_events
    ADD COLUMN IF NOT EXISTS clustering_version_id uuid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fire_events_clustering_version_id_fkey'
    ) THEN
        ALTER TABLE public.fire_events
            ADD CONSTRAINT fire_events_clustering_version_id_fkey
            FOREIGN KEY (clustering_version_id)
            REFERENCES public.clustering_versions(id);
    END IF;
END
$$ LANGUAGE plpgsql;

CREATE INDEX IF NOT EXISTS idx_fire_events_clustering_version_id
    ON public.fire_events (clustering_version_id);

DO $$
DECLARE
    v_id uuid;
BEGIN
    SELECT id
      INTO v_id
      FROM public.clustering_versions
     WHERE is_active = true
  ORDER BY created_at DESC
     LIMIT 1;

    IF v_id IS NULL THEN
        INSERT INTO public.clustering_versions (
            version_name,
            epsilon_km,
            min_points,
            temporal_window_hours,
            algorithm,
            is_active,
            change_reason
        ) VALUES (
            'legacy-auto',
            1.0,
            2,
            24,
            'ST-DBSCAN',
            true,
            'auto-created for backfill'
        )
        RETURNING id INTO v_id;
    END IF;

    UPDATE public.fire_events
       SET clustering_version_id = v_id
     WHERE clustering_version_id IS NULL;
END
$$ LANGUAGE plpgsql;

-- 1.4 Make fire_episodes.end_date nullable and add last_seen_at
ALTER TABLE IF EXISTS public.fire_episodes
    ALTER COLUMN end_date DROP NOT NULL;

ALTER TABLE IF EXISTS public.fire_episodes
    ADD COLUMN IF NOT EXISTS last_seen_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_fire_episodes_last_seen_at
    ON public.fire_episodes (last_seen_at);

UPDATE public.fire_episodes
   SET last_seen_at = end_date
 WHERE last_seen_at IS NULL
   AND end_date IS NOT NULL;

-- 1.5 System parameters (idempotent inserts)
INSERT INTO public.system_parameters (param_key, param_value, description, category) VALUES
('carousel_batch_size', '{"value": 30}', 'Carousel batch size (episodes)', 'limits'),
('default_timezone', '{"value": "America/Argentina/Buenos_Aires"}', 'Default timezone for display', 'general'),
('gee_max_concurrency', '{"value": 3}', 'Max concurrent GEE requests', 'imagery'),
('max_cloud_coverage', '{"value": 0.35}', 'Max cloud coverage for imagery selection', 'imagery')
ON CONFLICT (param_key) DO NOTHING;

COMMIT;
