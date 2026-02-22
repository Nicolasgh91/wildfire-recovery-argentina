-- Migration: 015_exploration_investigations_rls.sql

BEGIN;

ALTER TABLE user_investigations ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE investigation_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE hd_generation_jobs ENABLE ROW LEVEL SECURITY;

-- user_investigations
DROP POLICY IF EXISTS user_investigations_select ON user_investigations;
CREATE POLICY user_investigations_select ON user_investigations
    FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS user_investigations_insert ON user_investigations;
CREATE POLICY user_investigations_insert ON user_investigations
    FOR INSERT WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS user_investigations_update ON user_investigations;
CREATE POLICY user_investigations_update ON user_investigations
    FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS user_investigations_delete ON user_investigations;
CREATE POLICY user_investigations_delete ON user_investigations
    FOR DELETE USING (user_id = auth.uid());

DROP POLICY IF EXISTS user_investigations_service_role ON user_investigations;
CREATE POLICY user_investigations_service_role ON user_investigations
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- investigation_items
DROP POLICY IF EXISTS investigation_items_select ON investigation_items;
CREATE POLICY investigation_items_select ON investigation_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_items.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_items_insert ON investigation_items;
CREATE POLICY investigation_items_insert ON investigation_items
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_items.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_items_update ON investigation_items;
CREATE POLICY investigation_items_update ON investigation_items
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_items.investigation_id
              AND ui.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_items.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_items_delete ON investigation_items;
CREATE POLICY investigation_items_delete ON investigation_items
    FOR DELETE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_items.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_items_service_role ON investigation_items;
CREATE POLICY investigation_items_service_role ON investigation_items
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- investigation_assets
DROP POLICY IF EXISTS investigation_assets_select ON investigation_assets;
CREATE POLICY investigation_assets_select ON investigation_assets
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM investigation_items ii
            JOIN user_investigations ui ON ui.id = ii.investigation_id
            WHERE ii.id = investigation_assets.investigation_item_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_assets_insert ON investigation_assets;
CREATE POLICY investigation_assets_insert ON investigation_assets
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM investigation_items ii
            JOIN user_investigations ui ON ui.id = ii.investigation_id
            WHERE ii.id = investigation_assets.investigation_item_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_assets_update ON investigation_assets;
CREATE POLICY investigation_assets_update ON investigation_assets
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM investigation_items ii
            JOIN user_investigations ui ON ui.id = ii.investigation_id
            WHERE ii.id = investigation_assets.investigation_item_id
              AND ui.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1
            FROM investigation_items ii
            JOIN user_investigations ui ON ui.id = ii.investigation_id
            WHERE ii.id = investigation_assets.investigation_item_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_assets_delete ON investigation_assets;
CREATE POLICY investigation_assets_delete ON investigation_assets
    FOR DELETE USING (
        EXISTS (
            SELECT 1
            FROM investigation_items ii
            JOIN user_investigations ui ON ui.id = ii.investigation_id
            WHERE ii.id = investigation_assets.investigation_item_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_assets_service_role ON investigation_assets;
CREATE POLICY investigation_assets_service_role ON investigation_assets
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- investigation_shares
DROP POLICY IF EXISTS investigation_shares_select ON investigation_shares;
CREATE POLICY investigation_shares_select ON investigation_shares
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_shares.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_shares_insert ON investigation_shares;
CREATE POLICY investigation_shares_insert ON investigation_shares
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_shares.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_shares_update ON investigation_shares;
CREATE POLICY investigation_shares_update ON investigation_shares
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_shares.investigation_id
              AND ui.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_shares.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_shares_delete ON investigation_shares;
CREATE POLICY investigation_shares_delete ON investigation_shares
    FOR DELETE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = investigation_shares.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS investigation_shares_service_role ON investigation_shares;
CREATE POLICY investigation_shares_service_role ON investigation_shares
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- hd_generation_jobs
DROP POLICY IF EXISTS hd_generation_jobs_select ON hd_generation_jobs;
CREATE POLICY hd_generation_jobs_select ON hd_generation_jobs
    FOR SELECT USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = hd_generation_jobs.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS hd_generation_jobs_insert ON hd_generation_jobs;
CREATE POLICY hd_generation_jobs_insert ON hd_generation_jobs
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = hd_generation_jobs.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS hd_generation_jobs_update ON hd_generation_jobs;
CREATE POLICY hd_generation_jobs_update ON hd_generation_jobs
    FOR UPDATE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = hd_generation_jobs.investigation_id
              AND ui.user_id = auth.uid()
        )
    ) WITH CHECK (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = hd_generation_jobs.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS hd_generation_jobs_delete ON hd_generation_jobs;
CREATE POLICY hd_generation_jobs_delete ON hd_generation_jobs
    FOR DELETE USING (
        EXISTS (
            SELECT 1
            FROM user_investigations ui
            WHERE ui.id = hd_generation_jobs.investigation_id
              AND ui.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS hd_generation_jobs_service_role ON hd_generation_jobs;
CREATE POLICY hd_generation_jobs_service_role ON hd_generation_jobs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

COMMIT;
