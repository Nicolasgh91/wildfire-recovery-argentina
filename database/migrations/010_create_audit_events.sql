-- Migration: 010_create_audit_events.sql

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id VARCHAR(255),
    principal_role VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS audit_events_action_idx
    ON audit_events(action);

CREATE INDEX IF NOT EXISTS audit_events_resource_idx
    ON audit_events(resource_type, resource_id);

CREATE INDEX IF NOT EXISTS audit_events_created_at_idx
    ON audit_events(created_at);

COMMENT ON TABLE audit_events IS
    'Append-only system audit log for critical actions and evidence chain-of-custody.';
