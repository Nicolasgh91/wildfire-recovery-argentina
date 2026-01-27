-- =============================================================================
-- FORESTGUARD API - SCHEMA v0.2 CORREGIDO PARA SUPABASE
-- PostgreSQL 14+ con PostGIS 3.0+
-- Diseño: Fiscalización legal de incendios forestales (Ley 26.815 Art. 22 bis)
-- Fecha: 2025-01-25
-- =============================================================================

-- NOTA SUPABASE: Las extensiones postgis, uuid-ossp ya están habilitadas
-- Solo necesitamos pg_trgm
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- LAYER 1: RAW DETECTIONS (Datos crudos de sensores)
-- =============================================================================

CREATE TABLE IF NOT EXISTS fire_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Datos del sensor
    satellite VARCHAR(20) NOT NULL CHECK (satellite IN ('VIIRS', 'MODIS', 'VIIRS-NOAA20', 'VIIRS-NOAA21', 'VIIRS-SNPP')),
    instrument VARCHAR(20) NOT NULL,

    -- Espaciotemporal
    detected_at TIMESTAMPTZ NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    longitude NUMERIC(9,6) NOT NULL,

    -- Temperaturas (normalizadas)
    bt_mir_kelvin NUMERIC,
    bt_tir_kelvin NUMERIC,
    bt_delta_kelvin NUMERIC GENERATED ALWAYS AS (bt_mir_kelvin - bt_tir_kelvin) STORED,

    -- Potencia
    fire_radiative_power NUMERIC,

    -- Confianza
    confidence_raw VARCHAR(10),
    confidence_normalized SMALLINT CHECK (confidence_normalized >= 0 AND confidence_normalized <= 100),

    -- Metadata temporal
    acquisition_date DATE NOT NULL,
    acquisition_time TIME,
    daynight VARCHAR(1) CHECK (daynight IN ('D', 'N')),

    -- Procesamiento
    is_processed BOOLEAN DEFAULT FALSE,
    fire_event_id UUID,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fire_detections_location ON fire_detections USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_fire_detections_date ON fire_detections(acquisition_date DESC);
CREATE INDEX IF NOT EXISTS idx_fire_detections_satellite ON fire_detections(satellite);
CREATE INDEX IF NOT EXISTS idx_fire_detections_high_conf ON fire_detections(confidence_normalized) 
    WHERE confidence_normalized >= 80;
CREATE INDEX IF NOT EXISTS idx_fire_detections_unprocessed ON fire_detections(is_processed) 
    WHERE is_processed = FALSE;

COMMENT ON TABLE fire_detections IS 'Detecciones individuales de focos de calor de NASA FIRMS (MODIS/VIIRS). Datos crudos sin procesar.';
COMMENT ON COLUMN fire_detections.confidence_normalized IS 'Confianza normalizada 0-100. MODIS l/n/h -> 33/66/100, VIIRS usa valor directo.';

-- =============================================================================
-- LAYER 2: AGGREGATED EVENTS (Eventos únicos procesados)
-- =============================================================================

CREATE TABLE IF NOT EXISTS fire_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Geometría
    centroid GEOGRAPHY(POINT, 4326) NOT NULL,
    perimeter GEOGRAPHY(POLYGON, 4326),
    
    -- Temporal
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    duration_hours NUMERIC GENERATED ALWAYS AS 
        (EXTRACT(EPOCH FROM (end_date - start_date)) / 3600) STORED,
    
    -- Estadísticas del evento
    total_detections INTEGER NOT NULL DEFAULT 1,
    avg_frp NUMERIC,
    max_frp NUMERIC,
    sum_frp NUMERIC,
    estimated_area_hectares NUMERIC,
    
    -- Clasificación
    avg_confidence NUMERIC,
    is_significant BOOLEAN DEFAULT FALSE,
    
    -- Geográfico administrativo (desnormalizado para performance)
    province VARCHAR(100),
    department VARCHAR(100),
    
    -- Estado de procesamiento (flags para workers)
    has_satellite_imagery BOOLEAN DEFAULT FALSE,
    has_climate_data BOOLEAN DEFAULT FALSE,
    has_legal_analysis BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fire_events_start_date ON fire_events(start_date DESC);
