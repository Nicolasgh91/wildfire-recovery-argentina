# Tablero Go-Live por Caso de Uso

> Fuente de verdad operativa para decision GO/NO GO.
> Validado contra codigo y tests el **2026-02-10**.
> Se usa junto con:
> - `docs/v2/10-go-live/3_checklist_go_live.md`
> - `docs/v2/10-go-live/GO_LIVE_RUNBOOK.md`

Leyenda:
- `VERDE`: implementado y validado para el perfil de salida.
- `AMARILLO`: implementado, pero requiere controles/evidencia adicional.
- `ROJO`: no habilitar en esta release.
- `N/A`: fuera de alcance del perfil.

---

## Estado por UC (codigo + pruebas)

| UC | Estado | Decision go-live | Evidencia en codigo/tests | Pendiente real |
|---|---|---|---|---|
| UC-F01 Contacto | VERDE | Habilitable | `app/api/v1/contact.py`, `app/core/rate_limiter.py`, `tests/unit/test_contact.py`, `tests/e2e/test_critical_flows.py::test_contact_flow_e2e` | SMTP y observabilidad en entorno objetivo |
| UC-F02 Stats publicas | VERDE | Habilitable (no bloquea MVP_CORE) | `supabase/functions/public-stats/index.ts`, `tests/integration/test_public_stats.py`, `scripts/validate_uc_f02.py` | Sin bloqueantes tecnicos abiertos; mantener monitoreo operativo de egress/rate limit |
| UC-F03 Historico | AMARILLO | Habilitable | `app/api/v1/fires.py`, `tests/e2e/test_fires_uc13.py` | Evidencia de performance en entorno objetivo |
| UC-F04 Calidad dato | VERDE | Habilitable | `app/api/v1/quality.py`, `tests/unit/test_quality_service.py` | Solo seguimiento operativo |
| UC-F05 Recurrencia/KPIs | AMARILLO | Condicional | `app/api/v1/analysis.py`, `tests/unit/test_recurrence_service.py` | Smoke readonly productivo + evidencia de carga geoespacial |
| UC-F06 Auditoria suelo | VERDE | Habilitable | `app/api/v1/audit.py`, `frontend/tests/ui/verify-land.spec.ts`, `tests/integration/test_audit_legal.py` | Mantener API key y rate limit activos en deploy |
| UC-F07 Refugios | N/A | Fuera de MVP | Feature flag activo | Excluido por decision de producto |
| UC-F08 Carrusel satelital | AMARILLO | Condicional `ASYNC_GCS` | `app/api/v1/imagery.py`, `tests/integration/test_imagery_refresh.py`, `tests/unit/test_carousel_task.py` | Falta corrida funcional real de refresh y evidencia de `slides_data` en entorno objetivo |
| UC-F09 Reporte cierre | AMARILLO | Condicional `ASYNC_GCS` | `app/services/closure_report_service.py`, `tests/unit/test_closure_report_service.py` | Falta corrida funcional real de cierre y evidencia de retention/lifecycle en entorno objetivo |
| UC-F10 Certificados | N/A | Fuera de MVP | Feature flag activo | Excluido por decision de producto |
| UC-F11 Reportes especializados | AMARILLO | Condicional `ASYNC_GCS` | `app/api/routes/reports.py`, `app/api/v1/explorations.py`, `tests/integration/test_judicial_reports.py`, `tests/integration/test_reports_verify.py`, `frontend/tests/ui/exploration.spec.ts` | Checklist tecnico `ASYNC_GCS` validado; falta evidencia funcional final de negocio si se habilita |
| UC-F12 VAE recuperacion | AMARILLO | No habilitar en MVP_CORE | `app/services/vae_service.py`, `app/api/routes/monitoring.py`, `tests/integration/test_historical_reports.py -k VAE` | Definir criterio de producto para release + hardening/performance especifico |
| UC-F13 Clustering macro | AMARILLO | Condicional `ASYNC_GCS` | `app/services/clustering_service.py`, `workers/tasks/clustering_task.py`, `tests/unit/test_clustering_service.py` | Falta corrida funcional programada del pipeline y evidencia de monitoreo en entorno objetivo |

---

## Requisitos tecnicos por bloque

### Bloque A: `MVP_CORE` (siempre bloqueante)

- Salud API: `/health`, `/api/v1/health/db`, `/api/v1/health/celery`, `/api/v1/health/gee`.
- Flags MVP:
  - Backend: 404 en `/api/v1/certificates/*`, `/api/v1/visitor-logs`, `/api/v1/shelters`.
  - Frontend: 404 en `/certificates` y `/shelters`.
- UC-F03, UC-F04 y UC-F06 operativas.
- Smoke scripts:
  - `scripts/go_live_smoke.ps1`
  - `scripts/ui_smoke.ps1` (si frontend forma parte del release)

### Bloque B: `ASYNC_GCS` (bloqueante condicional)

Se activa si:
- se habilita UC-F08, UC-F09, UC-F11 o UC-F13, o
- hay workers activos en produccion, o
- `STORAGE_BACKEND=gcs` en entorno objetivo.

Checks:
- `python scripts/test_gcs_conn.py` con 3/3 buckets en pass.
- Workers Celery levantan y consumen tareas.
- Idempotencia y rate limit de endpoints criticos verificados.
- Ultima evidencia (2026-02-10):
  - `artifacts/gcs_conn_report.json` -> `3/3` buckets pass.
  - Celery `inspect ping` -> `pong` y `debug_task` consumida.
  - `pytest tests/integration/test_reports_verify.py tests/integration/test_judicial_reports.py` -> `5 passed, 1 skipped`.

---

## Plan de accion por CU pendiente (sin UC-F07 y UC-F10)

1. UC-F02 (COMPLETADO 2026-02-10)
   - Edge function `public-stats` validada en endpoint objetivo.
   - RLS/anon/cache/RPC validados con `scripts/validate_uc_f02.py`.
2. UC-F05
   - Correr smoke readonly con `RUN_PROD_READONLY_TESTS=1`.
   - Adjuntar evidencia de latencia/carga geoespacial.
3. UC-F08
   - Ejecutar worker real de refresh.
   - Verificar actualizacion de `slides_data` y objetos en storage.
4. UC-F09
   - Ejecutar task de closure report en evento de prueba.
   - Verificar idempotencia y lifecycle de artefactos.
5. UC-F11
   - Validar cola asincrona end-to-end con GCS y Celery.
   - Confirmar idempotencia en POST criticos en entorno objetivo.
6. UC-F12
   - Definir si entra en release (hoy: fuera de MVP_CORE).
   - Si se habilita: agregar smoke dedicado y criterio de capacidad.
7. UC-F13
   - Ejecutar pipeline de clustering programado.
   - Medir estabilidad, tiempos y trazabilidad N:M.

---

## Criterio final de go-live

### Perfil `MVP_CORE`

Puede salir a produccion si:
1. UC-F03, UC-F04 y UC-F06 pasan evidencias minimas.
2. UC fuera de perfil se mantienen bloqueadas por flags o no publicadas.
3. Commit de release queda limpio y reproducible.

### Perfil `ASYNC_GCS`

Puede salir a produccion si:
1. Cumple todo `MVP_CORE`.
2. GCS esta operativo (3/3 buckets).
3. Celery/colas estan operativas, sin acumulacion.
4. UC-F08/F09/F11/F13 tienen evidencia de ejecucion real.
