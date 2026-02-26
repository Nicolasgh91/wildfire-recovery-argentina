-- =============================================================================
-- Fase 2b: slides_status en fire_episodes (observabilidad carrusel)
-- =============================================================================
-- Valores: pending | processing | ready | failed
-- =============================================================================

ALTER TABLE fire_episodes
  ADD COLUMN IF NOT EXISTS slides_status TEXT DEFAULT 'pending'
  CHECK (slides_status IN ('pending', 'processing', 'ready', 'failed'));

-- Backfill: episodios con al menos un slide con thumbnail_url no vacio -> ready
UPDATE fire_episodes fe
   SET slides_status = 'ready'
 WHERE fe.slides_data IS NOT NULL
   AND jsonb_array_length(fe.slides_data) > 0
   AND EXISTS (
     SELECT 1 FROM jsonb_array_elements(fe.slides_data) AS s
     WHERE (s->>'thumbnail_url') IS NOT NULL
       AND TRIM(COALESCE(s->>'thumbnail_url', '')) != ''
   );
