# Deudas Técnicas — ForestGuard

**Fecha inicio:** 2026-02-25  
**Mantenedor:** equipo ForestGuard  

---

## DT-001: `slides_data` no se limpia proactivamente al cerrar episodios

**Componente:** `app/services/episode_service.py`, `workers/tasks/episode_closer_task.py`  
**Detectado en:** revisión arquitectural flujo thumbnails (2026-02-25)  
**Severidad:** Baja  
**Estado:** ✅ RESUELTO (2026-02-25)

**Contexto:** Cuando un episodio transiciona a `closed`, `slides_data` queda con las URLs antiguas. Con OCI Object Storage y URLs directas (no presignadas) esto no rompe nada hoy. Si en el futuro se adopta un backend con URLs firmadas con TTL corto, las tarjetas mostrarán imágenes rotas.  

**Solución implementada:**  
- Creado `workers/tasks/episode_closer_task.py` con la tarea `close_extinct_episodes`.
- Al hacer `status = 'closed'` se setea simultáneamente `slides_data = '[]'::jsonb`.
- Registrada en beat schedule como `close-extinct-episodes-daily` a las 05:00 UTC.
- Registrada en `task_routes` y en la lista `include` de `celery_app.py`.

---

## DT-002: `OP-1` — Episodios nuevos sin thumbnails hasta el día siguiente

**Componente:** `workers/tasks/carousel_task.py`, `workers/tasks/clustering_task.py`, beat schedule  
**Detectado en:** revisión arquitectural flujo thumbnails (2026-02-25)  
**Severidad:** Media  
**Estado:** ✅ RESUELTO (2026-02-25)

**Contexto:** Un episodio creado a las 02:00 UTC no recibe thumbnails hasta las 03:00 UTC del día siguiente (hasta 25h de delay). La API filtra episodios sin `slides_data`, por lo que no aparecen en el carrusel hasta esa regeneración.  

**Solución implementada:**  
- En `cluster_fire_episodes` (`clustering_task.py`): si `result["episodes_created"] > 0`, se encola inmediatamente `generate_carousel.apply_async(queue="analysis")`.
- Elimina el delay de hasta 25h para episodios recién creados.

---

## DT-003: `OP-2` — Rate limiting de GEE puede truncar el batch con errores/retries

**Componente:** `app/services/imagery_service.py`, `app/core/gee_semaphore.py`, `workers/tasks/carousel_task.py`  
**Detectado en:** revisión arquitectural flujo thumbnails (2026-02-25)  
**Severidad:** Media  
**Estado:** ✅ RESUELTO (2026-02-25)

**Contexto:** Con batch_size=20, ~5-7 calls GEE por episodio y rate limit de 1 req/s, un batch completo toma ~10 minutos. Si hay errores y reintentos (Celery retry backoff), el lock de 30min podía expirar y la siguiente invocación del beat encontraba el lock stale.  

**Solución implementada:**  
- Lock TTL aumentado de 30 min (`ex=1800`) a 60 min (`ex=3600`) en `carousel_task.py`.
- Test `test_carousel_worker.py` actualizado para reflejar el nuevo valor `ex=3600`.
- Pendiente de monitorear cuando episodios activos superen 15 (considerar reducir batch_size o implementar heartbeat).

---

## DT-004: `OP-3` — `ON DELETE CASCADE` en `satellite_images.fire_event_id` puede destruir thumbnails

**Componente:** `app/models/evidence.py`  
**Detectado en:** revisión arquitectural flujo thumbnails (2026-02-25)  
**Severidad:** Alta (riesgo latente)  
**Estado:** ✅ RESUELTO en ORM (2026-02-25) — ⚠️ pendiente migración DDL en Postgres

**Contexto:** La FK `satellite_images.fire_event_id → fire_events(id)` tenía `ON DELETE CASCADE`. Si un `fire_event` se absorbe en un merge y se elimina físicamente, todos sus thumbnails se borraban en cascada.

