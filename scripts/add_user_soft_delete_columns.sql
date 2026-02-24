-- Migration: Add soft-delete columns to users table
-- Required by User model (app/models/user.py)
-- These columns were added to the model but never migrated in production.
-- Without them, ALL authenticated requests crash with:
--   ProgrammingError: column users.is_deleted does not exist

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_reason VARCHAR(255);
