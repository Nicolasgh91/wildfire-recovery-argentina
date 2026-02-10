# ForestGuard Go-Live Runbook

## Proposito

Runbook operativo para validar readiness antes de despliegue.
Este documento unifica criterios con:
- `docs/v2/10-go-live/3_checklist_go_live.md`
- `docs/v2/10-go-live/2_tech_go_live_tasks.md`

---

## 1. Alcance del release

Definir perfil antes de ejecutar validaciones:

- `MVP_CORE`: UC-F03, UC-F04, UC-F06.
- `ASYNC_GCS`: incluye flujos asincronos o dependientes de GCS (ej. UC-F11).

Regla:
- `MVP_CORE`: GCS/Celery pueden ser warning.
- `ASYNC_GCS`: GCS/Celery son bloqueantes.

---

## 2. Prerrequisitos minimos

- Backend levantado en `http://localhost:8000`.
- `.env` cargado para backend.
- Frontend levantado en `http://localhost:5173` (si se valida UI).
- Entorno de release definido (commit/branch objetivo).

---

## 3. Validacion rapida (automatizada)

### 3.1 Smoke backend (siempre)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/go_live_smoke.ps1
```

Esperado:
- Exit code `0`.
- 7 checks criticos en verde.

### 3.2 Smoke UI (si frontend entra en release)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/ui_smoke.ps1
```

Esperado:
- Exit code `0`.
- Suite Playwright completa en verde.

---

## 4. Validacion manual por capas

### 4.1 Health endpoints

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health/db
curl http://localhost:8000/api/v1/health/celery
curl http://localhost:8000/api/v1/health/gee
```

Criterio:
- Todos deben responder HTTP 200.
- En `/api/v1/health/gee`, `degraded` es valido para `MVP_CORE`.

### 4.2 Feature flags (UI + API)

```powershell
curl -i http://localhost:8000/api/v1/certificates/verify/test
curl -i http://localhost:8000/api/v1/visitor-logs
curl -i http://localhost:8000/api/v1/shelters
```

Esperado:
- 404 en los tres endpoints con flags en `false`.

Frontend:
- `/certificates` -> 404.
- `/shelters` -> 404.
- Navbar sin links a Certificates/Shelters.

### 4.3 Use cases MVP_CORE

- UC-F03:
  - `GET /api/v1/fires`
  - `GET /api/v1/fires/stats`
- UC-F04:
  - `GET /api/v1/quality/fire-event/{id}`
- UC-F06:
  - `POST /api/v1/audit/land-use` con `X-API-Key` valida.

---

## 5. Validaciones condicionales (`ASYNC_GCS`)

Aplican si:
- release `ASYNC_GCS`, o
- `STORAGE_BACKEND=gcs` en el entorno objetivo.

### 5.1 GCS connectivity

```powershell
python scripts/test_gcs_conn.py
```

Esperado:
- Exit code `0`.
- `artifacts/gcs_conn_report.json` actualizado con 3/3 buckets en pass.

Nota Windows:
- Si aparece `UnicodeEncodeError` por consola cp1252, ejecutar:

```powershell
$env:PYTHONUTF8=1
python scripts/test_gcs_conn.py
```

### 5.2 Celery worker

```powershell
$env:CELERY_BROKER_URL="redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND="redis://localhost:6379/0"
python -m celery -A workers.celery_app.celery_app worker --loglevel=info --pool=solo
```

Validar:
- Startup sin errores.
- Tarea dummy con estado `SUCCESS`.

Checks recomendados:

```powershell
python -m celery -A workers.celery_app.celery_app inspect ping --timeout=10
python -c "from workers.celery_app import debug_task; r = debug_task.delay(); print(r.id); print(r.get(timeout=45))"
```

---

## 6. Criterios GO / NO GO

### GO para `MVP_CORE`

- Health checks OK.
- Feature flags MVP bloquean correctamente.
- UC-F03/F04/F06 OK.
- Smoke backend y smoke UI OK.

### GO para `ASYNC_GCS`

- Todo lo anterior, y ademas:
  - GCS 3/3 buckets OK.
  - Celery/colas OK.

### NO GO automatico

- Cualquier falla en checks bloqueantes del perfil elegido.
- Working tree sucio para el commit de release.
- UC en estado "no habilitar" accesible desde UI o API.

---

## 7. Post-MVP: habilitar features

Backend `.env`:

```env
FEATURE_CERTIFICATES=true
FEATURE_REFUGES=true
```

Frontend `frontend/.env`:

```env
VITE_FEATURE_CERTIFICATES=true
VITE_FEATURE_REFUGES=true
```

Reiniciar backend/frontend despues del cambio.
