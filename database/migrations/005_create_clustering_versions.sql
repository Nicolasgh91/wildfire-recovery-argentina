-- Migration: 005_create_clustering_versions.sql

CREATE TABLE IF NOT EXISTS clustering_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_name VARCHAR(50) NOT NULL,
    epsilon_km NUMERIC NOT NULL CHECK (epsilon_km > 0 AND epsilon_km <= 100),
    min_points INTEGER NOT NULL CHECK (min_points >= 1 AND min_points <= 100),
    temporal_window_hours INTEGER NOT NULL CHECK (temporal_window_hours >= 1),
    algorithm VARCHAR(20) NOT NULL DEFAULT 'ST-DBSCAN',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT true,
    change_reason TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_clustering_single_active
    ON clustering_versions(is_active) WHERE is_active = true;

INSERT INTO clustering_versions (version_name, epsilon_km, min_points, temporal_window_hours, change_reason)
VALUES ('v1.0-initial', 5.0, 3, 24, 'Configuracion inicial')
ON CONFLICT DO NOTHING;
