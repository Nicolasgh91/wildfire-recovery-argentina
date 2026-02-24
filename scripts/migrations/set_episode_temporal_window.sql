-- Corrige la ventana temporal de episodios de 4 días (96h) a 30 días (720h)
-- Esto permite que episodios en monitoring no se extingan prematuramente
INSERT INTO system_parameters (param_key, param_value, description, category)
VALUES (
    'episode_temporal_window_hours',
    '720'::jsonb,
    'Ventana temporal para declarar episodio extinto (en horas). 720h = 30 días.',
    'clustering'
)
ON CONFLICT (param_key) DO UPDATE
SET param_value = EXCLUDED.param_value,
    description = EXCLUDED.description,
    updated_at = NOW();
