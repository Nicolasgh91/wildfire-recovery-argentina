# Tareas técnicas - Integración MercadoPago Checkout Pro

**Proyecto**: ForestGuard  
**Fase**: 3.4  
**Estimación**: 2 días  
**Prioridad**: Alta (habilita monetización)


┌─────────────────────────────────────────────────────────────────────────────┐
│                    TAREAS TÉCNICAS - MERCADOPAGO                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  BACKEND (12h)                        FRONTEND (7h)                         │
│  ════════════                         ═════════════                         │
│                                                                             │
│  BE-PAY-01: Migración SQL (1h)        FE-PAY-01: Hooks (2h)                 │
│  - 4 tablas                           - useCreateCheckout                   │
│  - RLS policies                       - usePaymentStatus                    │
│  - Funciones helper                   - useCreditBalance                    │
│                                                                             │
│  BE-PAY-02: MP Service (3h)           FE-PAY-02: PaymentButton (1h)         │
│  - SDK singleton                                                            │
│  - Validación firma webhook           FE-PAY-03: StatusPoller (1h)          │
│                                                                             │
│  BE-PAY-03: POST /checkout (2h)       FE-PAY-04: Credits UI (2h)            │
│                                       - Balance widget                      │
│  BE-PAY-04: POST /webhook (3h)        - Purchase modal                      │
│  - Idempotencia                                                             │
│  - Acreditación créditos              FE-PAY-05: Return page (1h)           │
│                                       - Polling con timeout                 │
│  BE-PAY-05/06: GET endpoints (3h)                                           │
│                                                                             │
│  TOTAL: 19h (~2 días)                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘



---

## Índice de tareas

| ID | Tarea | Tipo | Estimación |
|----|-------|------|------------|
| BE-PAY-01 | Migración SQL de tablas de pagos | Backend/DB | 1h |
| BE-PAY-02 | Servicio de MercadoPago | Backend | 3h |
| BE-PAY-03 | Endpoint POST /payments/checkout | Backend | 2h |
| BE-PAY-04 | Endpoint POST /webhooks/mercadopago | Backend | 3h |
| BE-PAY-05 | Endpoint GET /payments/{id} | Backend | 1h |
| BE-PAY-06 | Endpoints de créditos | Backend | 2h |
| FE-PAY-01 | Hooks de pagos y créditos | Frontend | 2h |
| FE-PAY-02 | Componente PaymentButton | Frontend | 1h |
| FE-PAY-03 | Componente PaymentStatusPoller | Frontend | 1h |
| FE-PAY-04 | Componentes de créditos | Frontend | 2h |
| FE-PAY-05 | Página de retorno de pago | Frontend | 1h |
| TEST-PAY-01 | Tests unitarios y E2E | Testing | 2h |

---

## BE-PAY-01: Migración SQL de tablas de pagos

### Objetivo
Crear las tablas necesarias para el sistema de pagos y créditos.

### Input requerido
- Acceso a base de datos PostgreSQL/Supabase
- Permisos de DDL

### Proceso paso a paso

1. Crear archivo de migración `migrations/003_payment_tables.sql`
2. Ejecutar migración en orden
3. Verificar índices creados
4. Configurar RLS policies

### Output esperado
- Tabla `payment_requests` creada
- Tabla `payment_webhook_logs` creada
- Tabla `user_credits` creada
- Tabla `credit_transactions` creada
- Índices optimizados
- RLS policies configuradas

### Código SQL completo

```sql
-- ============================================================================
-- MIGRACIÓN: Sistema de pagos MercadoPago + Créditos
-- Archivo: migrations/003_payment_tables.sql
-- Fecha: 2026-02-03
-- ============================================================================

-- 1. Tabla principal de solicitudes de pago
-- ============================================================================
CREATE TABLE IF NOT EXISTS payment_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
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
CREATE INDEX idx_payment_requests_user_id ON payment_requests(user_id);
CREATE INDEX idx_payment_requests_status ON payment_requests(status);
CREATE INDEX idx_payment_requests_external_ref ON payment_requests(external_reference);
CREATE INDEX idx_payment_requests_created_at ON payment_requests(created_at DESC);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_payment_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

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

CREATE INDEX idx_webhook_logs_payment_id ON payment_webhook_logs(payment_request_id);
CREATE INDEX idx_webhook_logs_received_at ON payment_webhook_logs(received_at DESC);
CREATE INDEX idx_webhook_logs_mp_payment_id ON payment_webhook_logs(mp_payment_id);

-- 3. Sistema de créditos de usuario
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_credits_user_id ON user_credits(user_id);

-- Trigger para updated_at
CREATE TRIGGER trigger_user_credits_updated_at
    BEFORE UPDATE ON user_credits
    FOR EACH ROW
    EXECUTE FUNCTION update_payment_requests_updated_at();

-- 4. Historial de transacciones de créditos
-- ============================================================================
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
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

CREATE INDEX idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX idx_credit_transactions_created_at ON credit_transactions(created_at DESC);
CREATE INDEX idx_credit_transactions_payment_id ON credit_transactions(payment_request_id);

-- 5. RLS Policies
-- ============================================================================

-- payment_requests: usuarios solo ven sus propios pagos
ALTER TABLE payment_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY payment_requests_select_own ON payment_requests
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY payment_requests_insert_own ON payment_requests
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Admins pueden ver todo
CREATE POLICY payment_requests_admin_all ON payment_requests
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' = 'admin'
        )
    );

-- user_credits: usuarios solo ven su propio saldo
ALTER TABLE user_credits ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_credits_select_own ON user_credits
    FOR SELECT USING (auth.uid() = user_id);

-- credit_transactions: usuarios solo ven sus propias transacciones
ALTER TABLE credit_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY credit_transactions_select_own ON credit_transactions
    FOR SELECT USING (auth.uid() = user_id);

-- webhook_logs: solo admins (no usuarios normales)
ALTER TABLE payment_webhook_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY webhook_logs_admin_only ON payment_webhook_logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' = 'admin'
        )
    );

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
```