CREATE INDEX IF NOT EXISTS idx_fire_events_centroid ON fire_events USING GIST(centroid);
CREATE INDEX IF NOT EXISTS idx_fire_events_province ON fire_events(province);
CREATE INDEX IF NOT EXISTS idx_fire_events_significant ON fire_events(is_significant) WHERE is_significant = TRUE;

COMMENT ON TABLE fire_events IS 'Eventos de incendio únicos, agregados desde múltiples detecciones cercanas en espacio/tiempo.';

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS fire_events_updated_at ON fire_events;
CREATE TRIGGER fire_events_updated_at 
    BEFORE UPDATE ON fire_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- FK de fire_detections a fire_events (después de crear fire_events)
ALTER TABLE fire_detections 
    DROP CONSTRAINT IF EXISTS fk_fire_detections_event;
ALTER TABLE fire_detections 
    ADD CONSTRAINT fk_fire_detections_event 
    FOREIGN KEY (fire_event_id) REFERENCES fire_events(id) ON DELETE SET NULL;

-- =============================================================================
-- LAYER 3: CONTEXTUAL DATA (Enriquecimiento geoespacial y climático)
-- =============================================================================

CREATE TABLE IF NOT EXISTS protected_areas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identificación oficial
    official_name VARCHAR(255) NOT NULL,
    alternative_names TEXT[],
    category VARCHAR(50) NOT NULL CHECK (category IN (
        'national_park',
        'provincial_reserve',
        'natural_monument',
        'biosphere_reserve',
        'ramsar_site',
        'provincial_park',
        'municipal_reserve'
    )),
    
    -- Geográfico
    boundary GEOGRAPHY(MULTIPOLYGON, 4326) NOT NULL,
    simplified_boundary GEOGRAPHY(POLYGON, 4326),
    centroid GEOGRAPHY(POINT, 4326),
    area_hectares NUMERIC,
    
    -- Administrativa
    jurisdiction VARCHAR(50) CHECK (jurisdiction IN ('national', 'provincial', 'municipal')),
    province VARCHAR(100),
    department VARCHAR(100),
    
    -- Legal (crítico para UC-01 y UC-07)
    prohibition_years INTEGER NOT NULL DEFAULT 60,
    
    -- Metadata
    established_date DATE,
    managing_authority VARCHAR(200),
    source_dataset VARCHAR(100),
    source_url TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_protected_areas_boundary ON protected_areas USING GIST(boundary);
CREATE INDEX IF NOT EXISTS idx_protected_areas_simplified ON protected_areas USING GIST(simplified_boundary);
CREATE INDEX IF NOT EXISTS idx_protected_areas_category ON protected_areas(category);
CREATE INDEX IF NOT EXISTS idx_protected_areas_name ON protected_areas USING GIN(official_name gin_trgm_ops);

COMMENT ON TABLE protected_areas IS 'Áreas protegidas de Argentina (Parques Nacionales, Reservas Provinciales, etc.)';
COMMENT ON COLUMN protected_areas.prohibition_years IS 'Años de prohibición de cambio de uso según Ley 26.815 Art. 22 bis (60 para bosques nativos, 30 para otras zonas).';

-- Intersecciones fuego-área protegida
CREATE TABLE IF NOT EXISTS fire_protected_area_intersections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    fire_event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    protected_area_id UUID NOT NULL REFERENCES protected_areas(id) ON DELETE CASCADE,
    
    -- Geométrico
    intersection_geometry GEOGRAPHY(POLYGON, 4326),
    intersection_area_hectares NUMERIC,
    overlap_percentage NUMERIC,
    
    -- Legal
    fire_date DATE NOT NULL,
    prohibition_until DATE NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(fire_event_id, protected_area_id)
);

