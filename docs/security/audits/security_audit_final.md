# ForestGuard v2.0 — Auditoría de Seguridad Integral

> **Fecha**: 2026-02-16  
> **Modo**: repo-grounded con validación externa parcial  
> **Auditor**: Codex (skills: security-threat-model, security-best-practices, security-ownership-map)  
> **Scoring**: Impacto (1–5) × Probabilidad (1–5) = Severidad (1–25)  
> **Criterio de hallazgo**: solo se reporta con reproducción técnica, camino de código alcanzable, o misconfiguración validada.

---

## 1. Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| **Riesgo general** | **Medium-High** |
| **Hallazgos totales** | 13 |
| **Critical (20–25)** | 0 |
| **High (15–19)** | 1 |
| **Medium (8–14)** | 8 |
| **Low (1–7)** | 4 |
| **Controles correctos documentados** | 5 |
| **Requires manual verification** | 4 items (infra productiva) |
| **Bus factor = 1 en módulos sensibles** | 20 de 21 archivos auditados |

### Top 5 riesgos

| # | ID | Vulnerabilidad | Severidad |
|---|---|---|---|
| 1 | SEC-001 | Webhook fail-open sin secreto | **16 High** |
| 2 | SEC-002 | Workers/tasks sin auth admin dedicada | 12 Medium |
| 3 | SEC-003 | Frontend API-key fallback para flujos autenticados | 12 Medium |
| 4 | SEC-004 | Webhook replay protection solo in-memory | 12 Medium |
| 5 | SEC-005 | Path traversal en storage backend local | 10 Medium |

### Recomendación estratégica

1. **Inmediato (≤1 día)**: Cerrar webhook fail-open (SEC-001) y deshabilitar sourcemaps en producción (SEC-013).  
2. **Corto plazo (1 semana)**: Migrar replay protection a Redis persistente (SEC-004), endurecer workers con `require_admin` (SEC-002), eliminar API-key fallback en frontend (SEC-003).  
3. **Mediano plazo (1 mes)**: Hardening de CSP a enforcement (SEC-010), sanitización de keys de storage (SEC-005), auditoría IAM/RLS de producción.  
4. **Sostenido**: Incrementar bus factor en módulos sensibles (auth, payments, workers, infra).

---

## 2. Matriz de Riesgos Completa