### Tests de verificación

```sql
-- Verificar tablas creadas
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('payment_requests', 'payment_webhook_logs', 'user_credits', 'credit_transactions');

-- Verificar índices
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('payment_requests', 'payment_webhook_logs', 'user_credits', 'credit_transactions');

-- Verificar RLS habilitado
SELECT tablename, rowsecurity FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('payment_requests', 'payment_webhook_logs', 'user_credits', 'credit_transactions');
```

---

## BE-PAY-02: Servicio de MercadoPago

### Objetivo
Crear servicio que encapsula la comunicación con la API de MercadoPago.

### Input requerido
- Variable de entorno: `MP_ACCESS_TOKEN`
- Variable de entorno: `MP_WEBHOOK_SECRET` (opcional, para validación)
- Dependencia: `mercadopago` (pip)

### Proceso paso a paso

1. Crear archivo `app/services/mercadopago_service.py`
2. Implementar cliente singleton
3. Implementar métodos de preferencia y consulta
4. Implementar validación de webhook

### Output esperado
- Archivo `app/services/mercadopago_service.py`
- Clase `MercadoPagoService` funcional
- Métodos documentados

### Código Python

```python
"""
Servicio de integración con MercadoPago Checkout Pro.

Este módulo encapsula toda la comunicación con la API de MercadoPago,
incluyendo creación de preferencias de pago y consulta de estados.

@requires MP_ACCESS_TOKEN - Token de acceso de MercadoPago
@requires MP_WEBHOOK_SECRET - (Opcional) Secret para validar webhooks
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

import mercadopago
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class PreferenceItem(BaseModel):
    """Item a incluir en la preferencia de pago."""
    title: str
    quantity: int = 1
    unit_price: Decimal
    currency_id: str = "ARS"
    description: Optional[str] = None


class PreferenceResponse(BaseModel):
    """Respuesta de creación de preferencia."""
    preference_id: str
    init_point: str  # URL de checkout
    sandbox_init_point: str  # URL de checkout en sandbox


class PaymentInfo(BaseModel):
    """Información de un pago consultado."""
    id: str
    status: str  # approved, pending, rejected, etc.
    status_detail: str
    transaction_amount: Decimal
    currency_id: str
    external_reference: Optional[str]
    date_approved: Optional[datetime]
    payer_email: Optional[str]


class MercadoPagoService:
    """
    Servicio singleton para interactuar con MercadoPago.
    
    Encapsula la creación de preferencias de pago y la consulta
    de estados de pagos. No maneja webhooks directamente (eso
    lo hace el endpoint correspondiente).
    
    Ejemplo de uso:
        mp_service = MercadoPagoService()
        preference = await mp_service.create_preference(
            external_reference="pay_123",
            items=[PreferenceItem(title="Reporte HD", unit_price=6.00)],
            payer_email="user@example.com"
        )
    """
    
    _instance: Optional["MercadoPagoService"] = None
    
    def __new__(cls) -> "MercadoPagoService":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa el SDK de MercadoPago."""
        if self._initialized:
            return
            
        self._sdk = mercadopago.SDK(settings.MP_ACCESS_TOKEN)
        self._webhook_secret = getattr(settings, "MP_WEBHOOK_SECRET", None)
        self._initialized = True
        
        logger.info("MercadoPago service initialized")
    
    async def create_preference(
        self,
        external_reference: str,
        items: list[PreferenceItem],
        payer_email: Optional[str] = None,
        notification_url: Optional[str] = None,
        back_urls: Optional[dict] = None,
        expires_in_hours: int = 24,
        metadata: Optional[dict] = None
    ) -> PreferenceResponse:
        """
        Crea una preferencia de pago en MercadoPago.
        
        Args:
            external_reference: ID único para reconciliación (UUID del payment_request)
            items: Lista de items a cobrar
            payer_email: Email del pagador (opcional pero recomendado)
            notification_url: URL del webhook para notificaciones
            back_urls: URLs de retorno (success, failure, pending)
            expires_in_hours: Horas hasta expiración de la preferencia
            metadata: Datos adicionales a guardar
            
        Returns:
            PreferenceResponse con URLs de checkout
            
        Raises:
            MercadoPagoError: Si falla la creación
        """
        # Construir items para MP
        mp_items = [
            {
                "title": item.title,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "currency_id": item.currency_id,
                "description": item.description or item.title
            }
            for item in items
        ]
        
        # Construir preferencia
        preference_data = {
            "items": mp_items,
            "external_reference": external_reference,
            "expires": True,
            "expiration_date_from": datetime.utcnow().isoformat() + "Z",
            "expiration_date_to": (
                datetime.utcnow() + timedelta(hours=expires_in_hours)
            ).isoformat() + "Z",
        }
        
        # Agregar payer si está disponible
        if payer_email:
            preference_data["payer"] = {"email": payer_email}
        
        # Agregar notification_url si está disponible
        if notification_url:
            preference_data["notification_url"] = notification_url
        
        # Agregar back_urls si están disponibles
        if back_urls:
            preference_data["back_urls"] = back_urls
            preference_data["auto_return"] = "approved"
        
        # Agregar metadata si está disponible
        if metadata:
            preference_data["metadata"] = metadata
        
        logger.info(f"Creating preference for external_reference: {external_reference}")
        
        # Llamar a MP API
        result = self._sdk.preference().create(preference_data)
        
        if result["status"] != 201:
            logger.error(f"MercadoPago error: {result}")
            raise MercadoPagoError(
                f"Failed to create preference: {result.get('response', {}).get('message', 'Unknown error')}"
            )
        
        response_data = result["response"]
        
        logger.info(f"Preference created: {response_data['id']}")
        
        return PreferenceResponse(
            preference_id=response_data["id"],
            init_point=response_data["init_point"],
            sandbox_init_point=response_data["sandbox_init_point"]
        )
    
    async def get_payment(self, payment_id: str) -> PaymentInfo:
        """
        Consulta el estado de un pago por su ID de MercadoPago.
        
        Args:
            payment_id: ID del pago en MercadoPago
            
        Returns:
            PaymentInfo con el estado actual
            
        Raises:
            MercadoPagoError: Si falla la consulta
        """
        logger.info(f"Getting payment info: {payment_id}")
        
        result = self._sdk.payment().get(payment_id)
        
        if result["status"] != 200:
            logger.error(f"MercadoPago error getting payment: {result}")
            raise MercadoPagoError(
                f"Failed to get payment: {result.get('response', {}).get('message', 'Unknown error')}"
            )
        
        data = result["response"]
        
        return PaymentInfo(
            id=str(data["id"]),
            status=data["status"],
            status_detail=data.get("status_detail", ""),
            transaction_amount=Decimal(str(data["transaction_amount"])),
            currency_id=data["currency_id"],
            external_reference=data.get("external_reference"),
            date_approved=data.get("date_approved"),
            payer_email=data.get("payer", {}).get("email")
        )
    
    def validate_webhook_signature(
        self,
        x_signature: str,
        x_request_id: str,
        data_id: str
    ) -> bool:
        """
        Valida la firma de un webhook de MercadoPago.
        
        Args:
            x_signature: Header x-signature del request
            x_request_id: Header x-request-id del request
            data_id: ID del dato en el body (data.id)
            
        Returns:
            True si la firma es válida
            
        Note:
            Si MP_WEBHOOK_SECRET no está configurado, retorna True
            (para desarrollo). En producción SIEMPRE configurar el secret.
        """
        if not self._webhook_secret:
            logger.warning("Webhook signature validation skipped: no secret configured")
            return True
        
        # Parsear x-signature
        # Formato: ts=xxx,v1=xxx
        parts = dict(p.split("=") for p in x_signature.split(","))
        ts = parts.get("ts")
        v1 = parts.get("v1")
        
        if not ts or not v1:
            logger.warning("Invalid x-signature format")
            return False
        
        # Construir manifest
        manifest = f"id:{data_id};request-id:{x_request_id};ts:{ts};"
        
        # Calcular HMAC
        expected = hmac.new(
            self._webhook_secret.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(expected, v1)
        
        if not is_valid:
            logger.warning("Webhook signature validation failed")
        
        return is_valid


class MercadoPagoError(Exception):
    """Error de comunicación con MercadoPago."""
    pass


# Instancia global (singleton)
mp_service = MercadoPagoService()
```

