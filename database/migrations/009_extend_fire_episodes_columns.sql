-- Migration: 009_extend_fire_episodes_columns.sql

ALTER TABLE IF EXISTS fire_episodes
    ADD COLUMN IF NOT EXISTS gee_candidate BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS gee_priority INTEGER,
    ADD COLUMN IF NOT EXISTS last_gee_image_id VARCHAR,
    ADD COLUMN IF NOT EXISTS last_update_sat TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS slides_data JSONB,
    ADD COLUMN IF NOT EXISTS clustering_version_id UUID,
    ADD COLUMN IF NOT EXISTS requires_recalculation BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS dnbr_severity NUMERIC,
    ADD COLUMN IF NOT EXISTS severity_class VARCHAR(20),
    ADD COLUMN IF NOT EXISTS dnbr_calculated_at TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fire_episodes_clustering_version_id_fkey'
    ) THEN
        ALTER TABLE fire_episodes
            ADD CONSTRAINT fire_episodes_clustering_version_id_fkey
            FOREIGN KEY (clustering_version_id)
            REFERENCES clustering_versions(id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_candidate
    ON fire_episodes(gee_candidate)
    WHERE gee_candidate = true;

CREATE INDEX IF NOT EXISTS idx_fire_episodes_gee_priority
    ON fire_episodes(gee_priority)
    WHERE gee_candidate = true;

CREATE INDEX IF NOT EXISTS idx_fire_episodes_last_update_sat
    ON fire_episodes(last_update_sat DESC);

CREATE INDEX IF NOT EXISTS idx_episodes_needs_recalc
    ON fire_episodes(requires_recalculation)
    WHERE requires_recalculation = true;

CREATE INDEX IF NOT EXISTS idx_episodes_severity
    ON fire_episodes(dnbr_severity DESC)
    WHERE dnbr_severity IS NOT NULL;

CREATE OR REPLACE FUNCTION mark_episode_for_recalculation()
RETURNS TRIGGER AS $$
BEGIN
    IF (
        OLD.centroid IS DISTINCT FROM NEW.centroid OR
        (OLD.status != 'false_positive' AND NEW.status = 'false_positive')
    ) THEN
        UPDATE fire_episodes
           SET requires_recalculation = true
         WHERE id IN (
            SELECT episode_id
              FROM fire_episode_events
             WHERE event_id = NEW.id
         );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_invalidate_episode_on_event_change ON fire_events;
CREATE TRIGGER trg_invalidate_episode_on_event_change
AFTER UPDATE ON fire_events
FOR EACH ROW EXECUTE FUNCTION mark_episode_for_recalculation();
