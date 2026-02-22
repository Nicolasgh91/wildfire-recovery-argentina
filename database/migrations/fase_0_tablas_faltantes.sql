-- ============================================================
-- MIGRACIÓN CONSOLIDADA FASE 0: TABLAS BASE FALTANTES
-- ForestGuard - Wildfire Recovery Argentina
-- 
-- EJECUTAR ANTES de fire_event_quality_metrics.sql
-- Este script crea las tablas que bloquean UC-F04
-- ============================================================

BEGIN;

-- ============================================================
-- T0.1: CLIMATE_DATA
-- Datos climáticos de Open-Meteo (ERA5-Land) para análisis
-- Requerido por: UC-F04 (20% del score), UC-F11 (reportes)
-- ============================================================

CREATE TABLE IF NOT EXISTS climate_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ubicación y tiempo del registro climático
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    latitude NUMERIC(10, 6) NOT NULL,
    longitude NUMERIC(10, 6) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    
    -- Fuente de datos
    data_source VARCHAR(50) NOT NULL DEFAULT 'open-meteo',
    source_dataset VARCHAR(100),  -- e.g., 'ERA5-Land', 'ECMWF'
    
    -- Variables meteorológicas principales
    temperature_2m NUMERIC(5, 2),           -- °C
    relative_humidity_2m NUMERIC(5, 2),     -- %
    wind_speed_10m NUMERIC(6, 2),           -- km/h
    wind_direction_10m INTEGER,             -- degrees (0-360)
    wind_gusts_10m NUMERIC(6, 2),           -- km/h
    precipitation NUMERIC(6, 2),            -- mm
    
    -- Variables adicionales para análisis de incendios
    soil_moisture_0_to_10cm NUMERIC(5, 4),  -- m³/m³
    evapotranspiration NUMERIC(6, 2),       -- mm
    vapor_pressure_deficit NUMERIC(6, 2),   -- kPa
    
    -- Índices de riesgo de incendio (calculados)
    fire_weather_index NUMERIC(6, 2),       -- FWI (Canadian system)
    drought_code NUMERIC(6, 2),             -- DC
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint para evitar duplicados
    CONSTRAINT unique_climate_location_time 
        UNIQUE (latitude, longitude, recorded_at, data_source)
);

-- Índices para consultas eficientes
CREATE INDEX IF NOT EXISTS idx_climate_data_location 
    ON climate_data USING GIST (location);

CREATE INDEX IF NOT EXISTS idx_climate_data_recorded_at 
    ON climate_data (recorded_at);

CREATE INDEX IF NOT EXISTS idx_climate_data_location_time 
    ON climate_data (latitude, longitude, recorded_at);

COMMENT ON TABLE climate_data IS 
    'Datos climáticos de Open-Meteo (ERA5-Land) para análisis de incendios. '
    'Usado por UC-F04 (score de calidad, 20%) y UC-F11 (reportes judiciales).';


-- ============================================================
-- T0.2: FIRE_CLIMATE_ASSOCIATIONS
-- Relación N:M entre fire_events y climate_data
-- Requerido por: Vista fire_event_quality_metrics
-- ============================================================

CREATE TABLE IF NOT EXISTS fire_climate_associations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Referencias a las tablas relacionadas
    fire_event_id UUID NOT NULL 
        REFERENCES fire_events(id) ON DELETE CASCADE,
    climate_data_id UUID NOT NULL 
        REFERENCES climate_data(id) ON DELETE CASCADE,
    
    -- Tipo de asociación temporal
    association_type VARCHAR(30) NOT NULL DEFAULT 'during'
        CHECK (association_type IN (
            'before',   -- Condiciones previas al incendio
            'during',   -- Condiciones durante el incendio
            'after',    -- Condiciones posteriores
            'peak'      -- Momento de máxima intensidad
        )),
    
    -- Distancia temporal entre el registro climático y el evento
    hours_offset INTEGER,  -- Horas de diferencia (negativo = antes)
    
    -- Distancia espacial entre el centroide del incendio y el punto climático
    distance_km NUMERIC(8, 2),
    
    -- Peso de relevancia (para promedios ponderados)
    relevance_weight NUMERIC(3, 2) DEFAULT 1.0
        CHECK (relevance_weight >= 0 AND relevance_weight <= 1),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Evitar duplicados
    CONSTRAINT unique_fire_climate_assoc 
        UNIQUE (fire_event_id, climate_data_id, association_type)
);

-- Índices para consultas eficientes (JOINs en la vista)
CREATE INDEX IF NOT EXISTS idx_fca_fire_event 
    ON fire_climate_associations(fire_event_id);

CREATE INDEX IF NOT EXISTS idx_fca_climate_data 
    ON fire_climate_associations(climate_data_id);

CREATE INDEX IF NOT EXISTS idx_fca_type 
    ON fire_climate_associations(association_type);

COMMENT ON TABLE fire_climate_associations IS 
    'Relación N:M entre fire_events y climate_data. '
    'Permite asociar múltiples registros climáticos a cada incendio '
    'para el cálculo del score de calidad (UC-F04) y reportes (UC-F11).';


-- ============================================================
-- T0.3: DATA_SOURCE_METADATA
-- Metadata de fuentes de datos para score de calidad
-- Requerido por: UC-F04 (respuesta completa), UC-F11 (custodia)
-- ============================================================

