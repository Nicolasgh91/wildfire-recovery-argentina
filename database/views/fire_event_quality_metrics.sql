-- Materialized view for quality metrics (UC-F04)
-- Provides cached component scores for each fire event.

CREATE TABLE IF NOT EXISTS data_source_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(100) UNIQUE NOT NULL,
    source_type VARCHAR(50),
    spatial_resolution_meters INTEGER,
    temporal_resolution_hours INTEGER,
    coverage_area TEXT,
    typical_accuracy_percentage DOUBLE PRECISION,
    known_limitations TEXT,
    is_admissible_in_court BOOLEAN,
    legal_precedent_cases TEXT[],
    data_provider VARCHAR(200),
    provider_url TEXT,
    documentation_url TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

DROP MATERIALIZED VIEW IF EXISTS fire_event_quality_metrics;

CREATE MATERIALIZED VIEW fire_event_quality_metrics AS
WITH base_events AS (
    SELECT
        fe.id AS fire_event_id,
        fe.start_date,
        fe.province,
        COALESCE(fe.total_detections, 0) AS total_detections,
        COALESCE(fe.avg_confidence, 0) AS avg_confidence
    FROM fire_events fe
),
detections AS (
    SELECT
        fd.fire_event_id,
        COUNT(fd.id) AS detection_count,
        COUNT(DISTINCT fd.satellite) AS independent_sources
    FROM fire_detections fd
    GROUP BY fd.fire_event_id
),
imagery AS (
    SELECT
        si.fire_event_id,
        COUNT(si.id) AS imagery_count
    FROM satellite_images si
    GROUP BY si.fire_event_id
),
climate AS (
    SELECT
        fca.fire_event_id,
        COUNT(fca.fire_event_id) AS climate_count
    FROM fire_climate_associations fca
    GROUP BY fca.fire_event_id
),
ndvi AS (
    SELECT
        vm.fire_event_id,
        COUNT(vm.id) AS ndvi_count
    FROM vegetation_monitoring vm
    GROUP BY vm.fire_event_id
),
weights AS (
    SELECT param_value
    FROM system_parameters
    WHERE param_key = 'quality_weights'
    LIMIT 1
)
SELECT
    base.fire_event_id,
    base.start_date,
    base.province,
    base.total_detections,
    base.avg_confidence,
    COALESCE(det.detection_count, 0) AS detection_count,
    COALESCE(det.independent_sources, 0) AS independent_sources,
    COALESCE(img.imagery_count, 0) AS imagery_count,
    (COALESCE(img.imagery_count, 0) > 0) AS has_imagery,
    (COALESCE(cli.climate_count, 0) > 0) AS has_climate,
    (COALESCE(ndv.ndvi_count, 0) > 0) AS has_ndvi,
    LEAST(GREATEST(COALESCE(base.avg_confidence, 0), 0), 100) AS confidence_score,
    CASE WHEN COALESCE(img.imagery_count, 0) > 0 THEN 100 ELSE 0 END AS imagery_score,
    CASE WHEN COALESCE(cli.climate_count, 0) > 0 THEN 100 ELSE 0 END AS climate_score,
    CASE
        WHEN COALESCE(det.independent_sources, 0) >= 2 THEN 100
        WHEN COALESCE(det.independent_sources, 0) = 1 THEN 50
        ELSE 0
    END AS independent_score,
    (
        LEAST(GREATEST(COALESCE(base.avg_confidence, 0), 0), 100)
            * COALESCE((weights.param_value->>'detections')::numeric, 0.4)
        + (CASE WHEN COALESCE(img.imagery_count, 0) > 0 THEN 100 ELSE 0 END)
            * COALESCE((weights.param_value->>'imagery')::numeric, 0.2)
        + (CASE WHEN COALESCE(cli.climate_count, 0) > 0 THEN 100 ELSE 0 END)
            * COALESCE((weights.param_value->>'climate')::numeric, 0.2)
        + (CASE
            WHEN COALESCE(det.independent_sources, 0) >= 2 THEN 100
            WHEN COALESCE(det.independent_sources, 0) = 1 THEN 50
            ELSE 0
        END) * COALESCE((weights.param_value->>'independent')::numeric, 0.2)
    )::numeric(5, 2) AS reliability_score,
    NOW() AS score_calculated_at
FROM base_events base
LEFT JOIN detections det ON det.fire_event_id = base.fire_event_id
LEFT JOIN imagery img ON img.fire_event_id = base.fire_event_id
LEFT JOIN climate cli ON cli.fire_event_id = base.fire_event_id
LEFT JOIN ndvi ndv ON ndv.fire_event_id = base.fire_event_id
LEFT JOIN weights ON TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fire_event_quality_metrics_event_id
ON fire_event_quality_metrics(fire_event_id);

COMMENT ON MATERIALIZED VIEW fire_event_quality_metrics IS
    'Cached quality metrics per fire event (UC-F04).';
