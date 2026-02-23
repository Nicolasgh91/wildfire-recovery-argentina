# Backlog Recommendations

Formato: prioridad, estimación rápida, alcance y criterio de cierre.

## P0 (urgente)

### BL-001 - Endurecer auth en endpoints de reportes
- **Prioridad:** P0
- **Estimación:** 4-6h
- **Área:** backend
- **Contexto:** `/api/v1/reports/*` aparece público en el estado MVP actual; alto riesgo de consumo indebido.
- **Tarea:** aplicar dependencia JWT/API key explícita por endpoint + tests de autorización.
- **Done cuando:** llamadas sin credenciales devuelven 401/403 y tests cubren rutas críticas.

### BL-002 - Rate limiting distribuido (Redis/gateway)
- **Prioridad:** P0
- **Estimación:** 1-2 días
- **Área:** backend/infra
- **Contexto:** limitador en memoria no escala de forma segura en multi-réplica.
- **Tarea:** mover contadores/bloqueos a Redis con TTL y llaves por endpoint/IP/user.
- **Done cuando:** límites consistentes en despliegue con >1 instancia y métricas de rechazo observables.

### BL-003 - Guardrail de storage en producción
- **Prioridad:** P0
- **Estimación:** 2-4h
- **Área:** infra
- **Contexto:** `STORAGE_BACKEND` permite `local`; riesgo de configuración accidental en prod.
- **Tarea:** fail-fast en startup si `ENVIRONMENT=production` y backend local.
- **Done cuando:** el servicio no inicia con configuración insegura y el motivo queda logueado.

## P1 (alta)

### BL-004 - Política CORS estricta por ambiente
- **Prioridad:** P1
- **Estimación:** 3-5h
- **Área:** backend
- **Contexto:** `allow_methods` y `allow_headers` en wildcard.
- **Tarea:** restringir a métodos/headers usados y agregar test de cabeceras CORS.
- **Done cuando:** preflight permitido solo para combinación esperada de origen/método/header.

### BL-005 - Hard cap explícito de paginación en `/fires`
- **Prioridad:** P1
- **Estimación:** 1-2h
- **Área:** backend/performance
- **Contexto:** `page_size` sin tope explícito en endpoint principal.
- **Tarea:** agregar `le` en Query + test de validación 422 para valores excedidos.
- **Done cuando:** endpoint rechaza tamaños fuera de rango y docs reflejan el límite.

### BL-006 - Índice y estrategia de paginación en transacciones
- **Prioridad:** P1
- **Estimación:** 4-8h
- **Área:** db/performance
- **Contexto:** query de historial con `count + offset` puede degradar con volumen.
- **Tarea:** índice `(user_id, created_at DESC)` y evaluar cursor pagination.
- **Done cuando:** mejora medible en p95 y plan de ejecución del query.

### BL-007 - Pipeline de seguridad en CI
- **Prioridad:** P1
- **Estimación:** 1 día
- **Área:** infra/ci-cd
- **Contexto:** falta gate automático para secretos, dependencias y auth contracts.
- **Tarea:** integrar secret scan + dependency audit + test suite de auth.
- **Done cuando:** merge bloqueado ante hallazgos de severidad configurable.

## P2 (media)

### BL-008 - Sanitización de logs transversal
- **Prioridad:** P2
- **Estimación:** 1 día
- **Área:** backend/observabilidad
- **Contexto:** se mitigó contacto, pero falta política uniforme global.
- **Tarea:** middleware/filtro de logging para redacción de PII/tokens/IP sensible.
- **Done cuando:** casos de prueba demuestran redacción consistente en logs estructurados.

### BL-009 - Cache de geocoding y resultados de búsqueda audit
- **Prioridad:** P2
- **Estimación:** 6-10h
- **Área:** backend/performance
- **Contexto:** `/audit/search` combina DB + proveedor externo, potencial cuello de botella.
- **Tarea:** cache TTL por consulta normalizada y política de invalidación.
- **Done cuando:** hit ratio razonable y reducción de latencia p95 del endpoint.

### BL-010 - Presupuesto de bundle y trazabilidad de chunks
- **Prioridad:** P2
- **Estimación:** 4-6h
- **Área:** frontend/performance
- **Contexto:** uso intensivo de mapas/charts sin budget formal.
- **Tarea:** incorporar análisis de bundle en CI y umbrales por ruta crítica.
- **Done cuando:** build falla al exceder budget y se emite reporte por chunk.

## P3 (baja)

### BL-011 - Consolidar fuente canónica de documentación
- **Prioridad:** P3
- **Estimación:** 4-8h
- **Área:** docs
- **Contexto:** múltiples roadmaps y documentos con estado heterogéneo.
- **Tarea:** definir un índice maestro de docs (arquitectura, API, frontend, runbooks, roadmap).
- **Done cuando:** existe una única ruta de lectura recomendada para onboarding/auditoría.

### BL-012 - Matriz pública de requisitos de auth por endpoint
- **Prioridad:** P3
- **Estimación:** 3-5h
- **Área:** docs/backend
- **Contexto:** reglas de auth distribuidas en routers y middlewares.
- **Tarea:** generar tabla endpoint -> público/api key/jwt/admin y validarla con tests.
- **Done cuando:** tabla y tests permanecen sincronizados en CI.