CREATE TABLE IF NOT EXISTS data_source_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificación de la fuente
    source_name VARCHAR(50) NOT NULL UNIQUE,
    source_type VARCHAR(30) NOT NULL
        CHECK (source_type IN (
            'satellite_detection',  -- NASA FIRMS, etc.
            'satellite_imagery',    -- Sentinel-2, Landsat
            'climate',              -- Open-Meteo, ERA5
            'administrative',       -- Áreas protegidas, límites
            'derived'               -- Datos calculados internamente
        )),
    
    -- Proveedor y acceso
    provider VARCHAR(100) NOT NULL,
    provider_url TEXT,
    api_endpoint TEXT,
    
    -- Características técnicas
    spatial_resolution_meters INTEGER,
    temporal_resolution_hours INTEGER,
    update_frequency VARCHAR(50),  -- 'daily', 'hourly', '5-day revisit'
    
    -- Cobertura
    coverage_description TEXT,
    coverage_start_date DATE,
    
    -- Calidad y confiabilidad
    accuracy_description TEXT,
    known_limitations TEXT[],  -- Array de limitaciones conocidas
    confidence_baseline NUMERIC(3, 2),  -- 0.0 a 1.0
    
    -- Para el cálculo del score de calidad
    quality_weight NUMERIC(3, 2) DEFAULT 0.25
        CHECK (quality_weight >= 0 AND quality_weight <= 1),
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    last_validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_dsm_source_type 
    ON data_source_metadata(source_type);
CREATE INDEX IF NOT EXISTS idx_dsm_active 
    ON data_source_metadata(is_active) WHERE is_active = true;

COMMENT ON TABLE data_source_metadata IS 
    'Metadata de fuentes de datos para UC-F04 (score de calidad) y UC-F11 (cadena de custodia). '
    'Incluye resolución, limitaciones y peso en el cálculo de confiabilidad.';


-- ============================================================
-- DATOS INICIALES: Fuentes conocidas del sistema
-- ============================================================

INSERT INTO data_source_metadata (
    source_name, 
    source_type, 
    provider, 
    provider_url,
    spatial_resolution_meters, 
    temporal_resolution_hours,
    update_frequency, 
    confidence_baseline, 
    quality_weight,
    known_limitations,
    accuracy_description
) VALUES 
(
    'NASA_FIRMS_VIIRS',
    'satellite_detection',
    'NASA',
    'https://firms.modaps.eosdis.nasa.gov',
    375,
    12,
    'every 12 hours',
    0.85,
    0.40,
    ARRAY[
        'Cloud cover affects detection', 
        'Small fires (<100m²) may be missed', 
        'False positives possible near industrial areas',
        'Satellite overpass timing affects detection'
    ],
    'Detection confidence provided per observation (low/nominal/high)'
),
(
    'NASA_FIRMS_MODIS',
    'satellite_detection',
    'NASA',
    'https://firms.modaps.eosdis.nasa.gov',
    1000,
    12,
    'every 12 hours',
    0.80,
    0.35,
    ARRAY[
        'Lower resolution than VIIRS (1km vs 375m)', 
        'Cloud cover affects detection', 
        'Coarse spatial accuracy for small fires',
        'Legacy sensor, being phased out'
    ],
    'Detection confidence provided per observation (0-100%)'
),
(
    'SENTINEL2_L2A',
    'satellite_imagery',
    'ESA/Copernicus',
    'https://scihub.copernicus.eu',
    10,
    120,
    '5-day revisit',
    0.90,
    0.20,
    ARRAY[
        '5-day revisit time limits temporal resolution', 
        'Cloud cover significantly limits usability', 
        'Processing delay 24-48h from acquisition',
        'Swath width 290km may miss some areas'
    ],
    'Atmospheric correction applied (L2A), radiometric accuracy <5%'
),
(
    'OPEN_METEO_ERA5',
    'climate',
    'Open-Meteo',
    'https://open-meteo.com',
    9000,
    1,
    'hourly',
    0.85,
    0.20,
    ARRAY[
        'Reanalysis data (not real-time observations)', 
        '9km grid resolution may miss microclimate', 
        'Mountain areas may have higher uncertainty',
        'Data available with ~5 day delay'
    ],
    'ERA5-Land reanalysis, validated against ground stations'
)
ON CONFLICT (source_name) DO UPDATE SET
    spatial_resolution_meters = EXCLUDED.spatial_resolution_meters,
    temporal_resolution_hours = EXCLUDED.temporal_resolution_hours,
    confidence_baseline = EXCLUDED.confidence_baseline,
    quality_weight = EXCLUDED.quality_weight,
    known_limitations = EXCLUDED.known_limitations,
    updated_at = NOW();


-- ============================================================
-- VERIFICACIÓN FINAL
-- ============================================================

DO $$
DECLARE
    climate_count INTEGER;
    fca_count INTEGER;
    dsm_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO climate_count FROM information_schema.tables 
        WHERE table_name = 'climate_data';
    SELECT COUNT(*) INTO fca_count FROM information_schema.tables 
        WHERE table_name = 'fire_climate_associations';
    SELECT COUNT(*) INTO dsm_count FROM information_schema.tables 
        WHERE table_name = 'data_source_metadata';
    
END $$;

COMMIT;