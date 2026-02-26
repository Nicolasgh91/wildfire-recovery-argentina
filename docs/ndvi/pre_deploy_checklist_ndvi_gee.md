# Checklist pre-deploy: NDVI, GEE y visibilidad (Fases 0–6)

**Fecha:** 2026-02-26  
**Alcance:** Cambios de la hoja de ruta `hoja_de_ruta_ndvi_gee_v2.md` (Fases 0 a 6).  
**Objetivo:** Revisar regresiones, pruebas manuales y validaciones antes del deploy.

---

## 1. Validaciones automáticas (ejecutar antes de merge/deploy)

| # | Verificación | Comando | Criterio de éxito |
|---|--------------|---------|-------------------|
| A1 | Build frontend | `cd frontend && npm run build` | Exit 0, sin errores de TypeScript |
| A2 | Lint backend (opcional) | `ruff check app/` o linter del proyecto | Sin errores en archivos tocados |
| A3 | Tests backend | `pytest tests/ -v --ignore=tests/integration` (o con integración si hay DB) | Tests existentes pasan |
| A4 | GEE aislado en GET | `grep -n "VAEService\|get_recovery_timeline\|get_recovery_time_series" app/api/routes/monitoring.py` | **0 resultados** en rutas GET |

**Nota:** Los tests en `tests/unit/test_compose_healthchecks.py` (nginx/workers en docker-compose) pueden fallar por diferencias de estructura del proyecto; no son regresiones de NDVI/GEE. El resto de tests unitarios debe pasar.

---

## 2. Regresiones a vigilar

### 2.1 Backend

| Área | Riesgo | Qué revisar |
|------|--------|-------------|
| **GET /fires/:id** | Respuesta sin `recovery_snapshot` si migración G3-2 no aplicada | Aplicar antes: `2026_02_26_vegetation_monitoring_cloud_recovery_status.sql` y `2026_02_26_fase3_vm_indexes_fire_events_recovery_snapshot.sql`. Sin ellas, `recovery_snapshot` puede ser siempre `null` o fallar si faltan columnas en `fire_events`. |
| **GET /monitoring/recovery/{id}** | Latencia o 503 | Sigue leyendo solo BD; no debe llamar a GEE. Si hay 503, revisar logs (vegetation_monitoring, conexión BD). |
| **POST /monitoring/recovery/trigger** | 429 inesperado o bloqueo de admins | Límite 10/h por IP + 5/6h por usuario. Admins deben poder disparar (verificar que el rate por usuario no bloquee al admin). |
| **Circuit breaker GEE** | Worker de recovery falla siempre si circuito abierto | Worker usa `VAEService` → `gee_circuit.call()`. Si el circuito está OPEN, el worker recibe `GEEServiceUnavailableError`; debe registrar y no caer en loop. |
| **Recovery por episodio** | 404 o 500 en GET by-episode | Episodio debe existir; `fire_episode_events` debe tener filas para ese episodio. Sin datos, respuesta 200 con `recovery_status: "pending"` y `monitoring_data: []`. |

### 2.2 Frontend

| Área | Riesgo | Qué revisar |
|------|--------|-------------|
| **Detalle evento (/fires/:id, evento)** | Chart no aparece o datos rotos | Usuario autenticado debe ver RecoveryPanel con datos de `GET /monitoring/recovery/{id}`. Badge público debe verse con `recovery_snapshot` si existe. |
| **Detalle episodio (/fires/:id, episodio)** | Chart no carga o error de red | Usuario autenticado debe ver RecoveryPanel con datos de `GET /monitoring/recovery/by-episode/{id}`. Sin datos, mensaje “No hay datos de monitoreo agregados para este episodio aún.” |
| **Usuario anónimo** | Ve chart o no ve badge | No debe ver RecoveryPanel (chart). Debe ver solo el badge de “Recuperación” cuando `recovery_snapshot` viene en GET /fires/:id. |
| **NdviChart** | Tipos o formato incorrecto | Props: `data: MonthlyNDVI[]`, `baselineNdvi`, `fireDate`. Tooltip con recovery % y cloud; línea vertical en fireDate. |

### 2.3 Migraciones y datos

| Área | Riesgo | Qué revisar |
|------|--------|-------------|
| **Orden de migraciones** | Trigger o columnas faltantes | 1) `2026_02_26_vegetation_monitoring_cloud_recovery_status.sql` (cloud_cover_pct, recovery_status en vm). 2) `2026_02_26_fase3_vm_indexes_fire_events_recovery_snapshot.sql` (columnas y trigger en fire_events). |
| **Trigger de snapshot** | fire_events sin actualizar | Tras INSERT/UPDATE en `vegetation_monitoring`, las columnas `recovery_status`, `recovery_percentage`, `last_monitoring_date` de `fire_events` deben actualizarse (trigger `trg_sync_recovery_snapshot`). |
| **Worker recovery** | No escribe o duplica filas | UPSERT por (fire_event_id, monitoring_date). Cola `gee`. Tras ejecutar un job, debe haber (o actualizarse) una fila en vegetation_monitoring. |

---

## 3. Pruebas manuales recomendadas

### 3.1 Autenticación y visibilidad (T-2, T-8)

1. **Anónimo – detalle evento**
   - Ir a `/fires/{id}` con un `id` de **evento** (no episodio), sin iniciar sesión.
   - **Esperado:** Badge “Recuperación: [estado] X%” si existe `recovery_snapshot`; **no** se muestra el panel con chart ni métricas.
   - **Esperado:** Si no hay `recovery_snapshot`, no aparece el bloque del badge.

