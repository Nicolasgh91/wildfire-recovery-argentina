-- Users table for ForestGuard authentication
-- Supports both email/password and Google OAuth authentication

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),          -- NULL for Google-only users
    dni VARCHAR(20) UNIQUE,              -- Argentine DNI (Documento Nacional de Identidad)
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    google_id VARCHAR(255) UNIQUE,       -- Google OAuth ID (NULL for email-only users)
    avatar_url VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Ensure at least one auth method exists
    CONSTRAINT users_auth_method_check CHECK (
        password_hash IS NOT NULL OR google_id IS NOT NULL
    )
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_dni ON users(dni) WHERE dni IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at_trigger ON users;
CREATE TRIGGER users_updated_at_trigger
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_updated_at();

-- RLS Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Users can read their own data
CREATE POLICY users_select_own ON users
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true)::uuid);

-- Admins can read all users
CREATE POLICY users_admin_select ON users
    FOR SELECT
    USING (current_setting('app.current_user_role', true) = 'admin');

-- Users can update their own profile (except role)
CREATE POLICY users_update_own ON users
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true)::uuid)
    WITH CHECK (id = current_setting('app.current_user_id', true)::uuid);

-- Only system can insert new users (via service role)
CREATE POLICY users_insert ON users
    FOR INSERT
    WITH CHECK (true);

COMMENT ON TABLE users IS 'User accounts for ForestGuard authentication';
COMMENT ON COLUMN users.dni IS 'Argentine DNI (Documento Nacional de Identidad)';
COMMENT ON COLUMN users.google_id IS 'Google OAuth subject ID for Google Sign-In users';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password, NULL for Google-only accounts';
