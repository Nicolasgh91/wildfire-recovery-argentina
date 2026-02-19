-- RPC function for public statistics (UC-F02)
-- Exposes aggregated fire metrics with date range validation and province filter.

CREATE SCHEMA IF NOT EXISTS api;

CREATE OR REPLACE FUNCTION api.get_public_stats(
    p_date_from DATE,
    p_date_to DATE,
    p_province TEXT DEFAULT NULL
)
RETURNS TABLE (
    stat_date DATE,
    province TEXT,
    fire_count BIGINT,
    total_hectares NUMERIC,
    frp_max NUMERIC,
    frp_sum NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, api
AS $$
BEGIN
    IF p_date_from IS NULL OR p_date_to IS NULL THEN
        RAISE EXCEPTION 'date_from and date_to are required'
            USING ERRCODE = 'P0001';
    END IF;

    IF p_date_to < p_date_from THEN
        RAISE EXCEPTION 'date_to must be >= date_from'
            USING ERRCODE = 'P0001';
    END IF;

    -- Validate date range (max 730 days)
    IF p_date_to - p_date_from > 730 THEN
        RAISE EXCEPTION 'Date range cannot exceed 730 days'
            USING ERRCODE = 'P0001';
    END IF;

    p_province := NULLIF(BTRIM(p_province), '');

    IF p_date_to - p_date_from > 90 THEN
        -- Monthly aggregation
        RETURN QUERY
        SELECT
            date_trunc('month', fs.stat_date)::DATE AS stat_date,
            fs.province::TEXT,
            SUM(fs.fire_count)::BIGINT,
            SUM(fs.total_hectares)::NUMERIC,
            MAX(fs.frp_max)::NUMERIC,
            SUM(fs.frp_sum)::NUMERIC
        FROM public.fire_stats fs
        WHERE fs.stat_date BETWEEN p_date_from AND p_date_to
          AND (p_province IS NULL OR fs.province = p_province)
        GROUP BY date_trunc('month', fs.stat_date), fs.province
        ORDER BY 1, 2;
    ELSE
        -- Daily data
        RETURN QUERY
        SELECT
            fs.stat_date::DATE,
            fs.province::TEXT,
            fs.fire_count::BIGINT,
            fs.total_hectares::NUMERIC,
            fs.frp_max::NUMERIC,
            fs.frp_sum::NUMERIC
        FROM public.fire_stats fs
        WHERE fs.stat_date BETWEEN p_date_from AND p_date_to
          AND (p_province IS NULL OR fs.province = p_province)
        ORDER BY fs.stat_date, fs.province;
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION api.get_public_stats FROM PUBLIC;
GRANT USAGE ON SCHEMA api TO anon;
GRANT EXECUTE ON FUNCTION api.get_public_stats TO anon;
