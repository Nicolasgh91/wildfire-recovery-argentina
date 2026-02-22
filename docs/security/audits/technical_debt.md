# Security Audit — Technical Debt

## TD-001: GraphML export fails with networkx
- **Timestamp**: 2026-02-16T11:50:00-03:00
- **Task**: Ownership Map (Official Script)
- **Error**: `ValueError: networkx does not support <class 'list'> as data values` during GraphML serialization
- **Hypothesis**: `bus_factor_hotspots` contains list-typed node attributes that GraphML cannot serialize
- **Workaround**: Ran without `--graphml` flag; `ownership.graphml` generated via co-change graph only
- **Fix**: Patch `build_ownership_map.py` to serialize list attributes as JSON strings before GraphML export
- **Priority**: Low (graphml is optional output)

## TD-002: External validation — No HSTS/CSP headers on root domain
- **Timestamp**: 2026-02-16T11:52:00-03:00
- **Task**: External Validation
- **Observation**: `curl -I https://forestguard.freedynamicdns.org` returns HTTP 200 from nginx/1.25.5 but **no** `Strict-Transport-Security`, `Content-Security-Policy`, or `X-Content-Type-Options` headers
- **Hypothesis**: The response is serving a static landing page on port 80/443 that is NOT the production API deployment. The `deployment/nginx.conf` with security headers may not be active on this host, or the domain is serving a different VHost.
- **Workaround**: Documented as "requires manual verification" in final report
- **Fix**: Verify nginx configuration on the production host matches `deployment/nginx.conf`; confirm Cloudflare is proxying with appropriate edge security settings
- **Priority**: Medium (security headers must be active in production)

## TD-003: CSV header incompatibility with ownership script
- **Timestamp**: 2026-02-16T11:48:00-03:00
- **Task**: Ownership Map (Official Script)
- **Error**: `ValueError: could not convert string to float: 'weight'`
- **Hypothesis**: `load_sensitive_rules()` skips empty lines and `#` comments but not CSV headers
- **Workaround**: Prefixed header row with `#` in `sensitive_paths.csv`
- **Fix**: Update `load_sensitive_rules()` to skip first row if it matches header pattern, or use `csv.DictReader`
- **Priority**: Low (one-time fix applied)

## TD-004: Rate limiter backend fallback to in_memory
- **Timestamp**: 2026-02-16T11:30:00-03:00
- **Task**: Security Tests Execution
- **Observation**: Local tests confirm rate limiter falls back to `in_memory` when Redis is not available
- **Hypothesis**: This is by design for dev environments, but must not happen in production
- **Workaround**: Documented in final report as SEC-004 relationship
- **Fix**: Add startup check that fails if `ENVIRONMENT=production` and Redis is unreachable
- **Priority**: Medium

## TD-005: Pydantic V2 deprecation warnings in test suite
- **Timestamp**: 2026-02-16T11:45:00-03:00
- **Task**: Security Tests Execution
- **Observation**: 18 deprecation warnings across all 6 test suites related to Pydantic V2 migration
- **Hypothesis**: Models still using V1-style validators or field definitions
- **Workaround**: None needed — tests pass correctly
- **Fix**: Migrate to Pydantic V2 validator syntax
- **Priority**: Low

Fase adicional: Validación de controles positivos

Para cada superficie crítica, confirmar explícitamente:
- Qué control existe
- Cómo se prueba que funciona
- Qué test manual o automatizado lo verifica

Ejemplo: Rate Limiter

Superficie: Rate Limiting (SEC-004)

Control existente: RateLimiter class con Redis backend por defecto, fallback a in_memory

Prueba de funcionamiento:

Test unitario: tests/unit/test_rate_limiter_redis.py (12 tests, pasan correctamente)

Test integración: tests/integration/test_rate_limiter_integration.py (4 tests, pasan correctamente)

Test manual: curl -I http://localhost:8000/api/v1/reports/ -H "X-Forwarded-For: [IP_ADDRESS]" (debe retornar 429 después de 100 requests)

Estado: Control implementado y testeado localmente. No se validó en producción.

Financial integrity tests:
- double-spend de créditos
- race condition en decremento
- pago confirmado sin verificación webhook
- reenvío manual de webhook válido
- modificación de monto en frontend

Fase específica: Abuse económico / resource exhaustion

Simular:
- export 10k repetido
- heatmap con bounding box gigante
- exploraciones simultáneas
- generación masiva de PDFs
- abuse de endpoints públicos cacheables

Test concurrente con 10 requests simultáneos
misma key
verificar atomicidad real

Dependency security audit:
- backend: pip list --outdated
- frontend: npm audit --production
- revisar CVEs críticas
- revisar transitive deps

Propuesta de ejecución:

1. Threat model
2. Backend auth + payments (primero)
3. Idempotencia + créditos
4. RLS + IDOR
5. Infra real en dominio productivo
6. Luego frontend