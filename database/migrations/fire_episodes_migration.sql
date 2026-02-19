-- ============================================================================
-- UC-17: Fire Episodes Schema Migration
-- Purpose: Add tables to aggregate fire_events into macro fire_episodes
-- for optimizing GEE requests
-- ============================================================================

-- Table: fire_episodes (Macro aggregation of fire_events)
CREATE TABLE IF NOT EXISTS public.fire_episodes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    status character varying DEFAULT 'active' CHECK (status IN ('active', 'monitoring', 'extinct', 'closed')),
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone NOT NULL,
    
    -- Centroid (calculated from all events)
    centroid_lat double precision NOT NULL,
    centroid_lon double precision NOT NULL,
    
    -- Bounding Box (union of all event bboxes + padding)
    bbox_minx double precision,
    bbox_miny double precision,
    bbox_maxx double precision,
    bbox_maxy double precision,
    
    -- Administrative (soft mode aggregation)
    provinces text[],  -- Array of provinces covered
    
    -- Aggregated metrics
    event_count integer NOT NULL DEFAULT 0,
    detection_count integer NOT NULL DEFAULT 0,
    frp_sum numeric DEFAULT 0,
    frp_max numeric DEFAULT 0,
    estimated_area_hectares numeric DEFAULT 0,
    
    -- GEE processing flags
    gee_candidate boolean DEFAULT false,
    gee_priority integer,
    last_gee_image_id character varying,
    last_update_sat timestamp with time zone,
    slides_data jsonb,
    
    -- Audit fields
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    
    CONSTRAINT fire_episodes_pkey PRIMARY KEY (id)
);

-- Ensure status constraint is updated when re-running this migration
ALTER TABLE public.fire_episodes
    DROP CONSTRAINT IF EXISTS fire_episodes_status_check;
ALTER TABLE public.fire_episodes
    ADD CONSTRAINT fire_episodes_status_check
    CHECK (status IN ('active', 'monitoring', 'extinct', 'closed'));

-- Table: fire_episode_events (N:M relationship between episodes and events)
CREATE TABLE IF NOT EXISTS public.fire_episode_events (
    episode_id uuid NOT NULL,
    event_id uuid NOT NULL,
    added_at timestamp with time zone DEFAULT now(),
    
    CONSTRAINT fire_episode_events_pkey PRIMARY KEY (episode_id, event_id),
    CONSTRAINT fire_episode_events_episode_fkey
        FOREIGN KEY (episode_id) REFERENCES public.fire_episodes(id) ON DELETE CASCADE,
    CONSTRAINT fire_episode_events_event_fkey
        FOREIGN KEY (event_id) REFERENCES public.fire_events(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fire_episodes_status ON fire_episodes (status);
CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_candidate ON fire_episodes (gee_candidate) WHERE gee_candidate = true;
CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_priority ON fire_episodes (gee_priority) WHERE gee_candidate = true;
CREATE INDEX IF NOT EXISTS idx_fire_episodes_dates ON fire_episodes (start_date DESC, end_date DESC);
CREATE INDEX IF NOT EXISTS idx_fire_episode_events_episode ON fire_episode_events (episode_id);
CREATE INDEX IF NOT EXISTS idx_fire_episode_events_event ON fire_episode_events (event_id);

-- Enable RLS
ALTER TABLE fire_episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE fire_episode_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies (Public Read, Admin Write)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'fire_episodes' AND policyname = 'Public Read Access'
    ) THEN
        DROP POLICY "Public Read Access" ON public.fire_episodes;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'fire_episodes' AND policyname = 'Admin Write Access'
    ) THEN
        DROP POLICY "Admin Write Access" ON public.fire_episodes;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'fire_episode_events' AND policyname = 'Public Read Access'
    ) THEN
        DROP POLICY "Public Read Access" ON public.fire_episode_events;
    END IF;
    IF EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname = 'public' AND tablename = 'fire_episode_events' AND policyname = 'Admin Write Access'
    ) THEN
        DROP POLICY "Admin Write Access" ON public.fire_episode_events;
    END IF;
END $$;

CREATE POLICY "Public Read Access" ON fire_episodes
    FOR SELECT TO anon, authenticated, service_role USING (true);

CREATE POLICY "Admin Write Access" ON fire_episodes
    FOR ALL TO service_role USING (true);

CREATE POLICY "Public Read Access" ON fire_episode_events
    FOR SELECT TO anon, authenticated, service_role USING (true);

CREATE POLICY "Admin Write Access" ON fire_episode_events
    FOR ALL TO service_role USING (true);

-- Comments for documentation
COMMENT ON TABLE fire_episodes IS 'UC-17: Macro aggregation of fire_events for GEE optimization';
COMMENT ON COLUMN fire_episodes.gee_candidate IS 'Whether this episode should be processed by GEE';
COMMENT ON COLUMN fire_episodes.gee_priority IS 'Priority ranking for GEE processing (lower = higher priority)';
COMMENT ON TABLE fire_episode_events IS 'N:M relationship linking episodes to their constituent fire_events';