2. **Anónimo – detalle episodio**
   - Ir a `/fires/{id}` con un `id` de **episodio**, sin iniciar sesión.
   - **Esperado:** Badge de recuperación si el episodio tiene `recovery_snapshot` (p. ej. desde evento representativo); **no** panel de chart.

3. **Autenticado – detalle evento**
   - Con usuario logueado, abrir `/fires/{id}` (evento).
   - **Esperado:** Badge público (si hay snapshot) + **RecoveryPanel** con chart, baseline, NDVI actual, % recuperación. Si no hay datos, mensaje de “Análisis de recuperación pendiente”.

4. **Autenticado – detalle episodio**
   - Con usuario logueado, abrir `/fires/{id}` (episodio).
   - **Esperado:** Badge (si hay snapshot) + **RecoveryPanel** con serie **agregada por episodio** (mismo formato de chart). Sin datos, mensaje “No hay datos de monitoreo agregados para este episodio aún.”

5. **GET monitoring sin token**
   - `GET /api/v1/monitoring/recovery/{uuid}` sin header `Authorization`.
   - **Esperado:** 401.

### 3.2 API y datos (T-1, T-7)

6. **GET /fires/:id – recovery_snapshot**
   - `GET /api/v1/fires/{id}` sin auth (o con auth).
   - **Esperado:** En el JSON, campo `recovery_snapshot` presente. Si hay datos de recuperación: `recovery_status`, `recovery_percentage` (y opcionalmente `last_monitoring_date`). Valores vienen de `fire_events` (trigger) o fallback a última fila de `vegetation_monitoring`.

7. **GET /monitoring/recovery/{id} – latencia**
   - Con token, `GET /api/v1/monitoring/recovery/{fire_event_id}` para un evento con datos en `vegetation_monitoring`.
   - **Esperado:** 200 y respuesta en < 0,5 s (solo lectura BD).

8. **GET /monitoring/recovery/by-episode/{id}**
   - Con token, `GET /api/v1/monitoring/recovery/by-episode/{episode_id}`.
   - **Esperado:** 200; estructura igual a RecoveryResponse (`fire_event_id` = episode_id, `monitoring_data` con promedios por mes). Episodio sin datos → 200, `recovery_status: "pending"`, `monitoring_data: []`. Episodio inexistente → 404.

### 3.3 Rate limit y admin (T-3)

9. **Trigger – rate limit por IP**
   - Como **admin**, llamar **POST /api/v1/monitoring/recovery/trigger?fire_event_id=...** más de 10 veces en 1 hora desde la misma IP.
   - **Esperado:** Tras superar el límite, 429 con body conteniendo `retry_after` (segundos).

10. **Trigger – éxito**
    - Como admin, 1 llamada a **POST /api/v1/monitoring/recovery/trigger?fire_event_id={uuid}**.
    - **Esperado:** 202, mensaje de jobs encolados en cola `gee`.

### 3.4 Circuit breaker (T-6 – opcional en pre-deploy)

11. **Health circuit (admin)**
    - Con usuario **admin**, `GET /api/v1/health/gee/circuit`.
    - **Esperado:** 200 con `circuit_state`, `failure_count`, `is_healthy`, `last_failure`. Sin auth o sin admin → 401/403.

---

## 4. Resumen de criterios de go/no-go

- [ ] **A1–A4** ejecutadas y exitosas.
- [ ] **Migraciones** aplicadas en orden (cloud_recovery_status → fase3 indexes + snapshot).
- [ ] **Al menos** pruebas manuales 1, 2, 3, 5, 6 y 9 ejecutadas sin regresiones.
- [ ] Sin 503 en GET recovery (evento) en entorno de staging con datos en BD.
- [ ] Documentación/runbook actualizada si hay nuevos endpoints o variables de entorno.

---

## 5. Resultados de validación automática (ejemplo 2026-02-26)

| Verificación | Resultado |
|--------------|-----------|
| A1 Build frontend | OK (exit 0) |
| A4 GEE aislado en GET | OK (0 coincidencias en monitoring.py) |
| A3 Tests unitarios | 86 passed; 6 failed en `test_compose_healthchecks.py` (preexistentes, no NDVI/GEE) |

Ejecutar antes del deploy: `cd frontend && npm run build` y `pytest tests/unit -v --ignore=tests/unit/test_compose_healthchecks.py` si se desea verde al 100 % en unit.

---

## 6. Referencias

- Hoja de ruta: `docs/ndvi/hoja_de_ruta_ndvi_gee_v2.md`
- Spec GEE: `docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md`
- Análisis NDVI: `docs/ndvi/analisis_ndvi.md`
- Deuda técnica chart: `docs/ndvi/deuda_tecnica_ndvi_chart.md`

---

## 7. Warnings opcionales (resueltos en plan de deuda técnica)

**Aplicado (Fase 1 y 2 del plan de deuda técnica):**

- `datetime.utcnow()` sustituido por `datetime.now(timezone.utc)` en `app/core/circuit_breaker.py` y `app/api/routes/health.py`.
- Pydantic `class Config` migrado a `model_config = ConfigDict(...)` en `RecoveryResponse` (monitoring.py), `DetailedHealthResponse` (health.py) y `ErrorResponse` (schemas/error.py).
- `HTTP_422_UNPROCESSABLE_ENTITY` sustituido por `HTTP_422_UNPROCESSABLE_CONTENT` en `app/services/contact_service.py` y `app/api/v1/account.py`.

**Pendiente (Fase 3 opcional):** Resto de usos de `datetime.utcnow()` en webhooks, payments, visitor_logs, alerts, models, user, mercadopago_service — ver plan de deuda técnica si se desea homogeneizar.
