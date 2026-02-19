-- Migration: 013_add_episode_inactive_grace_hours.sql

BEGIN;

INSERT INTO public.system_parameters (param_key, param_value, description, category) VALUES
('episode_inactive_grace_hours', '{"value": 72}', 'Hours of inactivity before marking an episode extinct', 'clustering')
ON CONFLICT (param_key) DO NOTHING;

COMMIT;
