# Plan de Auditoría de Seguridad Integral ForestGuard v2.0

## Resumen
- Objetivo: ejecutar una auditoría profunda, repo-grounded, con validación externa, para detectar vulnerabilidades reales y priorizar remediación.
- Skills a usar en orden: `security-threat-model` -> `security-best-practices` -> `security-ownership-map`.
- Decisiones cerradas:
1. Alcance: `Con validación externa`.
2. Ownership window: `últimos 12 meses`.
3. Severidad: `Impacto (1-5) x Probabilidad (1-5)`.

## Cambios importantes de API/interfaces/tipos que se evaluarán (si el hallazgo lo exige)
1. Endpoints críticos con idempotencia: volver `X-Idempotency-Key` obligatorio y estandarizar `409` por conflicto.
2. Endpoints de workers/tasks: endurecer autorización a `admin` o credencial de servicio dedicada.
3. Webhooks de pago: rechazar tráfico si falta secreto (`503` fail-closed) y reforzar anti-replay persistente.
4. Contrato JWT: documentar claims obligatorios (`iss`, `aud`, `sub`, `exp`, `kid`, `role`) y errores homogéneos.
5. Cliente frontend: eliminar fallback de API key pública para flujos autenticados.
6. Storage/PDF: sanitización estricta de claves/rutas y validación MIME real en uploads.

## Criterio de hallazgo válido (anti-hallazgos teóricos)
1. Solo se reporta vulnerabilidad si cumple al menos una condición:
- Reproducción técnica con request/flujo ejecutable.
- Prueba de camino de código alcanzable sin control efectivo.
- Misconfiguración validada en entorno/config real.
2. Si no se puede validar por acceso externo, se marca `requires manual verification` con evidencia mínima y paso exacto para confirmación.
3. También se documentan controles correctos cuando estén bien implementados.

## Modelo de scoring
1. `Score = Impacto x Probabilidad` (1-25).
2. Severidad:
- `Critical`: 20-25
- `High`: 15-19
- `Medium`: 8-14
- `Low`: 1-7
3. Impacto se asigna por confidencialidad/integridad/disponibilidad/regulatorio.
4. Probabilidad se asigna por explotabilidad, exposición, requisitos previos y detectabilidad.

## Fase 0 — Preflight y baseline de evidencia
1. Consolidar documentación canónica usando equivalentes reales del repo.
2. Levantar inventario base:
- Endpoints API (públicos/autenticados/admin/webhook).
- Servicios críticos (auth, storage, payments, workers).
- Configs de despliegue (`docker`, `deployment`, `nginx`, `supabase`).
3. Definir plantilla única de evidencia por hallazgo:
- `ID`, `Componente`, `Archivo:línea`, `Vector`, `Precondiciones`, `PoC/Prueba`, `Impacto`, `Probabilidad`, `Severidad`, `Fix`, `Estado`.
4. Criterio de salida fase:
- Inventario completo y plantilla lista.

## Fase 1 — Threat Modeling real de ForestGuard
1. Construir trust boundaries y data flows:
- Cliente -> Cloudflare -> Nginx -> FastAPI
- FastAPI -> Supabase/Postgres
- FastAPI/Workers -> GCS
- FastAPI -> MercadoPago/GEE
2. Cubrir superficies pedidas:
- API pública/autenticada/admin
- webhooks
- Celery/Redis
- JWT/API keys
- RLS
- uploads/PDF
- wizard/explorations
- audit endpoint
- rate limit/idempotency
3. Actores maliciosos:
- anónimo, autenticado, con créditos, admin, bot externo, insider, supply chain.
4. Abuse paths obligatorios:
- RLS bypass, IDOR, privilege escalation, replay/idempotency abuse, JWT gaps, rate-limit bypass, SSRF, task poisoning, DOS, data exfiltration.
5. Criterio de salida fase:
- Matriz actor -> superficie -> abuso -> control existente -> gap confirmado/manual.

## Fase 2 — Auditoría Backend profunda
1. AuthN/AuthZ y secretos:
- `app/core/security.py`
- `app/api/auth_deps.py`
- `app/services/supabase_auth.py`
- dependencias de routers en `app/main.py`
- controles admin (`require_admin`) vs `verify_api_key`.
2. Webhooks, idempotencia y rate limit:
- `app/api/v1/webhooks.py`
- `app/services/mercadopago_service.py`
- `app/core/idempotency.py`
- `app/core/rate_limiter.py`
3. Datos, consultas y async:
- servicios de acceso a DB y consultas raw.
- verificación de filtros por `user_id`, multi-tenant safety, y anti-IDOR.
4. Archivos, PDF y storage:
- `app/services/storage_service.py`
- `app/services/gcs_service.py`
- `app/services/pdf_service.py`
- `app/services/report_pdf_service.py`
- `app/services/contact_service.py`
5. Seguridad operativa:
- `app/core/config.py`
- `app/core/errors.py`
- logging y redacción de secretos.
6. Pruebas dirigidas backend:
- JWT inválido (alg/iss/aud/exp/kid).
- Reutilización de webhook firmado.
- Bypass rate-limit por headers proxy.
- colisión/race de idempotency key.
- intentos IDOR cross-user.
7. Criterio de salida fase:
- Hallazgos backend priorizados con evidencia concreta por archivo.