### Configuración requerida en settings

```python
# app/core/config.py (agregar)

class Settings(BaseSettings):
    # ... existentes ...
    
    # MercadoPago
    MP_ACCESS_TOKEN: str
    MP_WEBHOOK_SECRET: Optional[str] = None
    MP_NOTIFICATION_URL: Optional[str] = None  # URL del webhook
    
    # URLs de retorno
    PAYMENT_SUCCESS_URL: str = "https://forestguard.ar/payments/return?status=success"
    PAYMENT_FAILURE_URL: str = "https://forestguard.ar/payments/return?status=failure"
    PAYMENT_PENDING_URL: str = "https://forestguard.ar/payments/return?status=pending"
```

### Tests unitarios

```python
# tests/unit/test_mercadopago_service.py

import pytest
from unittest.mock import MagicMock, patch
from decimal import Decimal

from app.services.mercadopago_service import (
    MercadoPagoService,
    PreferenceItem,
    MercadoPagoError
)


class TestMercadoPagoService:
    """Tests para MercadoPagoService."""
    
    @pytest.fixture
    def mp_service(self):
        """Fixture que retorna una instancia del servicio."""
        with patch.object(MercadoPagoService, '_instance', None):
            service = MercadoPagoService()
            service._sdk = MagicMock()
            return service
    
    @pytest.mark.asyncio
    async def test_create_preference_success(self, mp_service):
        """Debe crear preferencia exitosamente."""
        mp_service._sdk.preference().create.return_value = {
            "status": 201,
            "response": {
                "id": "pref_123",
                "init_point": "https://mp.com/checkout/123",
                "sandbox_init_point": "https://sandbox.mp.com/checkout/123"
            }
        }
        
        result = await mp_service.create_preference(
            external_reference="pay_abc",
            items=[PreferenceItem(title="Test", unit_price=Decimal("10.00"))]
        )
        
        assert result.preference_id == "pref_123"
        assert "checkout" in result.init_point
    
    @pytest.mark.asyncio
    async def test_create_preference_failure(self, mp_service):
        """Debe lanzar error si MP falla."""
        mp_service._sdk.preference().create.return_value = {
            "status": 400,
            "response": {"message": "Invalid data"}
        }
        
        with pytest.raises(MercadoPagoError):
            await mp_service.create_preference(
                external_reference="pay_abc",
                items=[PreferenceItem(title="Test", unit_price=Decimal("10.00"))]
            )
    
    @pytest.mark.asyncio
    async def test_get_payment_success(self, mp_service):
        """Debe obtener información del pago."""
        mp_service._sdk.payment().get.return_value = {
            "status": 200,
            "response": {
                "id": 12345,
                "status": "approved",
                "status_detail": "accredited",
                "transaction_amount": 100.00,
                "currency_id": "ARS",
                "external_reference": "pay_abc"
            }
        }
        
        result = await mp_service.get_payment("12345")
        
        assert result.status == "approved"
        assert result.external_reference == "pay_abc"
    
    def test_validate_webhook_signature_no_secret(self, mp_service):
        """Sin secret configurado, debe retornar True (dev mode)."""
        mp_service._webhook_secret = None
        
        result = mp_service.validate_webhook_signature(
            x_signature="ts=123,v1=abc",
            x_request_id="req_123",
            data_id="data_123"
        )
        
        assert result is True
```

