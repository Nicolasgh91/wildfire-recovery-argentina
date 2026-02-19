-- Migration: 016_add_hd_generation_job_idempotency.sql

BEGIN;

ALTER TABLE hd_generation_jobs
    ADD COLUMN IF NOT EXISTS idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_hd_generation_jobs_idempotency
    ON hd_generation_jobs (investigation_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

COMMIT;
