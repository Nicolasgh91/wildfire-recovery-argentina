# ForestGuard v2.0 - Security Deep Audit

Fecha: 2026-02-16
Modo: repo-grounded con validacion externa parcial
Auditor: Codex (skills: security-threat-model, security-best-practices, security-ownership-map)

## Alcance y evidencia
- Backend FastAPI, auth/JWT/API keys, webhooks, idempotencia, rate limit, workers, storage, PDF.
- Frontend React/Supabase auth/session/protected routes/API client.
- Infra repo: Dockerfiles, compose, nginx, celery.
- Ownership map (fallback por dependencia faltante del script oficial):
  - `review/security/ownership/files_ownership_fallback.csv`
  - `review/security/ownership/tag_summary_fallback.csv`

## Limitaciones
- Validacion externa directa (headers/TLS del dominio productivo) no fue posible desde este entorno por restriccion de red/salida.
- Estado real de Cloudflare, IAM GCS y politicas activas RLS en Supabase: `requires manual verification`.

## Fase 1 - Threat model real

### Superficies
- API publica y autenticada (`app/main.py`)
- Webhooks MercadoPago (`app/api/v1/webhooks.py`)
- JWT/API keys (`app/services/supabase_auth.py`, `app/core/security.py`)
- Workers/Celery (`app/api/routes/tasks.py`, `app/api/routes/workers.py`, `workers/celery_app.py`)
- Storage/GCS/PDF (`app/services/storage_service.py`, `app/services/gcs_service.py`, `app/services/ers_service.py`)
- Nginx/Docker (`deployment/nginx.conf`, `docker/nginx.conf`, `docker-compose.yml`)
- Frontend auth/session (`frontend/src/services/api.ts`, `frontend/src/context/AuthContext.tsx`)

### Actores
- Anonimo, autenticado, admin, bot, insider, supply-chain.

### Abuse paths confirmados/reales
- Replay y bypass de verificacion webhook si falta secreto (`app/services/mercadopago_service.py:172`)
- Trigger de tareas internas con API key no-admin (`app/main.py:323`, `app/main.py:331`)
- Exposicion de API key desde frontend por diseno (`frontend/src/services/api.ts:12`, `frontend/src/services/api.ts:80`)
- Path traversal en backend local storage (`app/services/storage_service.py:177`, `app/services/storage_service.py:560`)
- Exfil por objetos GCS publicos en servicio legacy (`app/services/gcs_service.py:170`, `app/services/gcs_service.py:221`)

## Fase 2/3/4 - Hallazgos

### Controles correctos detectados
- JWT validado con `alg=ES256`, `issuer`, `audience`, `kid` (`app/services/supabase_auth.py:138`, `app/services/supabase_auth.py:157`, `app/services/supabase_auth.py:159`).
- Security headers middleware activo (`app/core/security_headers.py:19`-`app/core/security_headers.py:30`).
- Guardrail para bloquear `STORAGE_BACKEND=local` en produccion (`app/core/config.py:177`-`app/core/config.py:181`).
- Idempotency conflict devuelve `409` para body distinto (`app/core/idempotency.py:184`-`app/core/idempotency.py:191`).
- Ownership checks por `user_id` en explorations (anti-IDOR) (`app/services/exploration_service.py:206`-`app/services/exploration_service.py:209`).

### Vulnerabilidades / riesgos

1. Webhook fail-open cuando falta secreto
- Evidencia: `validate_webhook_signature()` retorna `True` si no hay `MP_WEBHOOK_SECRET` (`app/services/mercadopago_service.py:172`-`app/services/mercadopago_service.py:174`).
- Prueba ejecutada: `True` al validar con secreto ausente.
- Riesgo: aceptacion de notificaciones no autenticadas.

2. Endpoints de workers/tasks no exigen admin ni credencial de servicio separada
- Evidencia: routers registrados con `Depends(verify_api_key)` (`app/main.py:323`, `app/main.py:331`).
- `verify_api_key` acepta `API_KEY` usuario estandar (`app/core/security.py:87`-`app/core/security.py:89`).
- Riesgo: escalacion operacional (enqueued jobs internos).

3. Frontend inyecta `X-API-Key` desde variables publicas en todas las requests
- Evidencia: `const API_KEY = VITE_API_KEY || VITE_SUPABASE_ANON_KEY` (`frontend/src/services/api.ts:12`) y header siempre agregado (`frontend/src/services/api.ts:80`-`frontend/src/services/api.ts:82`).
- Riesgo: secure-by-default roto por mezcla JWT + API key publica.