---

## BE-PAY-03: Endpoint POST /payments/checkout

### Objetivo
Crear endpoint que inicia el proceso de pago creando una preferencia en MercadoPago.

### Input requerido
- MercadoPagoService (BE-PAY-02)
- Tablas de pagos (BE-PAY-01)
- Usuario autenticado

### Proceso paso a paso

1. Crear archivo `app/api/v1/payments.py`
2. Implementar schema de request/response
3. Implementar lógica de creación
4. Registrar router

### Output esperado
- Endpoint `POST /api/v1/payments/checkout` funcional
- Schemas Pydantic definidos

### Código Python

```python
"""
Endpoints de pagos con MercadoPago.

Este módulo maneja la creación de checkouts y consulta de estados
de pago. El procesamiento real ocurre en el webhook.

@requires Autenticación JWT para todos los endpoints
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.models.payment import PaymentRequest  # Modelo SQLAlchemy
from app.services.mercadopago_service import (
    mp_service,
    PreferenceItem,
    MercadoPagoError
)

router = APIRouter(prefix="/payments", tags=["payments"])


# =============================================================================
# SCHEMAS
# =============================================================================

class CreateCheckoutRequest(BaseModel):
    """Request para crear un checkout."""
    purpose: str = Field(..., pattern="^(report|credits)$")
    target_entity_type: Optional[str] = None
    target_entity_id: Optional[UUID] = None
    credits_amount: Optional[int] = Field(None, ge=1, le=100)
    metadata: Optional[dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "purpose": "credits",
                "credits_amount": 12
            }
        }


class CreateCheckoutResponse(BaseModel):
    """Response de creación de checkout."""
    payment_request_id: UUID
    checkout_url: str
    external_reference: str
    amount_usd: Decimal
    expires_at: datetime


class PaymentStatusResponse(BaseModel):
    """Response de estado de pago."""
    id: UUID
    status: str
    purpose: str
    amount_usd: Decimal
    created_at: datetime
    approved_at: Optional[datetime] = None


# =============================================================================
# PRECIOS
# =============================================================================

CREDIT_PRICE_USD = Decimal("0.50")  # Precio por crédito

CREDIT_PACKAGES = {
    5: Decimal("2.50"),    # $0.50 c/u
    12: Decimal("5.00"),   # $0.42 c/u (descuento)
    25: Decimal("10.00"),  # $0.40 c/u (mayor descuento)
}


def calculate_price(purpose: str, credits_amount: Optional[int]) -> Decimal:
    """
    Calcula el precio en USD según el propósito.
    
    Args:
        purpose: 'report' o 'credits'
        credits_amount: Cantidad de créditos (si purpose='credits')
        
    Returns:
        Precio en USD
    """
    if purpose == "credits":
        if credits_amount in CREDIT_PACKAGES:
            return CREDIT_PACKAGES[credits_amount]
        return CREDIT_PRICE_USD * credits_amount
    
    # Para reportes, el precio es fijo (12 imágenes)
    return Decimal("6.00")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    request: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Crea una preferencia de pago en MercadoPago.
    
    Flujo:
    1. Valida el request
    2. Calcula el precio
    3. Crea registro en payment_requests (pending)
    4. Crea preferencia en MercadoPago
    5. Retorna URL de checkout
    
    El usuario debe ser redirigido a checkout_url para completar el pago.
    El pago NO se confirma hasta que llegue el webhook.
    """
    # Validar request
    if request.purpose == "credits" and not request.credits_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="credits_amount is required when purpose is 'credits'"
        )
    
    if request.purpose == "report" and not request.target_entity_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_entity_id is required when purpose is 'report'"
        )
    
    # Calcular precio
    amount_usd = calculate_price(request.purpose, request.credits_amount)
    
    # Generar external_reference único
    external_reference = f"fg_{uuid4().hex[:16]}"
    
    # Calcular expiración
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Crear registro en BD
    payment_request = PaymentRequest(
        user_id=current_user.id,
        status="pending",
        provider="mercadopago",
        purpose=request.purpose,
        target_entity_type=request.target_entity_type,
        target_entity_id=request.target_entity_id,
        amount_usd=amount_usd,
        external_reference=external_reference,
        expires_at=expires_at,
        metadata={
            "credits_amount": request.credits_amount,
            **(request.metadata or {})
        }
    )
    
    db.add(payment_request)
    await db.flush()  # Para obtener el ID
    
    # Preparar items para MercadoPago
    if request.purpose == "credits":
        title = f"ForestGuard - {request.credits_amount} créditos"
        description = f"Paquete de {request.credits_amount} créditos para reportes HD"
    else:
        title = "ForestGuard - Reporte HD"
        description = "Generación de reporte con imágenes satelitales HD"
    
    items = [
        PreferenceItem(
            title=title,
            description=description,
            unit_price=amount_usd,
            quantity=1,
            currency_id="ARS"  # MP convierte automáticamente
        )
    ]
    
    # Crear preferencia en MercadoPago
    try:
        preference = await mp_service.create_preference(
            external_reference=external_reference,
            items=items,
            payer_email=current_user.email,
            notification_url=settings.MP_NOTIFICATION_URL,
            back_urls={
                "success": f"{settings.PAYMENT_SUCCESS_URL}&payment_request_id={payment_request.id}",
                "failure": f"{settings.PAYMENT_FAILURE_URL}&payment_request_id={payment_request.id}",
                "pending": f"{settings.PAYMENT_PENDING_URL}&payment_request_id={payment_request.id}"
            },
            expires_in_hours=24,
            metadata={
                "user_id": str(current_user.id),
                "purpose": request.purpose,
                "payment_request_id": str(payment_request.id)
            }
        )
    except MercadoPagoError as e:
        # Rollback implícito al salir del context
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error creating payment preference: {str(e)}"
        )
    
    # Actualizar registro con datos de MP
    payment_request.provider_preference_id = preference.preference_id
    payment_request.checkout_url = preference.init_point
    
    await db.commit()
    
    return CreateCheckoutResponse(
        payment_request_id=payment_request.id,
        checkout_url=preference.init_point,
        external_reference=external_reference,
        amount_usd=amount_usd,
        expires_at=expires_at
    )


@router.get("/{payment_request_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    payment_request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el estado actual de un pago.
    
    Usado por el frontend para polling después de que el usuario
    retorna de MercadoPago.
    """
    result = await db.execute(
        select(PaymentRequest).where(
            PaymentRequest.id == payment_request_id,
            PaymentRequest.user_id == current_user.id
        )
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment request not found"
        )
    
    return PaymentStatusResponse(
        id=payment.id,
        status=payment.status,
        purpose=payment.purpose,
        amount_usd=payment.amount_usd,
        created_at=payment.created_at,
        approved_at=payment.approved_at
    )
```

