-- ============================================================================
-- MIGRACIÓN: Sistema de pagos MercadoPago + Créditos
-- Archivo: migrations/2026_02_04_payment_tables.sql
-- Fecha: 2026-02-04
-- ============================================================================

-- 1. Tabla principal de solicitudes de pago
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Estado del pago
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'refunded')),

    -- Proveedor de pago
    provider VARCHAR(20) NOT NULL DEFAULT 'mercadopago'
        CHECK (provider IN ('mercadopago', 'manual', 'promotional')),

    -- Propósito del pago
    purpose VARCHAR(20) NOT NULL
        CHECK (purpose IN ('report', 'credits')),
    target_entity_type VARCHAR(50),
    target_entity_id UUID,

    -- Montos
    amount_usd NUMERIC(10,2) NOT NULL,
    amount_ars NUMERIC(12,2),

    -- Referencias externas MercadoPago
    external_reference VARCHAR(100) UNIQUE NOT NULL,
    provider_payment_id VARCHAR(100),
    provider_preference_id VARCHAR(100),
    checkout_url TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    webhook_received_at TIMESTAMPTZ,

    -- Control y metadata
    retry_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Índices para payment_requests
CREATE INDEX IF NOT EXISTS idx_payment_requests_user_id ON payment_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_requests_status ON payment_requests(status);
CREATE INDEX IF NOT EXISTS idx_payment_requests_external_ref ON payment_requests(external_reference);
CREATE INDEX IF NOT EXISTS idx_payment_requests_created_at ON payment_requests(created_at DESC);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_payment_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_payment_requests_updated_at ON payment_requests;
CREATE TRIGGER trigger_payment_requests_updated_at
    BEFORE UPDATE ON payment_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_requests_updated_at();

-- 2. Logs de webhooks para auditoría
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_request_id UUID REFERENCES payment_requests(id) ON DELETE SET NULL,

    -- Datos del webhook
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    topic VARCHAR(50),
    action VARCHAR(50),
    mp_payment_id VARCHAR(100),

    -- Payload completo para auditoría
    raw_payload JSONB NOT NULL,

    -- Resultado del procesamiento
    processing_result VARCHAR(20)
        CHECK (processing_result IN ('success', 'ignored', 'error', 'duplicate')),
    error_message TEXT,
    processing_time_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_webhook_logs_payment_id ON payment_webhook_logs(payment_request_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_received_at ON payment_webhook_logs(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_mp_payment_id ON payment_webhook_logs(mp_payment_id);

-- 3. Sistema de créditos de usuario
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_credits_user_id ON user_credits(user_id);

-- Trigger para updated_at
DROP TRIGGER IF EXISTS trigger_user_credits_updated_at ON user_credits;
CREATE TRIGGER trigger_user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_requests_updated_at();

-- 4. Historial de transacciones de créditos
-- ============================================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Monto (positivo = entrada, negativo = gasto)
    amount INTEGER NOT NULL,

    -- Tipo de transacción
    type VARCHAR(20) NOT NULL
        CHECK (type IN ('purchase', 'grant', 'spend', 'refund', 'expiration', 'adjustment')),

    -- Referencias
    payment_request_id UUID REFERENCES payment_requests(id) ON DELETE SET NULL,
    related_entity_type VARCHAR(50),
    related_entity_id UUID,

    -- Descripción y metadata
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_payment_id ON credit_transactions(payment_request_id);

-- 5. RLS Policies
-- ============================================================================

-- payment_requests: usuarios solo ven sus propios pagos
ALTER TABLE payment_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY payment_requests_select_own ON payment_requests
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true)::uuid);

CREATE POLICY payment_requests_insert_own ON payment_requests
    FOR INSERT WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid);

-- Admins pueden ver todo
CREATE POLICY payment_requests_admin_all ON payment_requests
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- user_credits: usuarios solo ven su propio saldo
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_credits_select_own ON user_credits
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- credit_transactions: usuarios solo ven sus propias transacciones
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY credit_transactions_select_own ON credit_transactions
    FOR SELECT USING (user_id = current_setting('app.current_user_id', true)::uuid);

-- webhook_logs: solo admins (no usuarios normales)
ALTER TABLE payment_webhook_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhook_logs_admin_only ON payment_webhook_logs
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 6. Función helper para obtener o crear créditos de usuario
-- ============================================================================
CREATE OR REPLACE FUNCTION get_or_create_user_credits(p_user_id UUID)
RETURNS user_credits AS $$
DECLARE
    v_credits user_credits;
BEGIN
    SELECT * INTO v_credits FROM user_credits WHERE user_id = p_user_id;

    IF NOT FOUND THEN
        INSERT INTO user_credits (user_id, balance)
        VALUES (p_user_id, 0)
        RETURNING * INTO v_credits;
    END IF;

    RETURN v_credits;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 7. Función para acreditar créditos (usada por webhook)
-- ============================================================================
CREATE OR REPLACE FUNCTION credit_user_balance(
    p_user_id UUID,
    p_amount INTEGER,
    p_type VARCHAR(20),
    p_payment_request_id UUID DEFAULT NULL,
    p_description TEXT DEFAULT NULL
)
RETURNS credit_transactions AS $$
DECLARE
    v_transaction credit_transactions;
    v_current_balance INTEGER;
BEGIN
    -- Obtener o crear registro de créditos
    PERFORM get_or_create_user_credits(p_user_id);

    -- Actualizar balance
    UPDATE user_credits
    SET balance = balance + p_amount
    WHERE user_id = p_user_id
    RETURNING balance INTO v_current_balance;

    -- Verificar que no quede negativo
    IF v_current_balance < 0 THEN
        RAISE EXCEPTION 'Insufficient credits balance';
    END IF;

    -- Crear transacción
    INSERT INTO credit_transactions (
        user_id, amount, type, payment_request_id, description
    ) VALUES (
        p_user_id, p_amount, p_type, p_payment_request_id, p_description
    ) RETURNING * INTO v_transaction;

    RETURN v_transaction;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- FIN DE MIGRACIÓN
-- ============================================================================
