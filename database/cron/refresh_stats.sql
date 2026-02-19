-- Refresh job for public stats (UC-F02)
-- Runs every 10 minutes with backoff: 5 retries every 10m, then every 60m.
-- Successful refresh schedules the next run for 02:00 UTC next day.

CREATE EXTENSION IF NOT EXISTS pg_cron;

CREATE TABLE IF NOT EXISTS fire_stats_refresh_state (
    id INTEGER PRIMARY KEY,
    fail_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ
);

INSERT INTO fire_stats_refresh_state (id, next_run_at)
VALUES (1, NOW())
ON CONFLICT (id) DO NOTHING;

CREATE OR REPLACE FUNCTION refresh_fire_stats_with_backoff()
RETURNS void AS $$
DECLARE
    v_state fire_stats_refresh_state%ROWTYPE;
    v_now TIMESTAMPTZ := NOW();
    v_next TIMESTAMPTZ;
    v_fail_count INTEGER;
BEGIN
    SELECT * INTO v_state FROM fire_stats_refresh_state WHERE id = 1 FOR UPDATE;
    IF NOT FOUND THEN
        INSERT INTO fire_stats_refresh_state (id, next_run_at)
        VALUES (1, v_now)
        RETURNING * INTO v_state;
    END IF;

    IF v_state.next_run_at IS NOT NULL AND v_state.next_run_at > v_now THEN
        RETURN;
    END IF;

    BEGIN
        REFRESH MATERIALIZED VIEW CONCURRENTLY fire_stats;

        v_next := date_trunc('day', v_now) + INTERVAL '1 day' + INTERVAL '2 hours';
        UPDATE fire_stats_refresh_state
        SET fail_count = 0,
            last_error = NULL,
            last_run_at = v_now,
            next_run_at = v_next
        WHERE id = 1;
    EXCEPTION WHEN OTHERS THEN
        v_fail_count := v_state.fail_count + 1;
        UPDATE fire_stats_refresh_state
        SET fail_count = v_fail_count,
            last_error = SQLERRM,
            last_run_at = v_now,
            next_run_at = v_now + CASE
                WHEN v_fail_count <= 5 THEN INTERVAL '10 minutes'
                ELSE INTERVAL '60 minutes'
            END
        WHERE id = 1;

        IF v_fail_count = 5 THEN
            PERFORM pg_notify(
                'fire_stats_refresh_alert',
                json_build_object(
                    'error', SQLERRM,
                    'failed_at', v_now,
                    'fail_count', v_fail_count
                )::text
            );
        END IF;
    END;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'refresh-fire-stats') THEN
        PERFORM cron.unschedule((SELECT jobid FROM cron.job WHERE jobname = 'refresh-fire-stats'));
    END IF;
END;
$$;

SELECT cron.schedule(
    'refresh-fire-stats',
    '*/10 * * * *',
    $$SELECT refresh_fire_stats_with_backoff();$$
);
