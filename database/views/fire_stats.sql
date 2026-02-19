-- Materialized view for public fire statistics (UC-F02)
-- Aggregates daily fire events by province for fast public access.

CREATE MATERIALIZED VIEW IF NOT EXISTS fire_stats AS
SELECT
    date_trunc('day', start_date)::date AS stat_date,
    province,
    COUNT(*)::bigint AS fire_count,
    COALESCE(SUM(estimated_area_hectares), 0) AS total_hectares,
    MAX(max_frp) AS frp_max,
    COALESCE(SUM(sum_frp), 0) AS frp_sum
FROM fire_events
WHERE province IS NOT NULL
GROUP BY 1, 2;

-- Unique index required for REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_fire_stats_stat_date_province
ON fire_stats(stat_date, province);

-- Supporting indexes for common filters
CREATE INDEX IF NOT EXISTS idx_fire_stats_stat_date ON fire_stats(stat_date);
CREATE INDEX IF NOT EXISTS idx_fire_stats_province ON fire_stats(province);

COMMENT ON MATERIALIZED VIEW fire_stats IS
    'Daily aggregated fire statistics by province for public stats (UC-F02).';