4. Replay/idempotencia webhook no persistente
- Evidencia: dedupe en memoria de proceso `_processed_webhooks: set[str]` (`app/api/v1/webhooks.py:54`), comentario de fallback in-memory (`app/api/v1/webhooks.py:160`).
- Riesgo: replay cross-instance/restart.

5. Path traversal en local storage backend
- Evidencia: path local concatena `key` sin normalizar (`app/services/storage_service.py:177`-`app/services/storage_service.py:179`); lectura usa ese path (`app/services/storage_service.py:560`-`app/services/storage_service.py:563`).
- Prueba ejecutada: `../secrets.env` resuelve fuera de bucket.

6. GCS service legacy publica objetos por defecto
- Evidencia: `blob.make_public()` en subidas (`app/services/gcs_service.py:170`, `app/services/gcs_service.py:221`).
- Riesgo: exposicion de evidencia/documentos si se usa ese servicio.

7. OpenAPI/docs expuestos por defecto
- Evidencia: `docs_url="/docs"`, `redoc_url="/redoc"` (`app/main.py:154`-`app/main.py:156`).
- Riesgo: mayor superficie de reconocimiento.

8. Redis/Flower expuestos en compose y modo debug/reload
- Evidencia: `6379:6379` (`docker-compose.yml:9`), `5555:5555` (`docker-compose.yml:219`), `DEBUG: "true"` (`docker-compose.yml:48`), `--reload` (`docker-compose.yml:65`, `Dockerfile.api:29`).
- Riesgo: exposicion operativa si config de dev se despliega sin hardening.

9. Nginx docker con CORS wildcard
- Evidencia: `Access-Control-Allow-Origin *` (`docker/nginx.conf:26`).
- Riesgo: abuso cross-origin de endpoints si se usa esa config.

10. CSP en report-only con `unsafe-inline` y `unsafe-eval`
- Evidencia: (`deployment/nginx.conf:38`).
- Riesgo: cobertura incompleta frente a XSS si no se enforcea CSP estricta.

11. Logging de prefijo de API key
- Evidencia: `Invalid API key attempt: {api_key[:8]}...` (`app/core/security.py:91`).
- Riesgo: leakage parcial de credenciales en logs.

12. Tablas de idempotencia/reportes sin migracion visible en repo
- Evidencia de uso: `idempotency_keys` (`app/core/idempotency.py:166`), `generated_reports` (`app/api/routes/reports.py:307`, `app/api/routes/reports.py:526`).
- Busqueda en `database/alembic` sin definicion encontrada.
- Riesgo: deriva schema/auditabilidad. `requires manual verification`.

13. Frontend build con sourcemaps activados
- Evidencia: `sourcemap: true` (`frontend/vite.config.ts:67`-`frontend/vite.config.ts:68`).
- Riesgo: facilita reverse engineering del cliente.

## Fase 5 - Security Ownership Map

Nota: el script oficial `run_ownership_map.py` no pudo ejecutarse por dependencia faltante (`networkx`) en este entorno. Se genero fallback equivalente con `git log` en 12 meses.

### Resultado (fallback)
- Archivos: `review/security/ownership/files_ownership_fallback.csv`
- Resumen por tag: `review/security/ownership/tag_summary_fallback.csv`
- Concentracion alta por modulo (bus factor efectivo bajo):
  - `frontend_auth`, `workers`, `auth`, `infra`, `payments` con alto indice de riesgo ponderado.
- Patrones observados:
  - fuerte concentracion de ownership en muy pocos autores en modulos sensibles.
  - bus factor recurrente = 1 en rutas criticas.

## Requires manual verification
- TLS/HSTS/CSP/headers efectivos en dominio real y edge Cloudflare.
- Politicas IAM efectivas de buckets GCS y permisos de service accounts.
- Exposicion real de Redis/Celery/Flower en infraestructura productiva.
- Politicas RLS activas en Supabase para tablas sensibles (mas alla de `user_saved_filters`).

## Reproducciones tecnicas ejecutadas
1. Webhook fail-open:
- Resultado: `True` con secreto ausente.

2. Path traversal local storage:
- `../secrets.env` resolvio fuera de bucket local (escape de ruta).

3. Rate limiter backend:
- Backend actual detectado: `in_memory` (fallback por Redis no disponible).