---

## BE-PAY-04: Endpoint POST /webhooks/mercadopago

### Objetivo
Procesar notificaciones de MercadoPago y actualizar estados de pago.

### Input requerido
- MercadoPagoService (BE-PAY-02)
- Tablas de pagos (BE-PAY-01)
- Función `credit_user_balance` de SQL

### Proceso paso a paso

1. Crear archivo `app/api/v1/webhooks.py`
2. Implementar validación de firma
3. Implementar lógica idempotente
4. Implementar acreditación de créditos

### Código Python

```python
"""
Webhook de MercadoPago.

Este endpoint recibe notificaciones de pagos y actualiza el estado
en la base de datos. Es idempotente y seguro.

@security No requiere autenticación JWT (validación por firma MP)
@idempotent Múltiples llamadas con mismo pago no duplican efectos
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.payment import PaymentRequest, PaymentWebhookLog
from app.services.mercadopago_service import mp_service, MercadoPagoError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class MPWebhookPayload(BaseModel):
    """Payload del webhook de MercadoPago."""
    action: str
    api_version: str
    data: dict  # {"id": "payment_id"}
    date_created: str
    id: str
    live_mode: bool
    type: str
    user_id: Optional[str] = None


@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    payload: MPWebhookPayload,
    db: AsyncSession = Depends(get_db),
    x_signature: Optional[str] = Header(None),
    x_request_id: Optional[str] = Header(None)
):
    """
    Recibe notificaciones de MercadoPago.
    
    Flujo:
    1. Valida firma (si está configurado el secret)
    2. Registra el webhook en logs
    3. Si es notificación de pago, consulta estado real
    4. Si el pago está aprobado y no fue procesado antes:
       - Actualiza payment_request a 'approved'
       - Acredita créditos al usuario
    5. Retorna 200 OK (siempre, para evitar reintentos innecesarios)
    
    @idempotent Múltiples llamadas no duplican créditos
    """
    start_time = datetime.utcnow()
    data_id = payload.data.get("id", "")
    
    # 1. Validar firma (opcional pero recomendado en producción)
    if x_signature and x_request_id:
        is_valid = mp_service.validate_webhook_signature(
            x_signature=x_signature,
            x_request_id=x_request_id,
            data_id=data_id
        )
        if not is_valid:
            logger.warning(f"Invalid webhook signature for {data_id}")
            # Retornamos 200 igual para no recibir más reintentos
            return {"status": "signature_invalid"}
    
    # 2. Crear log del webhook
    webhook_log = PaymentWebhookLog(
        topic=payload.type,
        action=payload.action,
        mp_payment_id=data_id,
        raw_payload=payload.model_dump()
    )
    db.add(webhook_log)
    
    # 3. Solo procesamos notificaciones de pago
    if payload.type != "payment":
        webhook_log.processing_result = "ignored"
        await db.commit()
        return {"status": "ignored", "reason": "not a payment notification"}
    
    # 4. Consultar estado real del pago en MP
    try:
        payment_info = await mp_service.get_payment(data_id)
    except MercadoPagoError as e:
        logger.error(f"Error getting payment {data_id}: {e}")
        webhook_log.processing_result = "error"
        webhook_log.error_message = str(e)
        await db.commit()
        return {"status": "error", "message": str(e)}
    
    # 5. Buscar payment_request por external_reference
    if not payment_info.external_reference:
        logger.warning(f"Payment {data_id} has no external_reference")
        webhook_log.processing_result = "error"
        webhook_log.error_message = "No external_reference"
        await db.commit()
        return {"status": "error", "message": "no external_reference"}
    
    result = await db.execute(
        select(PaymentRequest).where(
            PaymentRequest.external_reference == payment_info.external_reference
        )
    )
    payment_request = result.scalar_one_or_none()
    
    if not payment_request:
        logger.warning(f"Payment request not found: {payment_info.external_reference}")
        webhook_log.processing_result = "error"
        webhook_log.error_message = "Payment request not found"
        await db.commit()
        return {"status": "error", "message": "payment_request not found"}
    
    # Vincular log con payment_request
    webhook_log.payment_request_id = payment_request.id
    
    # 6. Verificar idempotencia
    if payment_request.status == "approved":
        logger.info(f"Payment {payment_request.id} already approved, ignoring")
        webhook_log.processing_result = "duplicate"
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        webhook_log.processing_time_ms = int(processing_time)
        await db.commit()
        return {"status": "duplicate", "message": "already processed"}
    
    # 7. Procesar según estado del pago
    if payment_info.status == "approved":
        # Actualizar payment_request
        payment_request.status = "approved"
        payment_request.provider_payment_id = payment_info.id
        payment_request.approved_at = datetime.utcnow()
        payment_request.webhook_received_at = datetime.utcnow()
        payment_request.amount_ars = payment_info.transaction_amount
        
        # Acreditar créditos
        credits_amount = payment_request.metadata.get("credits_amount", 0)
        if payment_request.purpose == "credits" and credits_amount > 0:
            # Usar función SQL para acreditar
            await db.execute(
                text("""
                    SELECT credit_user_balance(
                        :user_id,
                        :amount,
                        'purchase',
                        :payment_request_id,
                        :description
                    )
                """),
                {
                    "user_id": str(payment_request.user_id),
                    "amount": credits_amount,
                    "payment_request_id": str(payment_request.id),
                    "description": f"Compra de {credits_amount} créditos"
                }
            )
            logger.info(f"Credited {credits_amount} credits to user {payment_request.user_id}")
        
        elif payment_request.purpose == "report":
            # TODO: Disparar generación de reporte
            # Esto podría ser una tarea de Celery
            logger.info(f"Report generation triggered for {payment_request.target_entity_id}")
        
        webhook_log.processing_result = "success"
        logger.info(f"Payment {payment_request.id} approved successfully")
    
    elif payment_info.status in ("rejected", "cancelled"):
        payment_request.status = "rejected"
        payment_request.webhook_received_at = datetime.utcnow()
        webhook_log.processing_result = "success"
        logger.info(f"Payment {payment_request.id} rejected/cancelled")
    
    else:
        # pending, in_process, etc.
        webhook_log.processing_result = "ignored"
        logger.info(f"Payment {payment_request.id} status: {payment_info.status}")
    
    processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    webhook_log.processing_time_ms = int(processing_time)
    
    await db.commit()
    
    return {"status": "ok"}
```

