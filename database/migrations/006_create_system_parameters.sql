-- Migration: 006_create_system_parameters.sql

CREATE TABLE IF NOT EXISTS system_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    param_key VARCHAR(50) NOT NULL,
    param_value JSONB NOT NULL,
    description TEXT,
    category VARCHAR(30) DEFAULT 'general',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID REFERENCES users(id),
    previous_values JSONB DEFAULT '[]'::jsonb,
    CONSTRAINT system_parameters_category_check
        CHECK (category IN (
            'general', 'audit', 'imagery', 'reports',
            'clustering', 'notifications', 'limits'
        )),
    CONSTRAINT system_parameters_param_key_unique UNIQUE (param_key)
);

CREATE OR REPLACE FUNCTION track_parameter_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.param_value IS DISTINCT FROM NEW.param_value THEN
        NEW.previous_values = COALESCE(OLD.previous_values, '[]'::jsonb)
            || jsonb_build_array(jsonb_build_object(
                'value', OLD.param_value,
                'changed_at', OLD.updated_at,
                'changed_by', OLD.updated_by
            ));
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_track_parameter_changes ON system_parameters;
CREATE TRIGGER trg_track_parameter_changes
BEFORE UPDATE ON system_parameters
FOR EACH ROW EXECUTE FUNCTION track_parameter_changes();

INSERT INTO system_parameters (param_key, param_value, description, category) VALUES
('audit_search_radius_default',
 '{"value": 500, "unit": "meters"}',
 'Default search radius for land use audits',
 'audit'),

('audit_search_radius_max',
 '{"value": 5000, "unit": "meters", "is_hard_cap": true}',
 'Max allowed search radius (hard cap)',
 'audit'),

('carousel_batch_size',
 '{"value": 15}',
 'Number of fires processed per carousel batch',
 'imagery'),

('cloud_coverage_thresholds',
 '{"initial": 10, "increments": [20, 30, 50], "max": 50}',
 'Adaptive cloud thresholds for imagery selection',
 'imagery'),

('carousel_priority_weights',
 '{"proximity_pa": 0.40, "frp": 0.30, "area": 0.20, "recurrence": 0.10}',
 'Weights for carousel priority scoring',
 'imagery'),

('closure_report_min_area_ha',
 '{"value": 10}',
 'Minimum area (ha) for auto-generating closure reports',
 'reports'),

('closure_report_max_retry_days',
 '{"value": 30}',
 'Max retry days before marking closure report incomplete',
 'reports'),

('closure_report_cloud_max',
 '{"value": 40, "with_cloud_masking": true}',
 'Max cloud threshold with cloud masking enabled',
 'reports'),

('dashboard_page_size_default',
 '{"value": 20}',
 'Default page size for listings',
 'limits'),

('dashboard_page_size_max',
 '{"value": 100, "is_hard_cap": true}',
 'Max page size (hard cap for DoS protection)',
 'limits'),

('h3_max_cells_per_query',
 '{"value": 5000, "is_hard_cap": true}',
 'Max H3 cells per query (DoS protection)',
 'limits'),

('report_max_images',
 '{"value": 12, "is_fixed": true}',
 'Fixed number of images per historical report',
 'reports'),

('report_image_cost_usd',
 '{"value": 0.50}',
 'USD cost per HD image in reports',
 'reports')
ON CONFLICT (param_key) DO NOTHING;

COMMENT ON TABLE system_parameters IS
    'Admin-managed configuration parameters. Values with is_hard_cap=true cannot be exceeded.';