CREATE INDEX IF NOT EXISTS idx_fire_pa_intersections_fire ON fire_protected_area_intersections(fire_event_id);
CREATE INDEX IF NOT EXISTS idx_fire_pa_intersections_area ON fire_protected_area_intersections(protected_area_id);
-- Índice simple sin predicado (el filtro se aplica en query time)
CREATE INDEX IF NOT EXISTS idx_fire_pa_intersections_prohibition ON fire_protected_area_intersections(prohibition_until DESC);

-- Datos climáticos
CREATE TABLE IF NOT EXISTS climate_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Referencia espaciotemporal
    reference_date DATE NOT NULL,
    latitude NUMERIC(6,3) NOT NULL,
    longitude NUMERIC(6,3) NOT NULL,
    spatial_cluster_id VARCHAR(20),
    
    -- Variables críticas para peritaje
    temp_max_celsius NUMERIC(4,1),
    temp_min_celsius NUMERIC(4,1),
    temp_mean_celsius NUMERIC(4,1),
    wind_speed_kmh NUMERIC(4,1),
    wind_direction_degrees SMALLINT CHECK (wind_direction_degrees >= 0 AND wind_direction_degrees <= 360),
    wind_gusts_kmh NUMERIC(4,1),
    precipitation_mm NUMERIC(5,1),
    relative_humidity_pct SMALLINT CHECK (relative_humidity_pct >= 0 AND relative_humidity_pct <= 100),
    
    -- Índices de sequía
    kbdi NUMERIC(5,1),
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'ERA5-Land',
    query_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_climate_data_lookup ON climate_data(reference_date, spatial_cluster_id);
CREATE INDEX IF NOT EXISTS idx_climate_data_date ON climate_data(reference_date DESC);

COMMENT ON TABLE climate_data IS 'Datos climáticos históricos de ERA5-Land (Open-Meteo) para contexto forense.';

