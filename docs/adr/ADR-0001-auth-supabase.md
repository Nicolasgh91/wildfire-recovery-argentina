# ADR-0001: Autenticacion unica con Supabase Auth

Date: 2026-02-12
Status: Accepted

## Contexto
ForestGuard contiene dos sistemas de autenticacion en paralelo:
- Auth nativo via /api/v1/auth (JWT propio)
- Supabase Auth (SDK en frontend, JWT Supabase)

Esto genera inconsistencias entre endpoints (audit usa API key, payments usa JWT) y fallas en flujos externos.

## Decision
Usar Supabase Auth como unica fuente de verdad para autenticacion de usuarios.

Se eliminan:
- Endpoints /api/v1/auth/* (login/register/google/profile)
- Emision y validacion de JWT nativo
- Fallbacks legacy en frontend (localStorage key discovery y compatibilidad con payloads alternativos)

Los endpoints de usuario requeriran JWT de Supabase y lo validaran contra:
- Firma (SUPABASE_JWT_SECRET)
- aud (SUPABASE_JWT_AUDIENCE)
- iss (SUPABASE_URL + /auth/v1)

## Alternativas consideradas
1) Mantener auth nativo y Supabase en paralelo
- Rechazado: duplica superficie de ataque y crea inconsistencias.

2) Migrar todo a auth nativo
- Rechazado: Supabase ya es el proveedor objetivo y simplifica OAuth y mobile.

## Consecuencias
Positivas:
- Consistencia de sesion y token en frontend y backend.
- Menos deuda tecnica y menor complejidad.
- Flujos externos (Mercado Pago) mas robustos.

Negativas:
- Rompe clientes que dependan de /api/v1/auth/*
- Requiere SUPABASE_JWT_SECRET en backend

## Mitigaciones
- Refactor incremental con commits pequenos.
- Runbook de validacion manual y tests actualizados.
- Documentar cambios en release notes.

