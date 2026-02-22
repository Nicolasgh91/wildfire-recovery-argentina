-- Migration: 017_add_storage_and_pdf_parameters.sql
-- Adds storage control, PDF generation, and GEE concurrency parameters.
-- Also adds 'results' JSONB column to hd_generation_jobs for PDF metadata.

-- 1. System parameters for storage limits, PDF, and GEE concurrency
INSERT INTO system_parameters (param_key, param_value, description, category)
VALUES
  ('storage_max_total_gb', '{"value": 8}',
   'Límite de storage total en GB antes de alertar (Oracle Free Tier = 10 GB)', 'limits'),
  ('storage_alert_threshold_gb', '{"value": 7}',
   'Umbral en GB para reducir carousel_batch_size a la mitad', 'limits'),
  ('storage_critical_threshold_gb', '{"value": 9}',
   'Umbral en GB para suspender generación de assets HD', 'limits'),
  ('hd_asset_retention_days', '{"value": 7}',
   'Días de retención de assets HD sin acceso', 'limits'),
  ('pdf_retention_days', '{"value": 90}',
   'Días de retención de PDFs generados', 'limits'),
  ('pdf_max_embedded_images', '{"value": 6}',
   'Máximo de imágenes embebidas en un PDF', 'reports'),
  ('pdf_max_size_mb', '{"value": 20}',
   'Tamaño máximo de un PDF generado en MB', 'reports'),
  ('pdf_image_dpi', '{"value": 150}',
   'DPI de imágenes embebidas en PDF (150 = pantalla, 300 = impresión)', 'reports'),
  ('gee_max_concurrent_requests', '{"value": 20}',
   'Máximo de requests simultáneas a GEE (free tier soporta 40)', 'imagery')
ON CONFLICT (param_key) DO NOTHING;

-- 2. Add results JSONB column to hd_generation_jobs for PDF metadata
ALTER TABLE hd_generation_jobs
  ADD COLUMN IF NOT EXISTS results JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN hd_generation_jobs.results IS
  'Stores PDF generation results: pdf_url, pdf_sha256, pdf_status, pdf_size_bytes, pdf_error';
