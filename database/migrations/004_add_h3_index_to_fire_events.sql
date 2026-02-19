-- Migration: 004_add_h3_index_to_fire_events.sql

ALTER TABLE fire_events
ADD COLUMN IF NOT EXISTS h3_index BIGINT;

CREATE INDEX IF NOT EXISTS idx_fire_events_h3
    ON fire_events(h3_index);

CREATE INDEX IF NOT EXISTS idx_fire_events_h3_date
    ON fire_events(h3_index, start_date);

COMMENT ON COLUMN fire_events.h3_index IS
    'Indice H3 (resolucion 7-9) para agregacion espacial eficiente.';