## Fase 3 — Auditoría Frontend
1. Sesión y tokens:
- `frontend/src/lib/supabase.ts`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/services/api.ts`
2. Control de acceso UI:
- `frontend/src/components/auth/ProtectedRoute.tsx`
- rutas en `frontend/src/App.tsx`
3. Riesgos XSS/inyección/CSRF:
- búsqueda de `dangerouslySetInnerHTML`, uso de query params, manipulación de descargas.
4. Exposición de variables públicas:
- `VITE_*` y fallbacks inseguros.
5. Pruebas dirigidas frontend:
- elevación por flags de cliente.
- token expirado/refresh y comportamiento.
- acceso a rutas protegidas manipulando estado local.
6. Criterio de salida fase:
- Matriz de riesgos frontend con separación clara entre control UI y control backend real.

## Fase 4 — Workers e Infra (repo + validación externa)
1. Revisión repo:
- `Dockerfile.api`
- `Dockerfile.worker`
- `docker-compose.yml`
- `docker/docker-compose.yml`
- `deployment/nginx.conf`
- `docker/nginx.conf`
- `workers/celery_app.py`
2. Validación externa requerida:
- TLS/HSTS/CSP/headers en dominio real.
- políticas IAM de buckets GCS y service accounts.
- exposición Redis/Celery broker/Flower.
- alineación de políticas RLS activas en Supabase.
- configuración Cloudflare relevante (TLS, WAF/rate limits).
3. Si falta acceso a una plataforma:
- registrar `requires manual verification` con comando/consulta exacta.
4. Criterio de salida fase:
- checklist infra con estado `confirmed` o `requires manual verification`.

## Fase 5 — Security Ownership Map
1. Generar mapa en ventana de 12 meses con foco sensible.
2. Comando base:
```powershell
python C:\Users\nicog\.codex\skills\security-ownership-map\scripts\run_ownership_map.py `
  --repo . `
  --out review/security/ownership `
  --since "12 months ago" `
  --identity author `
  --date-field author `
  --emit-commits `
  --graphml `
  --sensitive-config review/security/sensitive_paths.csv `
  --bus-factor-threshold 2 `
  --stale-days 90 `
  --owner-threshold 0.6
```
3. Consultas de resumen:
```powershell
python C:\Users\nicog\.codex\skills\security-ownership-map\scripts\query_ownership.py --data-dir review/security/ownership summary
python C:\Users\nicog\.codex\skills\security-ownership-map\scripts\query_ownership.py --data-dir review/security/ownership tag --tag auth --limit 20
python C:\Users\nicog\.codex\skills\security-ownership-map\scripts\query_ownership.py --data-dir review/security/ownership tag --tag payments --limit 20
python C:\Users\nicog\.codex\skills\security-ownership-map\scripts\query_ownership.py --data-dir review/security/ownership tag --tag infra --limit 20
```
4. Entregable fase:
- bus factor por módulo sensible.
- componentes sin ownership claro.
- concentración de riesgo por persona/equipo.

## Fase 6 — Reporte final obligatorio
1. `Resumen Ejecutivo`:
- riesgo general `Low/Medium/High`.
- top 5 riesgos críticos.
- recomendación estratégica.
2. `Matriz de Riesgos`:
- tabla con `ID | Vulnerabilidad | Impacto | Probabilidad | Severidad | Archivo | Fix recomendado`.
3. `Quick Wins (<=1 día)`:
- lista priorizada y accionable.
4. `Fixes estructurales`:
- cambios de arquitectura y hardening sostenido.
5. `Checklist Secure-by-Default`:
- least privilege
- defense in depth
- zero trust boundaries
- secure storage
- auditability
- reproducibility integrity
- supply chain safety
6. Regla de calidad del reporte:
- cada hallazgo con ruta de archivo específica.
- incluir controles correctos ya bien implementados.
- marcar incertidumbres como `requires manual verification`.

## Casos de prueba y escenarios mínimos de aceptación
1. JWT mal firmado/reclamaciones inválidas debe fallar siempre.
2. Endpoint admin debe bloquear usuario no admin aunque UI lo permita.
3. Webhook replay no debe reprocesar evento.
4. Idempotency conflict debe ser consistente en concurrencia.
5. Rate limit debe sostenerse detrás de proxy/CDN.
6. Acceso cross-tenant (IDOR/RLS) debe ser denegado.
7. Upload/PDF no debe permitir traversal ni payload activo.
8. Logs no deben exponer secretos/tokens.
9. Redis/Celery no debe quedar expuesto públicamente.
10. Headers de seguridad y TLS deben estar activos en producción.

## Supuestos y defaults explícitos
1. Se usará acceso externo cuando existan credenciales; si no, se documentará verificación manual exacta.
2. No se harán pruebas destructivas ni de denegación real contra producción.
3. Se prioriza evidencia reproducible sobre volumen de hallazgos.
4. Los hallazgos de entornos de desarrollo se reportarán separados de producción para evitar falsos positivos.