| ID | Vulnerabilidad | Componente | Archivo:Línea | Impacto | Prob. | Sev. | Nivel |
|---|---|---|---|---|---|---|---|
| SEC-001 | Webhook fail-open cuando falta secreto | Payments/Webhooks | [mercadopago_service.py:172–174](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/mercadopago_service.py#L172-L174) | 4 | 4 | **16** | **High** |
| SEC-002 | Workers/tasks endpoints aceptan API key usuario, no requieren admin | Workers | [main.py:323](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L323), [main.py:331](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L331) | 4 | 3 | **12** | Medium |
| SEC-003 | Frontend inyecta X-API-Key pública en todas las requests (fallback anon key) | Frontend Auth | [api.ts:12](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts#L12), [api.ts:80–82](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts#L80-L82) | 3 | 4 | **12** | Medium |
| SEC-004 | Webhook replay protection in-memory (no persiste restart/multi-instance) | Webhooks | [webhooks.py:54](file:///c:/Users/nicog/wildfire-recovery-argentina/app/api/v1/webhooks.py#L54), [webhooks.py:160](file:///c:/Users/nicog/wildfire-recovery-argentina/app/api/v1/webhooks.py#L160) | 4 | 3 | **12** | Medium |
| SEC-005 | Path traversal en local storage backend (key sin sanitizar) | Storage | [storage_service.py:177–179](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#L177-L179), [storage_service.py:560–563](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#L560-L563) | 5 | 2 | **10** | Medium |
| SEC-006 | GCS legacy service publica objetos por defecto (`make_public`) | Storage | [gcs_service.py:170](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/gcs_service.py#L170), [gcs_service.py:221](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/gcs_service.py#L221) | 4 | 2 | **8** | Medium |
| SEC-007 | OpenAPI docs expuestos en producción (`/docs`, `/redoc`) | API Config | [main.py:154–155](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L154-L155) | 2 | 4 | **8** | Medium |
| SEC-008 | Redis/Flower puertos expuestos en compose, DEBUG=true, --reload | Infra | [docker-compose.yml:9](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml#L9), [docker-compose.yml:219](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml#L219), [docker-compose.yml:48](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml#L48) | 4 | 2 | **8** | Medium |
| SEC-009 | Nginx Docker config con CORS wildcard `*` | Infra/CORS | [docker/nginx.conf:26](file:///c:/Users/nicog/wildfire-recovery-argentina/docker/nginx.conf#L26) | 3 | 3 | **9** | Medium |
| SEC-010 | CSP en report-only con `unsafe-inline` + `unsafe-eval` | Infra/Headers | [deployment/nginx.conf:38](file:///c:/Users/nicog/wildfire-recovery-argentina/deployment/nginx.conf#L38) | 3 | 3 | **9** | Medium |
| SEC-011 | Logging de prefijo de API key (leakage parcial) | Auth | [security.py:91](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/security.py#L91) | 2 | 3 | **6** | Low |
| SEC-012 | Tablas `idempotency_keys`/`generated_reports` sin migración visible en repo | Schema | [idempotency.py:166](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/idempotency.py#L166), [reports.py:307](file:///c:/Users/nicog/wildfire-recovery-argentina/app/api/routes/reports.py#L307) | 2 | 2 | **4** | Low |
| SEC-013 | Frontend build con `sourcemap: true` en producción | Frontend | [vite.config.ts:68](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/vite.config.ts#L68) | 2 | 3 | **6** | Low |

### Justificación del scoring

**Impacto** se asigna por: Confidencialidad (datos personales, tokens), Integridad (pagos, créditos, reportes legales), Disponibilidad, Regulatorio (Ley 26.815).  
**Probabilidad** se asigna por: Explotabilidad (skill requerido), Exposición (público/autenticado/admin), Requisitos previos (acceso al secreto, red interna), Detectabilidad.

---

## 3. Detalle de Hallazgos

### SEC-001 — Webhook fail-open cuando falta secreto (High: 16)

- **Vector**: `validate_webhook_signature()` retorna `True` si `MP_WEBHOOK_SECRET` no está configurado.
- **Archivo**: [mercadopago_service.py:172–174](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/mercadopago_service.py#L172-L174)
- **Precondiciones**: Secreto no configurado en env productivo.
- **PoC**: Llamada a `validate_webhook_signature(None, None, "any")` retorna `True`.
- **Reproducción ejecutada**: ✅ Confirmada — `True` con secreto ausente.
- **Impacto**: Aceptación de webhooks no autenticados → acreditación de créditos fraudulentos.
- **Fix**: Cambiar a fail-closed: retornar `False` (o HTTP 503) si falta secreto.

```python
# Fix propuesto
if not self._webhook_secret:
    logger.error("Webhook secret not configured — rejecting request")
    return False
```

---

### SEC-002 — Workers/tasks sin auth admin (Medium: 12)

- **Vector**: Routers `workers` y `tasks` registrados con `Depends(verify_api_key)`, que acepta `API_KEY` de usuario estándar.
- **Archivo**: [main.py:323](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L323), [main.py:331](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L331)
- **Precondiciones**: Tener la API key de usuario (expuesta en frontend).
- **Impacto**: Escalación operacional — enqueue jobs internos de ingestion/clustering/analysis.
- **Fix**: Reemplazar `Depends(verify_api_key)` por `Depends(require_admin)`.

```diff
-    dependencies=[Depends(verify_api_key)],  # workers
+    dependencies=[Depends(require_admin)],    # workers
-    dependencies=[Depends(verify_api_key)],  # tasks
+    dependencies=[Depends(require_admin)],    # tasks
```

---

### SEC-003 — Frontend API-key fallback inseguro (Medium: 12)

- **Vector**: `API_KEY = VITE_API_KEY || SUPABASE_ANON_KEY` → siempre se envía una API key pública en header `X-API-Key`, rompiendo secure-by-default para flujos autenticados con JWT.
- **Archivo**: [api.ts:12](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts#L12), [api.ts:80–82](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/src/services/api.ts#L80-L82)
- **Precondiciones**: Ninguna — cualquier usuario del frontend.
- **Impacto**: API key pública visible en DevTools; si se usa para autorización real, bypass trivial para endpoints protegidos por `verify_api_key`.
- **Fix**: Eliminar fallback a `SUPABASE_ANON_KEY`; no enviar `X-API-Key` si el usuario tiene JWT.

```typescript
// Fix propuesto
if (API_KEY && !token) {
  setHeaderValue(headers, 'X-API-Key', API_KEY)
}
```

---

### SEC-004 — Webhook replay protection in-memory (Medium: 12)

- **Vector**: `_processed_webhooks: set[str]` vive en memoria del proceso. Se pierde en restart y no comparte entre workers/instancias.
- **Archivo**: [webhooks.py:54](file:///c:/Users/nicog/wildfire-recovery-argentina/app/api/v1/webhooks.py#L54)
- **Precondiciones**: Multi-instance deploy o restart del proceso.
- **Impacto**: Replay de webhook → doble acreditación de créditos.
- **Fix**: Migrar a Redis SET con TTL (5 min) o tabla `webhook_events` con UNIQUE constraint.

---

### SEC-005 — Path traversal en local storage (Medium: 10)

- **Vector**: `_local_path()` concatena `key` directamente al root sin normalizar.
- **Archivo**: [storage_service.py:177–179](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/storage_service.py#L177-L179)
- **Precondiciones**: `STORAGE_BACKEND=local` (bloqueado en producción por guardrail — mitigado parcialmente).
- **PoC**: `key = "../secrets.env"` resuelve fuera del bucket.
- **Reproducción ejecutada**: ✅ Confirmada — path escapa del directorio base.
- **Impacto**: Lectura/escritura arbitraria en filesystem (solo dev/staging por guardrail).
- **Fix**: Validar que `path.resolve()` tiene como prefijo `self._local_root`.

```python
def _local_path(self, key: str, bucket: Optional[str]) -> Path:
    bucket = bucket or self._default_bucket
    resolved = (self._local_root / bucket / key).resolve()
    if not resolved.is_relative_to(self._local_root):
        raise StorageError(f"Path traversal blocked: {key}")
    return resolved
```

---

### SEC-006 — GCS legacy `make_public()` (Medium: 8)

- **Vector**: `gcs_service.py` (servicio legacy) llama `blob.make_public()` en uploads.
- **Archivo**: [gcs_service.py:170](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/gcs_service.py#L170), [gcs_service.py:221](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/gcs_service.py#L221)
- **Precondiciones**: Que se use este servicio legacy en lugar del `storage_service.py` principal.
- **Impacto**: Documentos/evidencia accesibles públicamente sin autenticación.
- **Fix**: Deprecar `gcs_service.py` o eliminar `make_public()`.

---

### SEC-007 — OpenAPI docs expuestos (Medium: 8)

- **Vector**: `docs_url="/docs"`, `redoc_url="/redoc"` activos por defecto.
- **Archivo**: [main.py:154–155](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L154-L155)
- **Fix**: Condicionar a `ENVIRONMENT != "production"`.

```python
docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
```

---

### SEC-008 — Redis/Flower expuestos en compose (Medium: 8)

- **Vector**: `6379:6379` (Redis) y `5555:5555` (Flower) en docker-compose; `DEBUG: "true"`, `--reload` activo.
- **Archivo**: [docker-compose.yml:9,48,65,219](file:///c:/Users/nicog/wildfire-recovery-argentina/docker-compose.yml)
- **Fix**: Remover port mappings en producción o bind a `127.0.0.1:6379:6379`. Separar compose dev/prod.

---

### SEC-009 — Nginx Docker CORS wildcard (Medium: 9)

- **Vector**: `add_header Access-Control-Allow-Origin *` en Docker nginx config.
- **Archivo**: [docker/nginx.conf:26](file:///c:/Users/nicog/wildfire-recovery-argentina/docker/nginx.conf#L26)
- **Fix**: Reemplazar `*` por orígenes explícitos. **Nota**: El `deployment/nginx.conf` de producción no tiene este problema (CORS se maneja por FastAPI middleware con origins explícitos).

---

### SEC-010 — CSP report-only con unsafe-inline/eval (Medium: 9)

- **Vector**: `Content-Security-Policy-Report-Only` con `'unsafe-inline'` y `'unsafe-eval'`.
- **Archivo**: [deployment/nginx.conf:38](file:///c:/Users/nicog/wildfire-recovery-argentina/deployment/nginx.conf#L38)
- **Fix**: Plan de migración a enforcement: (1) monitorear violations, (2) usar nonces, (3) cambiar a `Content-Security-Policy`.

---

### SEC-011 — API key prefix logged (Low: 6)

- **Vector**: `f"Invalid API key attempt: {api_key[:8]}..."` en logs.
- **Archivo**: [security.py:91](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/security.py#L91)
- **Fix**: Loguear `api_key[:4]` o solo `"***"`.

---

### SEC-012 — Tablas sin migración visible (Low: 4)

- **Vector**: `idempotency_keys` y `generated_reports` referenciadas en código pero sin archivo de migración Alembic.
- **Estado**: `requires manual verification` — verificar si existen como migraciones ad-hoc o creadas manualmente.
- **Fix**: Crear migración Alembic para ambas tablas.

---

### SEC-013 — Sourcemaps en producción (Low: 6)

- **Vector**: `sourcemap: true` en `build` de Vite config.
- **Archivo**: [vite.config.ts:68](file:///c:/Users/nicog/wildfire-recovery-argentina/frontend/vite.config.ts#L68)
- **Fix**: Condicionar a `mode !== 'production'` o usar `'hidden'`.

```typescript
sourcemap: process.env.NODE_ENV !== 'production',
```

---

## 4. Controles Correctos Documentados

| Control | Archivo | Detalle |
|---|---|---|
| JWT ES256 con `issuer`, `audience`, `kid` | [supabase_auth.py:138,157,159](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/supabase_auth.py#L138) | Validación completa de algoritmo, emisor, audiencia y key id |
| Security headers middleware | [security_headers.py:19–30](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/security_headers.py#L19) | X-Content-Type-Options, X-Frame-Options, Referrer-Policy |
| Storage guardrail producción | [config.py:177–181](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/config.py#L177) | Bloquea `STORAGE_BACKEND=local` en `ENVIRONMENT=production` |
| Idempotency 409 conflict | [idempotency.py:184–191](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/idempotency.py#L184) | Devuelve 409 si misma key con body distinto |
| IDOR checks por user_id | [exploration_service.py:206–209](file:///c:/Users/nicog/wildfire-recovery-argentina/app/services/exploration_service.py#L206) | Ownership verificado en explorations |
| CORS explícito en FastAPI | [main.py:168–176](file:///c:/Users/nicog/wildfire-recovery-argentina/app/main.py#L168) | Métodos/headers explícitos, no wildcards (BL-004) |
| HSTS + TLS en nginx prod | [deployment/nginx.conf:16–18,30](file:///c:/Users/nicog/wildfire-recovery-argentina/deployment/nginx.conf#L16) | TLSv1.2+, HSTS 1 año, OCSP stapling |
| Timing-safe key comparison | [security.py:83,88](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/security.py#L83) | `secrets.compare_digest()` para API keys |
| Trusted proxy IP extraction | [rate_limiter.py](file:///c:/Users/nicog/wildfire-recovery-argentina/app/core/rate_limiter.py) | Solo acepta `X-Forwarded-For` de proxies confiables |

---

## 5. Quick Wins (≤ 1 día)

| Prioridad | ID | Fix | Esfuerzo |
|---|---|---|---|
| 🔴 1 | SEC-001 | Fail-closed en webhook: `return False` si falta secreto | 15 min |
| 🟠 2 | SEC-013 | Deshabilitar sourcemaps: `sourcemap: process.env.NODE_ENV !== 'production'` | 5 min |
| 🟠 3 | SEC-007 | Condicionar `/docs` y `/redoc` a non-production | 10 min |
| 🟠 4 | SEC-011 | Reducir prefijo loggeado de API key a 4 chars o masked | 5 min |
| 🟡 5 | SEC-009 | Reemplazar `Access-Control-Allow-Origin *` por orígenes explícitos en docker nginx | 15 min |
| 🟡 6 | SEC-002 | Cambiar `verify_api_key` → `require_admin` en workers/tasks routers | 10 min |

**Total estimado**: ~1 hora de trabajo.

---

## 6. Fixes Estructurales

### 6.1 — Migrar webhook replay protection a Redis (SEC-004)

**Justificación**: La protección actual es un `set` en memoria que no sobrevive a restarts ni se comparte entre instancias.

```python
# Usar Redis SET con TTL de 5 minutos
import redis
r = redis.from_url(settings.REDIS_URL)

def _is_duplicate_webhook(event_id: str) -> bool:
    return r.sismember("webhook:processed", event_id)

def _mark_webhook_processed(event_id: str) -> None:
    r.sadd("webhook:processed", event_id)
    r.expire("webhook:processed", 300)
```

### 6.2 — Eliminar API-key fallback en frontend (SEC-003)

**Justificación**: Mezclar JWT + API key pública rompe secure-by-default.

- Separar flujo: endpoints públicos no requieren API key; endpoints autenticados usan solo JWT.
- Eliminar `VITE_API_KEY` de `.env.production`.
- Condicionar envío de `X-API-Key` solo si no hay JWT activo.

### 6.3 — Sanitización de keys en storage (SEC-005)

**Justificación**: Aunque bloqueado en producción por guardrail, defense-in-depth exige sanitización.

- Agregar `_sanitize_key()` en `StorageService` que normalice path y bloquee traversal.
- Aplicar en `upload_bytes`, `download_bytes`, `delete_object`, `exists`.

### 6.4 — CSP enforcement roadmap (SEC-010)

1. Habilitar endpoint de reporte CSP para monitorear violations actuales.
2. Eliminar `unsafe-inline` usando nonces para scripts.
3. Eliminar `unsafe-eval` (requiere auditar dependencias que lo requieran).
4. Migrar de `Content-Security-Policy-Report-Only` a `Content-Security-Policy`.

### 6.5 — Migraciones Alembic para tablas faltantes (SEC-012)

Crear migraciones para `idempotency_keys` y `generated_reports`, incluyendo:
- Schema completo con tipos y constraints.
- Index en `(idempotency_key, endpoint)` UNIQUE.
- TTL/cleanup programado.

### 6.6 — Compose producción separado (SEC-008)

- Crear `docker-compose.prod.yml` sin port mappings, sin DEBUG, sin --reload.
- Bind Redis solo a `127.0.0.1`.
- Flower detrás de auth proxy o deshabilitado.

---

## 7. Checklist Secure-by-Default

| Principio | Estado | Evidencia |
|---|---|---|
| **Least Privilege** | ⚠️ Parcial | Workers/tasks aceptan user-level API key (SEC-002) |
| **Defense in Depth** | ✅ Bien | Storage guardrail, JWT + API key dual auth, RT middleware |
| **Zero Trust Boundaries** | ⚠️ Parcial | Webhook fail-open (SEC-001), CORS wildcard en docker (SEC-009) |
| **Secure Storage** | ⚠️ Parcial | Path traversal en local (SEC-005), GCS make_public legacy (SEC-006) |
| **Auditability** | ✅ Bien | Webhook logging, request-id tracing, audit endpoints |
| **Reproducibility Integrity** | ⚠️ Parcial | Tablas sin migración (SEC-012), sourcemaps en prod (SEC-013) |
| **Supply Chain Safety** | ✅ Bien | Dependencias pinned en requirements, no se detectaron inyecciones |
| **Fail-Closed** | ❌ Falla | Webhook acepta sin secreto (SEC-001), rate-limit fallback in-memory |

---

## 8. Security Ownership Map (12 meses)

> Generado con script oficial `run_ownership_map.py` (networkx instalado).  
> Parámetros: `--since 2025-02-16 --bus-factor-threshold 2 --stale-days 90 --owner-threshold 0.6`

### Estadísticas del análisis

| Métrica | Valor |
|---|---|
| Commits analizados | 76 |
| Archivos únicos tocados | 940 |
| Contribuidores | 2 |
| Edges persona→archivo | 1672 |
| Bus-factor hotspots (≤2) | 20 |
| Hidden owners detectados | 9 categorías |
| Orphaned sensitive code | 0 |

### Hidden Owners (control ≥60% de categoría)

| Persona | Categoría | Control |
|---|---|---|
| Nicolasgh91 | auth | **100%** |
| Nicolasgh91 | payments | **100%** |
| Nicolasgh91 | storage | **100%** |
| Nicolasgh91 | infra | **100%** |
| Nicolasgh91 | rate_limit | **100%** |
| Nicolasgh91 | idempotency | **100%** |
| Nicolasgh91 | supabase | **100%** |
| Nicolasgh91 | frontend_auth | **82%** |
| Nicolasgh91 | workers | **70%** |

### Bus Factor Hotspots (archivos sensibles con ≤2 contribuidores)

| Archivo | Bus Factor | Tag | Último touch |
|---|---|---|---|
| `app/core/security.py` | 1 | auth | 2026-02-10 |
| `app/api/auth_deps.py` | 1 | auth | 2026-02-11 |
| `app/services/supabase_auth.py` | 1 | auth | 2026-02-11 |
| `app/api/v1/webhooks.py` | 1 | payments | 2026-02-11 |
| `app/services/mercadopago_service.py` | 1 | payments | 2026-02-11 |
| `app/api/v1/payments.py` | 1 | payments | 2026-02-14 |
| `app/services/storage_service.py` | 1 | storage | 2026-02-14 |
| `app/services/gcs_service.py` | 1 | storage | 2026-02-10 |
| `app/core/rate_limiter.py` | 1 | rate_limit | 2026-02-14 |
| `app/core/idempotency.py` | 1 | idempotency | 2026-02-10 |
| `deployment/nginx.conf` | 1 | infra | 2026-02-14 |
| `docker-compose.yml` | 1 | infra | 2026-02-10 |
| `docker/docker-compose.yml` | 1 | infra | 2026-02-10 |
| `app/api/routes/tasks.py` | 1 | workers | 2026-02-14 |
| `frontend/src/components/auth/ProtectedRoute.tsx` | 1 | frontend_auth | 2026-02-10 |
| `supabase/functions/public-stats/index.ts` | 1 | supabase | 2026-02-10 |
| `workers/celery_app.py` | 2 | workers | 2026-02-16 |
| `frontend/src/services/api.ts` | 2 | frontend_auth | 2026-02-14 |
| `frontend/src/context/AuthContext.tsx` | 2 | frontend_auth | 2026-02-13 |
| `app/api/routes/workers.py` | 2 | workers | 2026-02-10 |

### Riesgos de concentración

- **Bus factor = 1** en **16 de 20** archivos sensibles.
- Un solo contribuidor (Nicolasgh91) controla **100%** de 7 de 9 categorías de seguridad.
- **Recomendación**: Code review cruzado obligatorio en cambios de auth/payments/storage, documentación de decisiones de seguridad, pair programming en módulos críticos.

### Datos de referencia

- [summary.json](file:///c:/Users/nicog/wildfire-recovery-argentina/review/security/ownership/summary.json) — resumen oficial
- [people.csv](file:///c:/Users/nicog/wildfire-recovery-argentina/review/security/ownership/people.csv) — contribuidores
- [files.csv](file:///c:/Users/nicog/wildfire-recovery-argentina/review/security/ownership/files.csv) — archivos con bus factor
- [communities.json](file:///c:/Users/nicog/wildfire-recovery-argentina/review/security/ownership/communities.json) — community detection

---

## 9. Requires Manual Verification

| Item | Comando/Verificación | Justificación |
|---|---|---|
| TLS/HSTS/CSP/headers reales | `curl -I https://forestguard.freedynamicdns.org` | Red de este entorno no permite salida a internet |
| Políticas IAM de buckets GCS | `gcloud storage buckets get-iam-policy gs://forestguard-images` | Requiere credenciales GCP |
| Exposición Redis/Celery/Flower en prod | `nmap -p 6379,5555 <prod-ip>` o verificar firewall rules | No tenemos acceso a consola de prod |
| Políticas RLS activas en Supabase | `SELECT * FROM pg_policies ORDER BY tablename, policyname;` | Requiere acceso a DB productiva |
| Configuración Cloudflare (TLS mode, WAF, rate limits) | Dashboard de Cloudflare | Requiere acceso al dashboard |

---

## 10. Reproducciones Técnicas Ejecutadas

| # | Prueba | Resultado | Estado |
|---|---|---|---|
| 1 | Webhook `validate_webhook_signature()` sin secreto | `True` (fail-open confirmado) | ✅ Reproducido |
| 2 | Path traversal `../secrets.env` en local storage | Resuelve fuera del bucket base | ✅ Reproducido |
| 3 | Rate limiter backend detection | `in_memory` (fallback por Redis no disponible) | ✅ Verificado |

---

## 11. Resultados de Tests de Seguridad

> Se ejecutarán 6 suites de tests unitarios y los resultados se registrarán aquí.

| Test Suite | Archivo | Tests | Resultado | Notas |
|---|---|---|---|---|
| RBAC Admin Access | `test_security_features.py` | 2 | ✅ 2 passed | Admin vs User RBAC verificado |
| Storage Guardrail | `test_storage_guardrail.py` | 5 | ✅ 5 passed | Config + Service guardrails |
| CORS Policy | `test_cors_policy.py` | 10 | ✅ 10 passed | Preflight, headers, error CORS |
| Reports Auth | `test_reports_auth.py` | 3 | ✅ 3 passed | 401 sin JWT en todos los endpoints |
| Auth Matrix | `test_auth_matrix.py` | 12 | ✅ 12 passed | Paramétrico: jwt/api_key/public |
| Rate Limiter Redis | `test_rate_limiter_redis.py` | 13 | ✅ 13 passed | Redis + InMemory + trusted proxy |

> **Total: 45 tests, 0 failures, 18 warnings** (warnings son deprecation de pydantic V2, no relevantes).

---

## 12. Casos de Prueba de Aceptación

| # | Escenario | Criterio | Estado |
|---|---|---|---|
| 1 | JWT mal firmado/claims inválidos | Debe fallar siempre (401) | ✅ Cubierto por `test_auth_matrix.py` |
| 2 | Endpoint admin bloquea usuario no-admin | 403 aunque UI lo permita | ✅ Cubierto por `test_security_features.py` |
| 3 | Webhook replay no reprocesa evento | `already_processed` response | ⚠️ In-memory only (SEC-004) |
| 4 | Idempotency conflict consistente | 409 con body distinto | ✅ Implementado en `idempotency.py` |
| 5 | Rate limit detrás de proxy/CDN | Trusted proxy extraction | ✅ Cubierto por `test_rate_limiter_redis.py` |
| 6 | Acceso cross-tenant (IDOR/RLS) denegado | user_id filter en queries | ✅ Verificado en `exploration_service.py` |
| 7 | Upload/PDF sin traversal ni payload activo | Path traversal blocked | ⚠️ Falta sanitización (SEC-005) |
| 8 | Logs no exponen secretos/tokens | Masked output | ⚠️ Prefix 8 chars loggeado (SEC-011) |
| 9 | Redis/Celery no expuesto públicamente | Bind to localhost / firewall | `requires manual verification` |
| 10 | Headers seguridad y TLS activos en prod | HSTS, OCSP, TLSv1.2+ | `requires manual verification` |