---

## BE-PAY-05 y BE-PAY-06: Endpoints de créditos

### Código Python (agregar a payments.py)

```python
# Agregar al router de payments.py

@router.get("/credits/balance")
async def get_credit_balance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el saldo de créditos del usuario actual."""
    result = await db.execute(
        text("SELECT * FROM get_or_create_user_credits(:user_id)"),
        {"user_id": str(current_user.id)}
    )
    row = result.fetchone()
    
    return {
        "balance": row.balance if row else 0,
        "last_updated": row.updated_at.isoformat() if row else datetime.utcnow().isoformat()
    }


@router.get("/credits/transactions")
async def get_credit_transactions(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el historial de transacciones de créditos."""
    from app.models.payment import CreditTransaction
    
    offset = (page - 1) * page_size
    
    # Contar total
    count_result = await db.execute(
        select(func.count()).where(CreditTransaction.user_id == current_user.id)
    )
    total = count_result.scalar()
    
    # Obtener transacciones
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    transactions = result.scalars().all()
    
    return {
        "transactions": [
            {
                "id": str(t.id),
                "amount": t.amount,
                "type": t.type,
                "description": t.description,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

---

## FE-PAY-01 a FE-PAY-05: Componentes Frontend

### Archivo: src/hooks/mutations/useCreateCheckout.ts

```typescript
/**
 * Hook para crear un checkout de MercadoPago.
 * 
 * @example
 * const { mutate: createCheckout, isPending } = useCreateCheckout();
 * createCheckout({ purpose: 'credits', credits_amount: 12 });
 */

