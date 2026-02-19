-- ============================================================================
-- MIGRATION: Add fire_episodes (UC-17) aggregation layer for GEE optimization
-- Version: 2026.02.01
-- ============================================================================

CREATE TABLE IF NOT EXISTS fire_episodes (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    status character varying DEFAULT 'active'::character varying
        CHECK (status IN ('active', 'monitoring', 'extinct', 'closed')),
    start_date timestamp with time zone NOT NULL,
    end_date timestamp with time zone NOT NULL,
    centroid_lat double precision NOT NULL,
    centroid_lon double precision NOT NULL,
    bbox_minx double precision,
    bbox_miny double precision,
    bbox_maxx double precision,
    bbox_maxy double precision,
    provinces text[],
    event_count integer DEFAULT 0,
    detection_count integer DEFAULT 0,
    frp_sum numeric,
    frp_max numeric,
    estimated_area_hectares numeric,
    gee_candidate boolean DEFAULT false,
    gee_priority integer,
    last_gee_image_id character varying,
    last_update_sat timestamp with time zone,
    slides_data jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT fire_episodes_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS fire_episode_events (
    episode_id uuid NOT NULL,
    event_id uuid NOT NULL,
    added_at timestamp with time zone DEFAULT now(),
    CONSTRAINT fire_episode_events_pkey PRIMARY KEY (episode_id, event_id),
    CONSTRAINT fire_episode_events_episode_id_fkey FOREIGN KEY (episode_id)
        REFERENCES fire_episodes (id) ON DELETE CASCADE,
    CONSTRAINT fire_episode_events_event_id_fkey FOREIGN KEY (event_id)
        REFERENCES fire_events (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fire_episodes_status ON fire_episodes (status);
CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_candidate
    ON fire_episodes (gee_candidate) WHERE gee_candidate = true;
CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_priority
    ON fire_episodes (gee_priority) WHERE gee_candidate = true;
CREATE INDEX IF NOT EXISTS idx_fire_episodes_dates
    ON fire_episodes (start_date DESC, end_date DESC);
CREATE INDEX IF NOT EXISTS idx_fire_episode_events_event_id ON fire_episode_events (event_id);
CREATE INDEX IF NOT EXISTS idx_fire_episode_events_episode_id ON fire_episode_events (episode_id);
