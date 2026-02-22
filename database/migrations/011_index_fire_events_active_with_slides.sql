-- Index parcial para optimizar Home (incendios activos con thumbnails)

CREATE INDEX IF NOT EXISTS idx_fire_events_active_with_slides
ON fire_events (start_date DESC)
WHERE slides_data IS NOT NULL
  AND jsonb_array_length(slides_data) > 0;
