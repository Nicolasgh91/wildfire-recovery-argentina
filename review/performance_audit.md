# Performance Audit (MVP publicable)

Fecha: 2026-02-14

## Resumen ejecutivo

- Hallazgos backend/db: 6
- Hallazgos frontend: 5
- Quick wins aplicables sin rediseño mayor: 6
- Cambios aplicados en esta ejecución: 0 de performance estructural (solo documentación + seguridad de logging)

---

## Backend / DB

### ID: PERF-001
**Severidad:** media  
**Área:** backend/db  
**Evidencia:** `app/api/v1/fires.py#L163-L165` (`page_size` sin hard cap explícito en endpoint de listado principal)  
**Riesgo:** Requests con `page_size` elevado pueden inflar tiempos de respuesta y memoria serializando listas grandes.  
**Recomendación:** Agregar `le` (ej. 100 o 200) en `page_size` del endpoint `/fires`; mantener consistencia con otros endpoints paginados.  
**Estado:** pendiente

### ID: PERF-002
**Severidad:** media  
**Área:** backend/db  
**Evidencia:** `app/api/v1/payments.py#L385-L398` (count + select paginado por usuario)  
**Riesgo:** Para usuarios con historial grande, `COUNT(*)` en cada request degrada latencia y carga de DB.  
**Recomendación:** 1) índice compuesto `(user_id, created_at DESC)` en `credit_transactions`; 2) cursor pagination para páginas profundas; 3) count opcional/estimado.  
**Estado:** pendiente

### ID: PERF-003
**Severidad:** media  
**Área:** backend/db  
**Evidencia:** `app/api/v1/audit.py#L371-L521` (`/audit/search` combina búsquedas por provincia/área/geocoding y geoespacial)  
**Riesgo:** Endpoint con rutas de ejecución costosas (ILIKE + geocoding externo + ST_DWithin/ST_Intersects) puede degradar bajo carga concurrente.  
**Recomendación:** 1) cachear resultados de geocoding por TTL; 2) índice geoespacial validado para campos usados; 3) circuito de timeout por proveedor externo.  
**Estado:** pendiente

### ID: PERF-004
**Severidad:** baja  
**Área:** backend  
**Evidencia:** `app/core/rate_limiter.py#L54-L65` y almacenamiento en memoria global  
**Riesgo:** Escalado horizontal rompe uniformidad del limitador y agrega overhead de cálculos duplicados por instancia.  
**Recomendación:** Migrar a Redis/shared store para limitar CPU y mejorar consistencia.  
**Estado:** pendiente

### ID: PERF-005
**Severidad:** media  
**Área:** backend/infra  
**Evidencia:** `frontend/src/services/api.ts#L183-L188` reintentos automáticos para cualquier endpoint con códigos retryables  
**Riesgo:** Reintentos sobre endpoints costosos (o no idempotentes) amplifican carga y latencia en incidentes.  
**Recomendación:** Limitar retry a métodos idempotentes (`GET`, opcional `HEAD`) o a endpoints explícitamente seguros.  
**Estado:** pendiente

### ID: PERF-006
**Severidad:** baja  
**Área:** backend/db  
**Evidencia:** `app/api/v1/fires.py#L260-L349` (`/fires/export` sync/async según volumen)  
**Riesgo:** Exportes grandes simultáneos generan presión de I/O y serialización, afectando endpoints interactivos.  
**Recomendación:** Forzar cola async para >N registros más bajo, con bucket de trabajo separado y límite de concurrencia por usuario.  
**Estado:** pendiente

---

## Frontend

### ID: PERF-007
**Severidad:** media  
**Área:** frontend  
**Evidencia:** `frontend/src/services/api.ts#L183-L188` (retry genérico a nivel cliente)  
**Riesgo:** Re-fetch masivo en fallback de red puede empeorar UX (toasts/reintentos) y aumentar consumo en mobile.  
**Recomendación:** Acotar retries por endpoint y definir backoff con jitter + cancelación al desmontar.  
**Estado:** pendiente

### ID: PERF-008
**Severidad:** media  
**Área:** frontend  
**Evidencia:** `frontend/src/App.tsx#L13-L32` (muchas páginas lazy, positivo) + dependencia de páginas con mapas/charts potencialmente pesadas  
**Riesgo:** Sin budget de bundle y sin trazas de chunks, puede haber regresiones de TTI en rutas con mapas/reportes.  
**Recomendación:** Medir bundle (`vite build --analyze`), fijar budgets y dividir aún más módulos de mapas/reportes si supera umbrales.  
**Estado:** pendiente

### ID: PERF-009
**Severidad:** media  
**Área:** frontend  
**Evidencia:** `frontend/README.md` indica uso de Leaflet + heatmap WebGL y listados históricos con paginación server-side  
**Riesgo:** Render de muchos marcadores sin cluster/virtualización puede bloquear main thread en equipos medios.  
**Recomendación:** Asegurar clustering por zoom, memo de capas y throttling de actualizaciones al mover mapa.  
**Estado:** pendiente

### ID: PERF-010
**Severidad:** baja  
**Área:** frontend  
**Evidencia:** rutas `/fires/history` y `/map` con alto volumen visual, sin evidencia en docs de virtualización en listas largas (roadmap lo sugiere)  
**Riesgo:** Scroll/rerender subóptimo con datasets altos.  
**Recomendación:** virtualizar filas de historial para >100 items y usar keys estables para evitar rerenders completos.  
**Estado:** pendiente

### ID: PERF-011
**Severidad:** baja  
**Área:** frontend  
**Evidencia:** no se documenta estrategia de imágenes lazy en páginas de detalle/reportes  
**Riesgo:** Descarga temprana de assets grandes impacta LCP y consumo de red.  
**Recomendación:** lazy loading + tamaños responsivos + formato optimizado para previews.  
**Estado:** pendiente

---

## Quick wins priorizados

1. **QW-01 (1-2h):** hard cap explícito de `page_size` en `/fires` (PERF-001).
2. **QW-02 (2-4h):** índice `(user_id, created_at DESC)` en transacciones + validación EXPLAIN (PERF-002).
3. **QW-03 (2-3h):** limitar retries frontend a métodos idempotentes (PERF-005/PERF-007).
4. **QW-04 (3-5h):** cache TTL de geocoding en `/audit/search` (PERF-003).
5. **QW-05 (2-4h):** presupuesto de bundle y reporte automático en CI (PERF-008).
6. **QW-06 (3-6h):** clusterización/optimización de capas en mapa para datasets grandes (PERF-009).

---

## Métrica mínima recomendada (antes/después)

- P95 latency: `/api/v1/fires`, `/api/v1/fires/stats`, `/api/v1/audit/search`.
- DB: tiempo de `COUNT` y query principal de transacciones.
- Frontend: tamaño de bundle inicial y TTI de `/map` y `/fires/history`.
- Error budget: tasa de 429/5xx y retries por sesión.
