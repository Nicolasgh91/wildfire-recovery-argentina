# ForestGuard Go-Live Status Report

**Generated**: 2026-02-10T12:20:38-03:00  
**Last validated**: 2026-02-10T12:20:38-03:00

---

## Snapshot del repositorio

- Branch: `main`
- Working tree: `DIRTY` (hay cambios locales pendientes)
- Estado de release-candidate: **NO APTO** hasta congelar commit limpio

---

## Validacion contra codigo (fuente de verdad)

### Feature flags

- Backend:
  - `FEATURE_CERTIFICATES` y `FEATURE_REFUGES` definidos en `app/core/config.py`.
  - Bloqueo por dependency `require_feature(...)` en `app/core/feature_flags.py`.
  - Routers protegidos en `app/main.py` (`/certificates`, `/visitor-logs`, `/shelters`).
- Frontend:
  - Helper `isFeatureEnabled(...)` en `frontend/src/lib/featureFlags.ts`.
  - Route guards para `/certificates` y `/shelters` en `frontend/src/App.tsx`.
  - Navbar condicional en `frontend/src/components/layout/navbar.tsx`.

### Health checks

- Endpoints implementados:
  - `/health`
  - `/api/v1/health/db`
  - `/api/v1/health/celery`
  - `/api/v1/health/gee`
- Implementacion verificada en `app/api/routes/health.py`.

### Scripts de validacion

- Backend smoke: `scripts/go_live_smoke.ps1`
- UI smoke: `scripts/ui_smoke.ps1`
- GCS diag: `scripts/test_gcs_conn.py`

---

## Evidencia ejecutada en esta sesion

### 1. Backend smoke (`scripts/go_live_smoke.ps1`)

Resultado:
- Critical checks: **7/7 PASSED**
- Failed: `0`
- Warnings: `1` (GCS opcional no validado localmente)
- Exit code: `0`

Detalle validado:
- `GET /health` -> 200
- `GET /api/v1/health/db` -> 200
- `GET /api/v1/health/celery` -> 200
- `GET /api/v1/health/gee` -> 200
- Feature flags bloquean:
  - `/api/v1/certificates/verify/test` -> 404
  - `/api/v1/visitor-logs` -> 404
  - `/api/v1/shelters` -> 404

### 2. UI smoke (`scripts/ui_smoke.ps1`)

Resultado:
- Playwright: **6 passed**
- Exit code: `0`

Cobertura:
- `frontend/tests/ui/verify-land.spec.ts`
- `frontend/tests/ui/exploration.spec.ts`

### 3. Suites de respaldo ejecutadas

- `pytest tests/unit/test_contact.py` -> `4 passed`
- `pytest tests/e2e/test_critical_flows.py::test_contact_flow_e2e` -> `1 passed`
- `pytest tests/integration/test_imagery_refresh.py tests/unit/test_carousel_task.py` -> `3 passed`
- `pytest tests/integration/test_judicial_reports.py tests/integration/test_reports_verify.py tests/integration/test_historical_reports_ucf11.py` -> `7 passed, 2 skipped`
- `pytest tests/unit/test_quality_service.py tests/integration/test_audit_legal.py` -> `3 passed, 1 skipped`
- `pytest tests/unit/test_recurrence_service.py` -> `1 passed`
- `pytest tests/integration/test_historical_reports.py -k VAE` -> `1 passed`

Notas:
- Skips observados son esperados por entorno (`RUN_PROD_READONLY_TESTS` no habilitado o dataset variable).

### 4. GCS diagnostico directo (`python scripts/test_gcs_conn.py`)

Resultado:
- Exit code: `0`
- Estado local: `VALIDADO`

Observado:
- Buckets `images/reports/certificates` en `PASS` (3/3).
- Evidencia: `artifacts/gcs_conn_report.json`.

### 5. UC-F02 target env (`python scripts/validate_uc_f02.py`)

Resultado:
- Exit code: `0`
- Checks: `14/14 PASS`

Detalle validado:
- Edge function `public-stats` responde 200 en rango valido.
- Cache headers presentes (`s-maxage`, `stale-while-revalidate`, `stale-if-error`).
- Validaciones de input responden 400.
- Sin acceso anonimo directo a `fire_events`, `fire_detections`, `fire_stats` (401).
- RLS activo en `fire_events` y `fire_detections`.
- RPC `api.get_public_stats` existe, `SECURITY DEFINER`, execute para anon.
- Evidencia: `artifacts/uc_f02_validation_report.json`.

### 6. ASYNC_GCS checklist tecnico (workers + idempotencia)

Resultado:
- Celery worker conectado a Redis (`inspect ping` -> `pong`).
- `debug_task` consumida con exito.
- Idempotencia/rate-limit cubiertos en integracion:
  - `pytest tests/integration/test_reports_verify.py tests/integration/test_judicial_reports.py -q` -> `5 passed, 1 skipped`.
- Flujos async de soporte:
  - `pytest tests/integration/test_imagery_refresh.py tests/unit/test_carousel_task.py tests/unit/test_closure_report_service.py tests/unit/test_clustering_service.py -q` -> `6 passed`.

---

## Decision de readiness (por perfil)

### Perfil `MVP_CORE`

Estado: **GO CONDICIONAL**

Condiciones para GO real:
1. Mantener UC-F07 y UC-F10 bloqueadas por flags.
2. Mantener fuera de release los CU fuera de perfil.
3. Congelar commit limpio (working tree sin cambios).

### Perfil `ASYNC_GCS` (incluye UC-F08/F09/F11/F13 o workers/GCS activos)

Estado: **GO CONDICIONAL**

Condiciones para GO real:
1. Mantener commit limpio y congelar release reproducible.
2. Si se habilitan UC-F08/F09/F13, adjuntar evidencia funcional final en entorno objetivo (corrida real por caso).

---

## Conclusiones

1. La base `MVP_CORE` se mantiene validada tecnicamente por smoke backend + smoke UI + pruebas de respaldo.
2. UC-F02 y el checklist tecnico `ASYNC_GCS` (GCS + Celery + idempotencia) quedaron cerrados en esta sesion.
3. Antes de deploy, resolver higiene de release: branch/commit limpio y reproducible.
4. Para UC-F08/F09/F13, la habilitacion productiva requiere evidencia funcional final por caso.
