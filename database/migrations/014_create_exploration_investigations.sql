-- Migration: 014_create_exploration_investigations.sql

BEGIN;

CREATE TABLE IF NOT EXISTS user_investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    fire_event_id UUID REFERENCES fire_events(id),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE user_investigations
    DROP CONSTRAINT IF EXISTS user_investigations_status_check;
ALTER TABLE user_investigations
    ADD CONSTRAINT user_investigations_status_check
    CHECK (status IN ('draft', 'quoted', 'processing', 'ready', 'failed'));

CREATE INDEX IF NOT EXISTS idx_user_investigations_user
    ON user_investigations(user_id);

CREATE INDEX IF NOT EXISTS idx_user_investigations_fire_event
    ON user_investigations(fire_event_id);

CREATE TABLE IF NOT EXISTS investigation_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES user_investigations(id) ON DELETE CASCADE,
    kind VARCHAR(10) NOT NULL,
    target_date TIMESTAMPTZ NOT NULL,
    sensor VARCHAR(50),
    aoi JSONB,
    geometry_ref TEXT,
    visualization_params JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE investigation_items
    DROP CONSTRAINT IF EXISTS investigation_items_kind_check;
ALTER TABLE investigation_items
    ADD CONSTRAINT investigation_items_kind_check
    CHECK (kind IN ('pre', 'post'));

ALTER TABLE investigation_items
    DROP CONSTRAINT IF EXISTS investigation_items_status_check;
ALTER TABLE investigation_items
    ADD CONSTRAINT investigation_items_status_check
    CHECK (status IN ('pending', 'queued', 'generated', 'failed'));

CREATE INDEX IF NOT EXISTS idx_investigation_items_investigation
    ON investigation_items(investigation_id);

CREATE OR REPLACE FUNCTION enforce_max_investigation_items()
RETURNS TRIGGER AS $$
DECLARE
    item_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO item_count
    FROM investigation_items
    WHERE investigation_id = NEW.investigation_id;

    IF TG_OP = 'INSERT' THEN
        IF item_count >= 12 THEN
            RAISE EXCEPTION 'Max 12 items per investigation';
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.investigation_id IS DISTINCT FROM OLD.investigation_id THEN
            SELECT COUNT(*) INTO item_count
            FROM investigation_items
            WHERE investigation_id = NEW.investigation_id;
            IF item_count >= 12 THEN
                RAISE EXCEPTION 'Max 12 items per investigation';
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enforce_max_investigation_items ON investigation_items;
CREATE TRIGGER trg_enforce_max_investigation_items
    BEFORE INSERT OR UPDATE OF investigation_id ON investigation_items
    FOR EACH ROW EXECUTE FUNCTION enforce_max_investigation_items();

CREATE TABLE IF NOT EXISTS investigation_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_item_id UUID NOT NULL REFERENCES investigation_items(id) ON DELETE CASCADE,
    gcs_path TEXT NOT NULL,
    signed_url_cache JSONB,
    mime TEXT,
    width INTEGER,
    height INTEGER,
    sha256 TEXT,
    generated_at TIMESTAMPTZ,
    recipe JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_investigation_assets_item
    ON investigation_assets(investigation_item_id);

CREATE TABLE IF NOT EXISTS investigation_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES user_investigations(id) ON DELETE CASCADE,
    share_token UUID NOT NULL DEFAULT gen_random_uuid(),
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_investigation_shares_investigation
    ON investigation_shares(investigation_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_investigation_shares_token
    ON investigation_shares(share_token);

CREATE TABLE IF NOT EXISTS hd_generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    investigation_id UUID NOT NULL REFERENCES user_investigations(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    progress_total INTEGER NOT NULL DEFAULT 0,
    progress_done INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE hd_generation_jobs
    DROP CONSTRAINT IF EXISTS hd_generation_jobs_status_check;
ALTER TABLE hd_generation_jobs
    ADD CONSTRAINT hd_generation_jobs_status_check
    CHECK (status IN ('queued', 'processing', 'ready', 'failed'));

CREATE INDEX IF NOT EXISTS idx_hd_generation_jobs_investigation
    ON hd_generation_jobs(investigation_id);

COMMIT;
