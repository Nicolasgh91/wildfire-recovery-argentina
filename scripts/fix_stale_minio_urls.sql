-- =============================================================================
-- fix_stale_minio_urls.sql
-- =============================================================================
-- Limpia URLs de MinIO local (127.0.0.1:9000 / localhost) que quedaron
-- almacenadas en BD tras ejecutar el carrusel con config de desarrollo.
--
-- Efecto: nulifica thumbnail_url / r2_url en satellite_images y vacía
-- slides_data en fire_episodes. El carrusel las regenerará en el próximo ciclo.
--
-- Ejecución:
--   psql "$DATABASE_URL" -f scripts/fix_stale_minio_urls.sql
--
-- Es idempotente y seguro: no elimina filas, solo limpia campos de URL.
-- =============================================================================

BEGIN;

-- ------------------------------------------------------------------
-- 1. Diagnóstico ANTES del fix
-- ------------------------------------------------------------------
SELECT 'satellite_images con URL local (antes)' AS check,
       COUNT(*) AS count
  FROM satellite_images
 WHERE thumbnail_url LIKE 'http://127.0.0.1%'
    OR thumbnail_url LIKE 'http://localhost%'
    OR r2_url        LIKE 'http://127.0.0.1%'
    OR r2_url        LIKE 'http://localhost%';

SELECT 'fire_episodes con slides_data local (antes)' AS check,
       COUNT(*) AS count
  FROM fire_episodes
 WHERE slides_data::text LIKE '%127.0.0.1%'
    OR slides_data::text LIKE '%localhost%';

-- ------------------------------------------------------------------
-- 2. Limpiar satellite_images
--    r2_url es NOT NULL en el schema, usar '' en lugar de NULL.
--    thumbnail_url permite NULL.
-- ------------------------------------------------------------------
UPDATE satellite_images
   SET thumbnail_url = NULL,
       r2_url        = ''
 WHERE thumbnail_url LIKE 'http://127.0.0.1%'
    OR thumbnail_url LIKE 'http://localhost%'
    OR r2_url        LIKE 'http://127.0.0.1%'
    OR r2_url        LIKE 'http://localhost%';

-- ------------------------------------------------------------------
-- 3. Limpiar fire_episodes.slides_data
--    También resetear last_gee_image_id para forzar regeneración GEE.
-- ------------------------------------------------------------------
UPDATE fire_episodes
   SET slides_data        = '[]'::jsonb,
       last_gee_image_id  = NULL
 WHERE slides_data::text LIKE '%127.0.0.1%'
    OR slides_data::text LIKE '%localhost%';

-- ------------------------------------------------------------------
-- 4. Diagnóstico DESPUÉS del fix (ambas tablas deben mostrar 0)
-- ------------------------------------------------------------------
SELECT 'satellite_images con URL local (después)' AS check,
       COUNT(*) AS count
  FROM satellite_images
 WHERE thumbnail_url LIKE 'http://127.0.0.1%'
    OR thumbnail_url LIKE 'http://localhost%';

SELECT 'fire_episodes con slides_data local (después)' AS check,
       COUNT(*) AS count
  FROM fire_episodes
 WHERE slides_data::text LIKE '%127.0.0.1%'
    OR slides_data::text LIKE '%localhost%';

-- ------------------------------------------------------------------
-- 5. Resumen: cuántos episodios quedan sin slides_data (necesitan refresh)
-- ------------------------------------------------------------------
SELECT 'fire_episodes sin slides (necesitan carousel refresh)' AS check,
       COUNT(*) AS count
  FROM fire_episodes
 WHERE slides_data IS NULL
    OR slides_data = '[]'::jsonb;

COMMIT;

-- =============================================================================
-- POST-DEPLOY: Trigger manual del carrusel para regenerar thumbnails con OCI
-- =============================================================================
-- Ejecutar desde el servidor tras el rebuild:
--
--   docker compose exec api python -c "
--   from app.db.session import SessionLocal
--   from app.services.imagery_service import ImageryService
--   db = SessionLocal()
--   svc = ImageryService(db)
--   result = svc.run_carousel(max_fires=20, force_refresh=True)
--   print(result)
--   db.close()
--   "
-- =============================================================================
