-- =============================================================================
-- ForestGuard — users table
-- Applied by auth-jwt-ci.yml before running integration tests.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    dni         VARCHAR(20),
    full_name   VARCHAR(255) NOT NULL DEFAULT '',
    role        VARCHAR(20)  NOT NULL DEFAULT 'user',
    google_id   VARCHAR(255),
    avatar_url  VARCHAR(500),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_verified BOOLEAN      NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN       NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    deletion_reason VARCHAR(255),

    CONSTRAINT users_role_check CHECK (role IN ('admin', 'user')),
    CONSTRAINT users_auth_method_check CHECK (
        password_hash IS NOT NULL OR google_id IS NOT NULL
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email     ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_dni       ON users(dni)       WHERE dni IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
