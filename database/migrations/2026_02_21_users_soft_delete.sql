-- =============================================================================
-- FORESTGUARD - USERS SOFT DELETE COLUMNS
-- =============================================================================
-- Adds soft-delete support required by account deletion flow.
-- =============================================================================

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS deletion_reason VARCHAR(255) NULL;

CREATE INDEX IF NOT EXISTS idx_users_is_deleted ON public.users(is_deleted);
