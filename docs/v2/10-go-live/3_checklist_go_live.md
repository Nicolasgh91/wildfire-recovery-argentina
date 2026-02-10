# Checklist Go-Live (smoke + validacion tecnica preproduccion)

> Objetivo: que la decision de salida sea repetible y auditable.
> Resultado esperado: "pasa / no pasa" con evidencia (logs, reportes y codigos de salida).

---

## 0. Perfil de release (obligatorio elegir uno)

- [ ] `MVP_CORE`: solo UC-F03, UC-F04 y UC-F06 expuestas al usuario final.
- [ ] `ASYNC_GCS`: se habilitan flujos asincronos o dependientes de storage remoto (ej. UC-F11).

Regla:
- `MVP_CORE`: GCS/Celery pueden quedar como advertencia.
- `ASYNC_GCS`: GCS/Celery pasan a ser bloqueantes.

---

## 1. Precondiciones de entorno

- [ ] Branch/commit de referencia definido para release.
- [ ] Working tree sin cambios locales pendientes.
- [ ] Backend responde en `http://localhost:8000`.
- [ ] Frontend responde en `http://localhost:5173` (si se valida UI).
- [ ] Variables de entorno cargadas de forma consistente.

Evidencia:
- `git status --porcelain` vacio.
- `GET /health` devuelve 200.

---

## 2. Bloqueantes siempre (todos los perfiles)

### 2.1 Salud backend

- [ ] `GET /health` -> 200.
- [ ] `GET /api/v1/health/db` -> 200.
- [ ] `GET /api/v1/health/celery` -> 200.
- [ ] `GET /api/v1/health/gee` -> 200 (`healthy` o `degraded`).

### 2.2 Feature flags MVP (bloqueo real UI + API)

- [ ] `GET /api/v1/certificates/verify/test` -> 404.
- [ ] `GET /api/v1/visitor-logs` -> 404.
- [ ] `GET /api/v1/shelters` -> 404.
- [ ] Frontend: `/certificates` y `/shelters` muestran 404.
- [ ] Frontend: navbar sin links a Certificates/Shelters.

### 2.3 Smoke automatizado base

- [ ] `powershell -ExecutionPolicy Bypass -File scripts/go_live_smoke.ps1` -> exit code 0.

Criterio de salida:
- Si falla cualquier punto de la seccion 2 -> **NO GO**.

---

## 3. Bloqueantes funcionales MVP (siempre)

### 3.1 UC-F03 historico y dashboard

- [ ] `/fires/history` carga y pagina.
- [ ] `GET /api/v1/fires` responde correctamente.
- [ ] `GET /api/v1/fires/stats` responde correctamente.
- [ ] Export respeta filtros.

### 3.2 UC-F04 calidad de dato

- [ ] `GET /api/v1/quality/fire-event/{id}` -> 200.
- [ ] Casos incompletos no rompen y devuelven degradacion controlada.

### 3.3 UC-F06 auditoria de uso del suelo

- [ ] UI `/audit` completa flujo minimo.
- [ ] `POST /api/v1/audit/land-use` con API key valida -> 200.
- [ ] Sin API key -> 401.

### 3.4 Smoke UI (si frontend incluido en release)

- [ ] `powershell -ExecutionPolicy Bypass -File scripts/ui_smoke.ps1` -> exit code 0.

Criterio de salida:
- Si falla cualquier punto de la seccion 3 -> **NO GO**.

---

## 4. Bloqueantes condicionales (`ASYNC_GCS`)

Aplican solo si:
- el perfil es `ASYNC_GCS`, o
- `STORAGE_BACKEND=gcs` en el entorno objetivo, o
- se habilita UC-F11/colas asincronas en release.

### 4.1 Conectividad GCS real

- [ ] `python scripts/test_gcs_conn.py` -> exit code 0.
- [ ] Buckets images/reports/certificates con upload/read/delete OK.
- [ ] Reporte actualizado en `artifacts/gcs_conn_report.json`.

### 4.2 Workers/Celery

- [ ] Worker levanta sin errores de import/config.
- [ ] Tarea dummy ejecuta y retorna `SUCCESS`.
- [ ] No hay acumulacion de cola sin consumo.

Criterio de salida:
- Si aplica seccion 4 y algun punto falla -> **NO GO**.

---

## 5. Seguridad transversal

- [ ] RLS activo en tablas sensibles.
- [ ] Sin acceso anonimo directo a tablas internas.
- [ ] CORS configurado para dominios esperados.
- [ ] Logs de auditoria activos para operaciones criticas.

---

## 6. Decision final GO / NO GO

- [ ] Secciones 2 y 3 completas.
- [ ] Seccion 4 completa si el release es `ASYNC_GCS`.
- [ ] Evidencias adjuntas (salida scripts + artifacts + capturas).
- [ ] Working tree limpio para la rama/commit que se despliega.

Resultado:
- [ ] GO a produccion.
- [ ] NO GO (registrar bloqueantes y fecha de revalidacion).