import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

interface CreateCheckoutRequest {
  purpose: 'report' | 'credits';
  target_entity_type?: string;
  target_entity_id?: string;
  credits_amount?: number;
  metadata?: Record<string, unknown>;
}

interface CreateCheckoutResponse {
  payment_request_id: string;
  checkout_url: string;
  external_reference: string;
  amount_usd: number;
  expires_at: string;
}

export function useCreateCheckout() {
  return useMutation<CreateCheckoutResponse, Error, CreateCheckoutRequest>({
    mutationFn: async (data) => {
      const response = await apiClient.post<CreateCheckoutResponse>(
        '/payments/checkout',
        data
      );
      return response.data;
    },
    onSuccess: (data) => {
      // Redirigir a MercadoPago
      window.location.href = data.checkout_url;
    },
  });
}
```

### Archivo: src/hooks/queries/usePaymentStatus.ts

```typescript
/**
 * Hook para polling del estado de un pago.
 * 
 * @param paymentRequestId - ID del payment_request
 * @param options.enabled - Si debe hacer polling
 * @param options.refetchInterval - Intervalo de polling (default: 3000ms)
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

interface PaymentStatusResponse {
  id: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  purpose: string;
  amount_usd: number;
  created_at: string;
  approved_at?: string;
}

export function usePaymentStatus(
  paymentRequestId: string,
  options?: {
    enabled?: boolean;
    refetchInterval?: number | false;
  }
) {
  return useQuery<PaymentStatusResponse>({
    queryKey: ['payment', paymentRequestId],
    queryFn: async () => {
      const response = await apiClient.get<PaymentStatusResponse>(
        `/payments/${paymentRequestId}`
      );
      return response.data;
    },
    enabled: options?.enabled ?? !!paymentRequestId,
    refetchInterval: (data) => {
      // Dejar de hacer polling si el pago ya fue procesado
      if (data?.status === 'approved' || data?.status === 'rejected') {
        return false;
      }
      return options?.refetchInterval ?? 3000;
    },
  });
}
```

### Archivo: src/hooks/queries/useCreditBalance.ts

```typescript
/**
 * Hook para obtener el saldo de créditos del usuario.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/services/api';

interface CreditBalanceResponse {
  balance: number;
  last_updated: string;
}

export function useCreditBalance() {
  return useQuery<CreditBalanceResponse>({
    queryKey: ['credits', 'balance'],
    queryFn: async () => {
      const response = await apiClient.get<CreditBalanceResponse>(
        '/payments/credits/balance'
      );
      return response.data;
    },
  });
}
```

### Archivo: src/components/payments/PaymentButton.tsx

```tsx
/**
 * Botón reutilizable para iniciar un checkout de MercadoPago.
 */