**Solución implementada:**  
- Modelo ORM `SatelliteImage.fire_event_id` cambiado: `ondelete="CASCADE"` → `ondelete="SET NULL"`, columna de `nullable=False` → `nullable=True`.
- Creado `scripts/maintenance/migrate_fk_fire_event_id.py` para aplicar el DDL en Postgres:
  1. `DROP CONSTRAINT` de la FK existente (con CASCADE).
  2. `ALTER COLUMN fire_event_id DROP NOT NULL`.
  3. `ADD CONSTRAINT ... FOREIGN KEY ... ON DELETE SET NULL`.
- **Acción requerida:** ejecutar `python scripts/maintenance/migrate_fk_fire_event_id.py` en producción.

---

## DT-005: Tests `test_carousel_worker.py` rotos por refactoring de `redis_client`

**Componente:** `tests/unit/test_carousel_worker.py`, `workers/tasks/carousel_task.py`  
**Detectado en:** ejecución suite de tests (2026-02-25)  
**Severidad:** Media (cobertura de regresión perdida)  
**Estado:** ✅ RESUELTO (2026-02-25)

**Tests afectados:**
- `test_generate_carousel_lock_acquired`
- `test_generate_carousel_lock_blocked`

**Causa raíz:** Los tests mockeaban `workers.tasks.carousel_task.redis_client` con `@patch`, pero `carousel_task.py` importaba `redis_client` inline dentro de la función (`from app.services.redis_service import redis_client`), lo que imposibilitaba el mock a nivel de módulo. Además, `app/services/redis_service.py` no existía.

**Solución implementada:**
- Creado `app/services/redis_service.py` que instancia `redis_client = redis.from_url(settings.REDIS_URL)` como variable de módulo.
- `carousel_task.py` ahora importa `redis_client` al nivel de módulo: `from app.services.redis_service import redis_client`.
- Tests actualizados para invocar con `generate_carousel.run(...)` (en lugar de `generate_carousel(self, ...)`) para compatibilidad con `bind=True`.
- `logger.info` con `str(result)` para evitar TypeError de `%`-format con dicts en pytest log capture.

---

## DT-006: `app/db/database.py` ya no exporta `engine`

**Componente:** `app/db/database.py`, `app/db/session.py`  
**Detectado en:** ejecución suite de tests (2026-02-25)  
**Severidad:** Media (riesgo de ruptura silenciosa en código legacy)  
**Estado:** ✅ RESUELTO (2026-02-25)

**Test afectado:**
- `test_db_url_construction.py::TestDatabaseModuleDelegation::test_engine_is_exported`

**Causa raíz:** El `engine` SQLAlchemy fue movido a `app/db/session.py` y `database.py` ya no lo re-exportaba. Código legacy que importara `from app.db.database import engine` rompería con `ImportError`.

**Solución implementada:**
- Agregado en `app/db/database.py`:
  ```python
  engine = get_engine()  # re-export para backward compatibility
  ```

---

## DT-007: Rutas eliminadas causan 404 en tests de autenticación

**Componente:** `app/api/` (rutas de workers y reports), `tests/unit/test_auth_matrix.py`, `tests/unit/test_reports_auth.py`  
**Detectado en:** ejecución suite de tests (2026-02-25)  
**Severidad:** Media (cobertura de seguridad desactualizada)  
**Estado:** ✅ RESUELTO (2026-02-25)

**Tests afectados:**
- `test_auth_matrix.py::TestApiKeyEndpointsRequireKey::test_workers_without_key_returns_403`
- `test_reports_auth.py::TestReportsRequireJWT::test_get_report_by_id_no_token_returns_401`

**Causa raíz:**
- `POST /api/v1/workers/detect-land-use` → ruta renombrada a `/detect-land-use-change`. El test esperaba 403 pero recibía 404.
- `GET /api/v1/reports/{id}` → ruta nunca implementada. Solo existe `GET /reports/{id}/verify` (público) y los POST con JWT. El test esperaba 401 pero recibía 404.

**Solución implementada:**
- `test_auth_matrix.py`: URL corregida a `/api/v1/workers/detect-land-use-change`.
- `test_reports_auth.py`: test reconvertido a verificar que `POST /reports/historical` sin token retorna 401 (ruta JWT existente, comportamiento correcto).

---
