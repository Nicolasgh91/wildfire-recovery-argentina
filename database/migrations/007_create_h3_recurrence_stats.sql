-- Migration: 007_create_h3_recurrence_stats.sql

DROP MATERIALIZED VIEW IF EXISTS h3_recurrence_stats;

CREATE MATERIALIZED VIEW h3_recurrence_stats AS
SELECT
    h3_index,
    COUNT(*) AS total_fires,
    COUNT(*) FILTER (WHERE start_date > NOW() - INTERVAL '5 years') AS fires_last_5_years,
    MAX(max_frp) AS max_frp_ever,
    SUM(estimated_area_hectares) AS total_hectares_burned,
    CASE
        WHEN COUNT(*) FILTER (WHERE start_date > NOW() - INTERVAL '5 years') > 3 THEN 'high'
        WHEN COUNT(*) FILTER (WHERE start_date > NOW() - INTERVAL '5 years') >= 1 THEN 'medium'
        ELSE 'low'
    END AS recurrence_class,
    LEAST(
        COUNT(*) FILTER (WHERE start_date > NOW() - INTERVAL '5 years')::NUMERIC / 5.0,
        1.0
    ) AS recurrence_score,
    NOW() AS calculated_at
FROM fire_events
WHERE h3_index IS NOT NULL
GROUP BY h3_index;

CREATE UNIQUE INDEX IF NOT EXISTS idx_h3_recurrence_h3
    ON h3_recurrence_stats(h3_index);
