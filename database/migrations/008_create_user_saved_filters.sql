-- Migration: 008_create_user_saved_filters.sql

CREATE TABLE IF NOT EXISTS user_saved_filters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filter_name VARCHAR(100) NOT NULL,
    filter_config JSONB NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    use_count INTEGER DEFAULT 0,
    UNIQUE(user_id, filter_name)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_filters_single_default
    ON user_saved_filters(user_id) WHERE is_default = true;

CREATE INDEX IF NOT EXISTS idx_user_filters_user
    ON user_saved_filters(user_id, last_used_at DESC);

ALTER TABLE user_saved_filters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_filters_select ON user_saved_filters;
CREATE POLICY user_filters_select ON user_saved_filters
    FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS user_filters_insert ON user_saved_filters;
CREATE POLICY user_filters_insert ON user_saved_filters
    FOR INSERT WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS user_filters_update ON user_saved_filters;
CREATE POLICY user_filters_update ON user_saved_filters
    FOR UPDATE USING (user_id = auth.uid());

DROP POLICY IF EXISTS user_filters_delete ON user_saved_filters;
CREATE POLICY user_filters_delete ON user_saved_filters
    FOR DELETE USING (user_id = auth.uid());

CREATE OR REPLACE FUNCTION update_filter_usage(p_filter_id UUID)
RETURNS void AS $$
BEGIN
    UPDATE user_saved_filters
    SET last_used_at = NOW(),
        use_count = use_count + 1
    WHERE id = p_filter_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE user_saved_filters IS
    'Saved filters per user for the fire dashboard. filter_config example: '
    '{"province":"Cordoba","status":["active"],"date_from":"2025-01-01",'
    '"date_to":"2025-12-31","min_area_ha":10}';