import { useCreateCheckout } from '@/hooks/mutations/useCreateCheckout';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface PaymentButtonProps {
  purpose: 'report' | 'credits';
  targetEntityType?: string;
  targetEntityId?: string;
  creditsAmount?: number;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

export function PaymentButton({
  purpose,
  targetEntityType,
  targetEntityId,
  creditsAmount,
  children,
  className,
  disabled,
}: PaymentButtonProps) {
  const { mutate: createCheckout, isPending } = useCreateCheckout();

  const handleClick = () => {
    createCheckout({
      purpose,
      target_entity_type: targetEntityType,
      target_entity_id: targetEntityId,
      credits_amount: creditsAmount,
    });
  };

  return (
    <Button
      onClick={handleClick}
      disabled={disabled || isPending}
      className={className}
    >
      {isPending ? (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Procesando...
        </>
      ) : (
        children
      )}
    </Button>
  );
}
```

### Archivo: src/pages/PaymentReturnPage.tsx

```tsx
/**
 * Página de retorno después de pagar en MercadoPago.
 * Hace polling del estado hasta confirmación.
 */

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { usePaymentStatus } from '@/hooks/queries/usePaymentStatus';
import { CheckCircle, XCircle, Loader2, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';

const POLLING_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutos

export default function PaymentReturnPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [timedOut, setTimedOut] = useState(false);

  const paymentRequestId = searchParams.get('payment_request_id') || '';
  const initialStatus = searchParams.get('status');

  const { data: payment, isLoading } = usePaymentStatus(paymentRequestId, {
    enabled: !!paymentRequestId && !timedOut,
    refetchInterval: 3000,
  });

  // Timeout después de 5 minutos
  useEffect(() => {
    const timer = setTimeout(() => setTimedOut(true), POLLING_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, []);

  // Renderizar según estado
  if (timedOut) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
        <Clock className="h-16 w-16 text-yellow-500 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Verificación en proceso</h1>
        <p className="text-gray-600 mb-6">
          Tu pago está siendo procesado. Recibirás un email de confirmación
          cuando se acredite.
        </p>
        <Button onClick={() => navigate('/fires')}>
          Volver al inicio
        </Button>
      </div>
    );
  }

  if (isLoading || payment?.status === 'pending') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
        <Loader2 className="h-16 w-16 text-primary animate-spin mb-4" />
        <h1 className="text-2xl font-bold mb-2">Verificando pago...</h1>
        <p className="text-gray-600">
          Por favor espera mientras confirmamos tu pago.
        </p>
      </div>
    );
  }

  if (payment?.status === 'approved') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
        <CheckCircle className="h-16 w-16 text-green-500 mb-4" />
        <h1 className="text-2xl font-bold mb-2">¡Pago exitoso!</h1>
        <p className="text-gray-600 mb-6">
          Tus créditos han sido acreditados a tu cuenta.
        </p>
        <Button onClick={() => navigate('/fires')}>
          Continuar
        </Button>
      </div>
    );
  }

  if (payment?.status === 'rejected') {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-4">
        <XCircle className="h-16 w-16 text-red-500 mb-4" />
        <h1 className="text-2xl font-bold mb-2">Pago rechazado</h1>
        <p className="text-gray-600 mb-6">
          No pudimos procesar tu pago. Por favor intenta nuevamente.
        </p>
        <Button onClick={() => navigate('/credits')}>
          Intentar de nuevo
        </Button>
      </div>
    );
  }

  return null;
}
```

---

## Variables de entorno requeridas

```env
# Backend (.env)
MP_ACCESS_TOKEN=APP_USR-xxx-xxx
MP_WEBHOOK_SECRET=xxx  # Opcional pero recomendado
MP_NOTIFICATION_URL=https://api.forestguard.ar/api/v1/webhooks/mercadopago
MP_MOCK_MODE=false
MP_MOCK_APPROVE=true
BNA_EXCHANGE_RATE_URL=https://www.bna.com.ar/Personas

PAYMENT_SUCCESS_URL=https://forestguard.ar/payments/return?status=success
PAYMENT_FAILURE_URL=https://forestguard.ar/payments/return?status=failure
PAYMENT_PENDING_URL=https://forestguard.ar/payments/return?status=pending
```

---

## Checklist de verificación

### Backend
- [ ] Migración SQL ejecutada sin errores
- [x] MercadoPagoService implementado (pendiente validación sandbox)
- [x] POST /payments/checkout crea preferencia (pendiente validación sandbox)
- [x] Webhook procesa notificaciones correctamente (pendiente validación MP)
- [ ] Idempotencia verificada (webhook duplicado no duplica créditos)
- [ ] RLS policies funcionando

### Frontend
- [x] PaymentButton redirige a MercadoPago (pendiente validación end-to-end)
- [x] PaymentReturnPage hace polling correctamente
- [x] Timeout de 5 minutos funciona
- [x] Estados visuales correctos (loading, success, error)

### Integración
- [ ] Flujo completo funciona en sandbox
- [ ] Webhook recibe notificaciones de MP
- [ ] Créditos se acreditan correctamente
- [ ] Logs de auditoría se generan

---

## Actualizacion 2026-02-04: precios en ARS + cotizacion BNA

- El backend obtiene la cotizacion USD/ARS diaria desde Banco Nacion (BNA_EXCHANGE_RATE_URL).
- POST /payments/checkout calcula amount_ars y guarda exchange_rate en metadata; MercadoPago cobra en ARS.
- Nuevo GET /payments/pricing devuelve paquetes con precio_ars, exchange_rate y timestamp.
- El frontend muestra precios en ARS usando /payments/pricing.


## Cambios fuera del plan (implementados)
- Modo mock de MercadoPago para pruebas locales sin credenciales (MP_MOCK_MODE/MP_MOCK_APPROVE).
- UI de compra de créditos simplificada (input + botón) en Perfil/Créditos en lugar de modal.
- Se agregó la página de perfil para gestionar créditos.