# ADR-0001: Autenticación única con Supabase Auth

Date: 2026-02-12  
Status: Accepted

## Contexto

ForestGuard contenía dos sistemas de autenticación en paralelo:

- Auth nativo via `/api/v1/auth` (JWT propio).
- Supabase Auth (SDK en frontend, JWT de Supabase).

Esto generaba inconsistencias entre endpoints (por ejemplo, audit con API key y payments con JWT) y fallas en flujos externos.

## Decisión

Usar Supabase Auth como única fuente de verdad para autenticación de usuarios.

Se eliminan:

- Endpoints `/api/v1/auth/*` (login, register, google, profile).
- Emisión y validación de JWT nativo.
- Fallbacks legacy en frontend (descubrimiento de claves en localStorage y compatibilidad con payloads alternativos).

Los endpoints de usuario requieren JWT de Supabase y lo validan contra:

- Firma (`SUPABASE_JWT_SECRET`).
- `aud` (`SUPABASE_JWT_AUDIENCE`).
- `iss` (`SUPABASE_URL + /auth/v1`).

## Alternativas consideradas

1. Mantener auth nativo y Supabase en paralelo.
   - Rechazado: duplica superficie de ataque y crea inconsistencias.

2. Migrar todo a auth nativo.
   - Rechazado: Supabase ya es el proveedor objetivo y simplifica OAuth y mobile.

## Consecuencias

Positivas:

- Consistencia de sesión y token en frontend y backend.
- Menos deuda técnica y menor complejidad.
- Flujos externos (como MercadoPago) más robustos.

Negativas:

- Rompe clientes que dependan de `/api/v1/auth/*`.
- Requiere `SUPABASE_JWT_SECRET` configurado correctamente en backend.

## Mitigaciones

- Refactor incremental con commits pequeños.
- Runbook de validación manual y tests actualizados.
- Documentar cambios en notas de versión.
