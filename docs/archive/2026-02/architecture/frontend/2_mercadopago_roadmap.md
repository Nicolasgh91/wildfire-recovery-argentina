# Roadmap técnico de integración frontend - ForestGuard

**Fecha**: 2026-02-03  
**Versión**: 1.2  
**Estado del backend**: ✅ Completo (fase 5 testing)

---

## 1. Resumen ejecutivo

Este documento define la estrategia de integración del frontend React existente con el backend FastAPI completado. El enfoque prioriza costo cero en infraestructura (solo comisiones por transacción), seguridad robusta y elegancia arquitectónica.

### Decisiones clave de esta versión

| Decisión | Valor | Justificación |
|----------|-------|---------------|
| Audit logs de test | Flag `is_test: true` | Permite limpieza selectiva post-testing |
| Pasarela de pagos | **MercadoPago Checkout Pro** | Sin fee fijo, solo comisión por transacción |
| Email de pruebas | nicolasgabrielh91@gmail.com | Centraliza notificaciones de test |
| Testing E2E | Contra producción | Simplifica setup, datos reales |
| Seguridad VITE_* | Validada | RLS + Rate Limit + JWT protegen |

### Cambios en v1.2

| Cambio | Detalle |
|--------|---------|
| Agregado | Fase 3.4 - Integración MercadoPago Checkout Pro |
| Modificado | Sistema de créditos con tabla de transacciones |
| Estimación | 16 → 18 días (+2 días para pagos) |

---

## 2. Arquitectura de pagos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE PAGO - MERCADOPAGO CHECKOUT PRO                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FRONTEND                 BACKEND                    MERCADOPAGO            │
│  ════════                 ═══════                    ══════════             │
│                                                                             │
│  1. Usuario               2. Crea                    3. Retorna             │
│     solicita ────────────▶   payment_request ───────▶   preferencia         │
│     reporte                  + preferencia MP           + init_point        │
│                                     │                                       │
│                                     ▼                                       │
│  4. Recibe ◀──────────────── checkout_url                                  │
│     URL                                                                     │
│       │                                                                     │
│       ▼                                                                     │
│  5. Redirige ─────────────────────────────────────▶ 6. Checkout            │
│     a MP                                               externo              │
│                                                           │                 │
│                                                           ▼                 │
│  7. Usuario ◀──────────────────────────────────────── completa             │
│     retorna                                              pago               │
│     (back_url)                                            │                 │
│       │                                                   │                 │
│       ▼                                                   ▼                 │
│  8. Polling ─────────────▶ 9. GET /payments/{id}    10. Webhook            │
│     estado                    retorna status ◀────────── notifica          │
│       │                              │                                      │
│       │                              ▼                                      │
│       │                       11. Si approved:                              │
│       │                           - Acredita créditos                       │
│       │                           - O genera reporte                        │
│       │                                                                     │
│       ▼                                                                     │
│  12. Muestra                                                                │
│      confirmación                                                           │
│                                                                             │
│  REGLA CRÍTICA: Nunca confiar en back_url como prueba de pago.             │
│  Solo el webhook + verificación API confirman el pago.                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Roadmap de fases actualizado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ROADMAP DE INTEGRACIÓN (v1.2)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FASE 0: Fundamentos (3 días)                                               │
│  ═══════════════════════════                                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-0.1  │──▶│ FE-0.2  │──▶│ FE-0.3  │                                   │
│  │ApiService│  │Supabase │   │TanStack │                                   │
│  │ (1 día) │   │Auth(1d) │   │Query(1d)│                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│       │                            │                                        │
│       ▼                            ▼                                        │
│  FASE 1: Módulos críticos (4 días)                                          │
│  ══════════════════════════════════                                         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐                     │
│  │ FE-1.1  │──▶│ FE-1.2  │──▶│ FE-1.3  │──▶│ FE-1.4  │                     │
│  │FireList │   │FireDetail│  │FireStats│   │ Export  │                     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘                     │
│       │                                          │                          │
│       ▼                                          ▼                          │
│  FASE 2: Visualización geoespacial (3 días)                                 │
│  ══════════════════════════════════════════                                 │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-2.1  │──▶│ FE-2.2  │──▶│ FE-2.3  │                                   │
│  │deck.gl  │   │H3 Layer │   │MapPage  │                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│       │                            │                                        │
│       ▼                            ▼                                        │
│  FASE 3: Módulos premium (5 días)                                           │
│  ════════════════════════════════                                           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐                     │
│  │ FE-3.1  │──▶│ FE-3.2  │──▶│ FE-3.3  │──▶│ FE-3.4  │  ← NUEVO           │
│  │ Audit   │   │ Reports │   │Contact  │   │MercadoPago                    │
│  │ (1 día) │   │ (1 día) │   │ (1 día) │   │ (2 días)│                     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘                     │
│       │                                          │                          │
│       ▼                                          ▼                          │
│  FASE 4: Pulido y testing (3 días)                                          │
│  ═════════════════════════════════                                          │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐                                   │
│  │ FE-4.1  │──▶│ FE-4.2  │──▶│ FE-4.3  │                                   │
│  │E2E Tests│   │ErrorBnd │   │Lazy Load│                                   │
│  │(prod DB)│   │+ Sentry │   │ + PWA   │                                   │
│  └─────────┘   └─────────┘   └─────────┘                                   │
│                                  │                                          │
│                                  ▼                                          │
│                          ══ INTEGRACIÓN COMPLETA ══                         │
│                                                                             │
│  Total estimado: 18 días                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Precios definidos

| Concepto | Precio USD | Créditos |
|----------|------------|----------|
| 1 imagen HD | $0.50 | 1 crédito |
| Reporte judicial (12 img) | $6.00 | 12 créditos |
| Reporte histórico (12 img) | $6.00 | 12 créditos |
| Paquete básico | $2.50 | 5 créditos |
| Paquete estándar | $5.00 | 12 créditos |
| Paquete premium | $10.00 | 25 créditos |

Nota: los precios base se definen en USD y se convierten automaticamente a ARS usando la cotizacion oficial diaria del Banco Nacion.

---

## 5. Checklist de entrega Fase 3.4

### Backend
- [ ] Migración SQL ejecutada (3 tablas)
- [x] `POST /payments/checkout` implementado
- [x] `POST /webhooks/mercadopago` implementado
- [x] `GET /payments/{id}` implementado
- [x] `GET /credits/balance` implementado
- [x] `GET /credits/transactions` implementado

### Frontend
- [x] `PaymentButton.tsx` creado
- [x] `PaymentStatusPoller.tsx` creado
- [x] `CreditBalance.tsx` creado
- [x] UI de compra de créditos (input + botón)
- [x] `PaymentReturnPage.tsx` creado
- [ ] Tests E2E de flujo de pago (sandbox)

### Cambios fuera del plan (implementados)
- Modo mock de MercadoPago para pruebas locales sin credenciales (MP_MOCK_MODE/MP_MOCK_APPROVE).
- Precios en ARS con conversión diaria BNA y endpoint `/payments/pricing`.
- Flujo de créditos movido a página Perfil y panel de Créditos.

---

**Estimación total**: 18 días  
**Prioridad**: Fase 0 → Fase 1 → Fase 3.4 → Fase 3 resto → Fase 2 → Fase 4