-- Relación fuego-clima
CREATE TABLE IF NOT EXISTS fire_climate_associations (
    fire_event_id UUID PRIMARY KEY REFERENCES fire_events(id) ON DELETE CASCADE,
    climate_data_id UUID NOT NULL REFERENCES climate_data(id) ON DELETE CASCADE,
    
    distance_meters NUMERIC,
    assignment_method VARCHAR(50) DEFAULT 'spatial_cluster',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- LAYER 4: EVIDENCE & REPORTS (Evidencia visual y legal)
-- =============================================================================

CREATE TABLE IF NOT EXISTS satellite_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    fire_event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    
    -- Identificación de la imagen
    satellite VARCHAR(20) DEFAULT 'Sentinel-2',
    tile_id VARCHAR(50),
    product_id VARCHAR(100),
    acquisition_date DATE NOT NULL,
    acquisition_time TIME,
    
    -- Timing relativo al fuego
    days_after_fire INTEGER,
    image_type VARCHAR(20) CHECK (image_type IN ('pre_fire', 'post_fire', 'monthly_monitoring')),
    
    -- Calidad
    cloud_cover_pct NUMERIC(4,1) CHECK (cloud_cover_pct >= 0 AND cloud_cover_pct <= 100),
    quality_score VARCHAR(20) CHECK (quality_score IN ('excellent', 'good', 'fair', 'poor', 'unusable')),
    usable_for_analysis BOOLEAN DEFAULT TRUE,
    
    -- Storage en Cloudflare R2
    r2_bucket VARCHAR(100) DEFAULT 'forestguard-images',
    r2_key TEXT NOT NULL,
    r2_url TEXT NOT NULL,
    thumbnail_url TEXT,
    file_size_mb NUMERIC(8,2),
    
    -- Procesamiento
    bands_included TEXT[],
    processing_level VARCHAR(10) DEFAULT 'L2A',
    spatial_resolution_meters SMALLINT DEFAULT 10,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_satellite_images_fire ON satellite_images(fire_event_id);
CREATE INDEX IF NOT EXISTS idx_satellite_images_type ON satellite_images(image_type);
CREATE INDEX IF NOT EXISTS idx_satellite_images_quality ON satellite_images(quality_score) 
    WHERE quality_score IN ('excellent', 'good');

COMMENT ON TABLE satellite_images IS 'Imágenes Sentinel-2 (pre/post fuego) almacenadas en Cloudflare R2.';

-- Seguimiento de recuperación de vegetación (UC-06)
CREATE TABLE IF NOT EXISTS vegetation_monitoring (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    fire_event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    satellite_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    
    -- Temporal
    month_number SMALLINT CHECK (month_number >= 1 AND month_number <= 36),
    monitoring_date DATE NOT NULL,
    months_after_fire INTEGER,
    
    -- Métricas de vegetación
    ndvi_mean NUMERIC(4,3) CHECK (ndvi_mean >= -1 AND ndvi_mean <= 1),
    ndvi_min NUMERIC(4,3) CHECK (ndvi_min >= -1 AND ndvi_min <= 1),
    ndvi_max NUMERIC(4,3) CHECK (ndvi_max >= -1 AND ndvi_max <= 1),
    ndvi_std_dev NUMERIC(4,3),
    
    -- Comparación con baseline
    baseline_ndvi NUMERIC(4,3),
    recovery_percentage NUMERIC(5,2),
    
    -- UC-08: Detección de cambio de uso
    land_use_classification VARCHAR(50) CHECK (land_use_classification IN (
        'natural_recovery',
        'bare_soil',
        'agriculture_detected',
        'construction_detected',
        'roads_detected',
        'mining_activity',
        'uncertain'
    )),
    classification_confidence NUMERIC(3,2) CHECK (classification_confidence >= 0 AND classification_confidence <= 1),
    classification_method VARCHAR(50) DEFAULT 'rule_based',
    
    -- Detección de actividad humana
    human_activity_detected BOOLEAN DEFAULT FALSE,
    activity_type VARCHAR(50),
    activity_confidence VARCHAR(20),
    
    -- Observaciones
    notes TEXT,
    analyst_name VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vegetation_monitoring_fire ON vegetation_monitoring(fire_event_id);
CREATE INDEX IF NOT EXISTS idx_vegetation_monitoring_month ON vegetation_monitoring(month_number);
CREATE INDEX IF NOT EXISTS idx_vegetation_monitoring_activity ON vegetation_monitoring(human_activity_detected) 
    WHERE human_activity_detected = TRUE;

COMMENT ON TABLE vegetation_monitoring IS 'Seguimiento mensual de recuperación de vegetación post-incendio (NDVI).';

-- =============================================================================
-- UC-08: LAND USE CHANGES (Detección de cambios post-incendio)
-- =============================================================================

CREATE TABLE IF NOT EXISTS land_use_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    fire_event_id UUID NOT NULL REFERENCES fire_events(id) ON DELETE CASCADE,
    monitoring_record_id UUID REFERENCES vegetation_monitoring(id) ON DELETE SET NULL,
    
    -- Detección del cambio
    change_detected_at DATE NOT NULL,
    months_after_fire INTEGER,
    
    -- Tipo de cambio
    change_type VARCHAR(50) NOT NULL,
    change_severity VARCHAR(20) CHECK (change_severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Evidencia visual
    before_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    after_image_id UUID REFERENCES satellite_images(id) ON DELETE SET NULL,
    change_detection_image_url TEXT,
    
    -- Análisis
    affected_area_hectares NUMERIC,
    is_potential_violation BOOLEAN DEFAULT FALSE,
    violation_confidence VARCHAR(20),
    
    -- Estado
    status VARCHAR(50) DEFAULT 'pending_review' CHECK (status IN (
        'pending_review',
        'confirmed_violation',
        'false_positive',
        'under_investigation',
        'reported_to_authorities'
    )),
    
    -- Seguimiento
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_land_use_changes_fire ON land_use_changes(fire_event_id);
CREATE INDEX IF NOT EXISTS idx_land_use_changes_violations ON land_use_changes(is_potential_violation) 
    WHERE is_potential_violation = TRUE;
CREATE INDEX IF NOT EXISTS idx_land_use_changes_status ON land_use_changes(status);

COMMENT ON TABLE land_use_changes IS 'UC-08: Cambios detectados en el uso del suelo post-incendio (posibles violaciones).';

-- =============================================================================
-- UC-01: LAND USE AUDITS (Consultas de usuarios)
-- =============================================================================

CREATE TABLE IF NOT EXISTS land_use_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Query del usuario
    queried_latitude NUMERIC(9,6) NOT NULL,
    queried_longitude NUMERIC(9,6) NOT NULL,
    queried_location GEOGRAPHY(POINT, 4326) NOT NULL,
    search_radius_meters INTEGER DEFAULT 500,
    
    -- Timestamp
    queried_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Resultados
    fires_found INTEGER DEFAULT 0,
    earliest_fire_date TIMESTAMPTZ,
    latest_fire_date TIMESTAMPTZ,
    prohibition_until DATE,
    is_violation BOOLEAN DEFAULT FALSE,
    violation_severity VARCHAR(20) CHECK (violation_severity IN ('none', 'low', 'medium', 'high', 'critical')),
    
    -- Evidencia generada
    report_generated BOOLEAN DEFAULT FALSE,
    report_pdf_url TEXT,
    report_json JSONB,
    
    -- Metadata de usuario
    user_ip INET,
    user_agent TEXT,
    api_key_id UUID,
    
    -- Performance
    query_duration_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_land_use_audits_location ON land_use_audits USING GIST(queried_location);
CREATE INDEX IF NOT EXISTS idx_land_use_audits_date ON land_use_audits(queried_at DESC);
CREATE INDEX IF NOT EXISTS idx_land_use_audits_violations ON land_use_audits(is_violation) WHERE is_violation = TRUE;
CREATE INDEX IF NOT EXISTS idx_land_use_audits_ip ON land_use_audits(user_ip, queried_at);

COMMENT ON TABLE land_use_audits IS 'UC-01: Log de consultas de usuarios sobre cambio de uso del suelo (auditoría legal).';

-- =============================================================================
-- UC-07: LAND CERTIFICATES (Certificación legal)
-- =============================================================================

CREATE TABLE IF NOT EXISTS land_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Referencia a la auditoría
    audit_id UUID NOT NULL REFERENCES land_use_audits(id) ON DELETE CASCADE,
    
    -- Datos del terreno
    queried_location GEOGRAPHY(POINT, 4326) NOT NULL,
    cadastral_id VARCHAR(100),
    address TEXT,
    
    -- Resultado legal
    is_legally_exploitable BOOLEAN NOT NULL,
    legal_status VARCHAR(50) CHECK (legal_status IN (
        'clear',
        'prohibited_protected_area',
        'prohibited_recent_fire',
        'restricted_partial',
        'under_investigation'
    )),
    
    -- Evidencia
    fire_events_affecting JSONB,
    earliest_prohibition_date DATE,
    prohibition_expires_on DATE,
    
    -- Metadata del certificado
    certificate_number VARCHAR(50) UNIQUE NOT NULL,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    
    -- Verificación anti-falsificación
    verification_hash VARCHAR(64) NOT NULL,
    pdf_url TEXT,
    qr_code_url TEXT,
    
    -- Solicitante
    requester_email VARCHAR(255),
    requester_organization VARCHAR(200),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_land_certificates_location ON land_certificates USING GIST(queried_location);
CREATE INDEX IF NOT EXISTS idx_land_certificates_status ON land_certificates(legal_status);
CREATE INDEX IF NOT EXISTS idx_land_certificates_number ON land_certificates(certificate_number);
-- Índice simple sin predicado (el filtro se aplica en query time)
CREATE INDEX IF NOT EXISTS idx_land_certificates_valid ON land_certificates(valid_until DESC);

COMMENT ON TABLE land_certificates IS 'UC-07: Certificados de condición legal del terreno emitidos por la API.';

-- =============================================================================
-- UC-09: CITIZEN REPORTS (Denuncias ciudadanas)
-- =============================================================================

CREATE TABLE IF NOT EXISTS citizen_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Ubicación denunciada
    reported_location GEOGRAPHY(POINT, 4326) NOT NULL,
    reported_latitude NUMERIC(9,6) NOT NULL,
    reported_longitude NUMERIC(9,6) NOT NULL,
    location_description TEXT,
    
    -- Tipo de denuncia
    report_type VARCHAR(50) CHECK (report_type IN (
        'illegal_land_clearing',
        'construction_in_prohibited_area',
        'suspicious_fire',
        'illegal_logging',
        'agricultural_expansion',
        'other'
    )),
    
    -- Descripción
    description TEXT NOT NULL,
    observed_date DATE,
    
    -- Evidencia del usuario
    user_photos TEXT[],
    
    -- Datos del denunciante
    reporter_name VARCHAR(200),
    reporter_email VARCHAR(255),
    reporter_phone VARCHAR(50),
    is_anonymous BOOLEAN DEFAULT FALSE,
    reporter_organization VARCHAR(200),
    
    -- Auto-cruce con datos del sistema
    related_fire_events UUID[],
    related_protected_areas UUID[],
    historical_fires_in_area INTEGER,
    
    -- Paquete de evidencia
    evidence_package_url TEXT,
    
    -- Estado
    status VARCHAR(50) DEFAULT 'submitted' CHECK (status IN (
        'submitted',
        'under_review',
        'evidence_collected',
        'forwarded_to_authorities',
        'closed_verified',
        'closed_unverified',
        'duplicate'
    )),
    
    -- Seguimiento
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    authority_notified VARCHAR(200),
    authority_notified_at TIMESTAMPTZ,
    internal_notes TEXT,
    
    -- Privacy
    is_public BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_citizen_reports_location ON citizen_reports USING GIST(reported_location);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_type ON citizen_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_status ON citizen_reports(status);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_date ON citizen_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_citizen_reports_public ON citizen_reports(is_public) WHERE is_public = TRUE;

DROP TRIGGER IF EXISTS citizen_reports_updated_at ON citizen_reports;
CREATE TRIGGER citizen_reports_updated_at 
    BEFORE UPDATE ON citizen_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE citizen_reports IS 'UC-09: Denuncias ciudadanas sobre actividad ilegal en áreas afectadas por incendios.';

-- =============================================================================
-- UC-11: DATA QUALITY METADATA
-- =============================================================================

CREATE TABLE IF NOT EXISTS data_source_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source_name VARCHAR(100) NOT NULL UNIQUE,
    source_type VARCHAR(50) CHECK (source_type IN ('satellite', 'reanalysis', 'ground_station', 'manual')),
    
    -- Características técnicas
    spatial_resolution_meters INTEGER,
    temporal_resolution_hours INTEGER,
    coverage_area TEXT,
    
    -- Confiabilidad
    typical_accuracy_percentage NUMERIC(4,1),
    known_limitations TEXT,
    
    -- Legal
    is_admissible_in_court BOOLEAN,
    legal_precedent_cases TEXT[],
    
    -- Metadata
    data_provider VARCHAR(200),
    provider_url TEXT,
    documentation_url TEXT,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE data_source_metadata IS 'UC-11: Metadata sobre fuentes de datos para transparencia y confiabilidad.';

-- Seed data para fuentes conocidas
INSERT INTO data_source_metadata (source_name, source_type, spatial_resolution_meters, typical_accuracy_percentage, is_admissible_in_court, data_provider, documentation_url) VALUES
('NASA_FIRMS_VIIRS', 'satellite', 375, 85.0, TRUE, 'NASA', 'https://firms.modaps.eosdis.nasa.gov/'),
('NASA_FIRMS_MODIS', 'satellite', 1000, 75.0, TRUE, 'NASA', 'https://firms.modaps.eosdis.nasa.gov/'),
('Sentinel2_L2A', 'satellite', 10, 95.0, TRUE, 'ESA Copernicus', 'https://sentinels.copernicus.eu/'),
('ERA5_Land', 'reanalysis', 9000, 80.0, FALSE, 'ECMWF', 'https://cds.climate.copernicus.eu/')
ON CONFLICT (source_name) DO NOTHING;

-- =============================================================================
-- VIEWS (Consultas comunes optimizadas) - CORREGIDAS
-- =============================================================================

-- Vista: Fuegos recientes de alta confianza (CORREGIDO: bt_mir_kelvin, bt_tir_kelvin)
CREATE OR REPLACE VIEW recent_high_confidence_fires AS
SELECT 
    fe.*,
    COUNT(fd.id) as detection_count,
    MAX(fd.bt_mir_kelvin) as max_bt_mir_kelvin,
    MAX(fd.bt_tir_kelvin) as max_bt_tir_kelvin
FROM fire_events fe
JOIN fire_detections fd ON fd.fire_event_id = fe.id
WHERE fe.start_date >= NOW() - INTERVAL '30 days'
  AND fe.avg_confidence >= 80
GROUP BY fe.id;

-- Vista: Áreas protegidas con fuegos recientes
CREATE OR REPLACE VIEW protected_areas_recent_fires AS
SELECT 
    pa.official_name,
    pa.category,
    pa.province,
    COUNT(DISTINCT fpai.fire_event_id) as fire_count_last_year,
    SUM(fpai.intersection_area_hectares) as total_burned_hectares,
    MAX(fpai.prohibition_until) as prohibition_valid_until
FROM protected_areas pa
LEFT JOIN fire_protected_area_intersections fpai ON fpai.protected_area_id = pa.id
LEFT JOIN fire_events fe ON fe.id = fpai.fire_event_id
WHERE fe.start_date >= NOW() - INTERVAL '1 year'
GROUP BY pa.id, pa.official_name, pa.category, pa.province;

-- Vista UC-11: Métricas de calidad por evento
CREATE OR REPLACE VIEW fire_event_quality_metrics AS
SELECT 
    fe.id as fire_event_id,
    fe.start_date,
    
    -- Métricas de detección
    COUNT(DISTINCT fd.satellite) as satellite_sources_count,
    AVG(fd.confidence_normalized) as avg_detection_confidence,
    MIN(fd.confidence_normalized) as min_detection_confidence,
    fe.total_detections,
    
    -- Calidad de imágenes
    COUNT(si.id) FILTER (WHERE si.quality_score IN ('excellent', 'good')) as good_images_count,
    AVG(si.cloud_cover_pct) as avg_cloud_cover,
    
    -- Disponibilidad de contexto
    CASE WHEN fca.climate_data_id IS NOT NULL THEN TRUE ELSE FALSE END as has_climate_data,
    CASE WHEN fpai.id IS NOT NULL THEN TRUE ELSE FALSE END as has_protected_area_data,
    
    -- Score de confiabilidad (0-100)
    (
        (COALESCE(AVG(fd.confidence_normalized), 0) * 0.4) +
        (CASE WHEN COUNT(si.id) > 0 THEN 20 ELSE 0 END) +
        (CASE WHEN fca.climate_data_id IS NOT NULL THEN 20 ELSE 0 END) +
        (CASE WHEN fe.total_detections >= 3 THEN 20 ELSE LEAST(fe.total_detections * 6.67, 20) END)
    ) as reliability_score,
    
    -- Clasificación
    CASE 
        WHEN (
            (COALESCE(AVG(fd.confidence_normalized), 0) * 0.4) +
            (CASE WHEN COUNT(si.id) > 0 THEN 20 ELSE 0 END) +
            (CASE WHEN fca.climate_data_id IS NOT NULL THEN 20 ELSE 0 END) +
            (CASE WHEN fe.total_detections >= 3 THEN 20 ELSE LEAST(fe.total_detections * 6.67, 20) END)
        ) >= 80 THEN 'high'
        WHEN (
            (COALESCE(AVG(fd.confidence_normalized), 0) * 0.4) +
            (CASE WHEN COUNT(si.id) > 0 THEN 20 ELSE 0 END) +
            (CASE WHEN fca.climate_data_id IS NOT NULL THEN 20 ELSE 0 END) +
            (CASE WHEN fe.total_detections >= 3 THEN 20 ELSE LEAST(fe.total_detections * 6.67, 20) END)
        ) >= 50 THEN 'medium'
        ELSE 'low'
    END as reliability_class

FROM fire_events fe
LEFT JOIN fire_detections fd ON fd.fire_event_id = fe.id
LEFT JOIN satellite_images si ON si.fire_event_id = fe.id
LEFT JOIN fire_climate_associations fca ON fca.fire_event_id = fe.id
LEFT JOIN fire_protected_area_intersections fpai ON fpai.fire_event_id = fe.id
GROUP BY fe.id, fca.climate_data_id, fpai.id;

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Normalizar confidence de diferentes satélites (MODIS/VIIRS)
CREATE OR REPLACE FUNCTION normalize_confidence(raw_value VARCHAR)
RETURNS SMALLINT
LANGUAGE plpgsql
AS $$
DECLARE
  v TEXT;
  n NUMERIC;
BEGIN
  v := lower(coalesce(raw_value, ''));

  IF v IN ('l', 'low') THEN
    RETURN 33;
  ELSIF v IN ('n', 'nominal') THEN
    RETURN 66;
  ELSIF v IN ('h', 'high') THEN
    RETURN 100;
  ELSE
    BEGIN
      n := v::NUMERIC;

      IF n < 0 THEN
        RETURN 0;
      ELSIF n > 100 THEN
        RETURN 100;
      ELSE
        RETURN n::SMALLINT;
      END IF;

    EXCEPTION WHEN OTHERS THEN
      RETURN 0;
    END;
  END IF;
END;
$$;

-- =============================================================================
-- RLS POLICIES (Supabase Row Level Security)
-- =============================================================================

-- Habilitar RLS en tablas públicas
ALTER TABLE fire_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE fire_detections ENABLE ROW LEVEL SECURITY;
ALTER TABLE protected_areas ENABLE ROW LEVEL SECURITY;
ALTER TABLE land_use_audits ENABLE ROW LEVEL SECURITY;
ALTER TABLE land_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE citizen_reports ENABLE ROW LEVEL SECURITY;

-- Políticas de lectura pública para datos de incendios
CREATE POLICY "fire_events_public_read" ON fire_events FOR SELECT USING (true);
CREATE POLICY "fire_detections_public_read" ON fire_detections FOR SELECT USING (true);
CREATE POLICY "protected_areas_public_read" ON protected_areas FOR SELECT USING (true);

-- Políticas para audits y certificates (solo lectura pública)
CREATE POLICY "land_use_audits_public_read" ON land_use_audits FOR SELECT USING (true);
CREATE POLICY "land_certificates_public_read" ON land_certificates FOR SELECT USING (true);

-- Denuncias ciudadanas: solo las públicas son visibles
CREATE POLICY "citizen_reports_public_read" ON citizen_reports FOR SELECT USING (is_public = true);

-- =============================================================================
-- VERIFICACIÓN FINAL
-- =============================================================================

-- Verificar que todas las tablas se crearon correctamente
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE'
    AND table_name IN (
        'fire_detections', 'fire_events', 'protected_areas',
        'fire_protected_area_intersections', 'climate_data',
        'fire_climate_associations', 'satellite_images',
        'vegetation_monitoring', 'land_use_changes',
        'land_use_audits', 'land_certificates',
        'citizen_reports', 'data_source_metadata'
    );
    
    IF table_count = 13 THEN
        RAISE NOTICE '✅ Schema v0.2 instalado correctamente: % tablas creadas', table_count;
    ELSE
        RAISE WARNING '⚠️ Solo % de 13 tablas creadas', table_count;
    END IF;
END $$;