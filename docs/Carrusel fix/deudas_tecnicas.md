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

## DT-008: Thumbnail black stripe — fixes fallidos y solución definitiva

**Componente:** `app/services/gee_service.py` (`get_thumbnail_url`, `get_dnbr_thumbnail_url`)
**Detectado en:** diagnóstico carrusel thumbnails (2026-03)
**Severidad:** Alta
**Estado:** ✅ RESUELTO (2026-03-04)

**Contexto:** Los thumbnails satelitales de 768×576 px (ratio 4:3) aparecían con franjas negras verticales (padding). La causa raíz es que en la proyección UTM nativa de Sentinel-2, 1° lat ≠ 1° lon en píxeles, por lo que un bbox 4:3 en grados no producía 4:3 en píxeles.

### Cronología de fixes

| Fix | Cambio | Resultado | Por qué falló |
|-----|--------|-----------|---------------|
| 1: bbox AR | `delta_lon = delta_lat * (w/h)` en `_bbox_from_point()` | bbox correcto en grados, pero franja persiste | Necesario pero insuficiente: UTM ≠ equiangular |
| 2: width/height | `{"width": 768, "height": 576}` en `getThumbURL` | Thumbnail 1×1 px | `width`/`height` NO son params válidos de la API de thumbnails de GEE |
| 3: crs en params | `"crs": "EPSG:4326"` en dict de `getThumbURL` | Error "inconsistent projections" | `crs` en params solo declara CRS de salida; bandas con resoluciones distintas (B4 10m vs B11/B12 20m) causan conflicto |
| 4: reproject + w/h | `vis_image.reproject("EPSG:4326", scale=20)` + `{"width": 768, "height": 576}` | Thumbnail 1×1 px | `width`/`height` siguen siendo inválidos |
| **5: reproject + dimensions** | `vis_image.reproject(crs="EPSG:4326", scale=20)` + `{"dimensions": "768x576"}` | **768×576 exacto, sin padding** | **SOLUCIÓN DEFINITIVA** |

### Solución definitiva (Fix 5)

```python
# 1. Normalizar proyección antes de generar thumbnail
vis_image = vis_image.reproject(crs="EPSG:4326", scale=20)

# 2. Pasar dimensions como string "WxH" — GEE produce canvas exacto
size_params = {"dimensions": "768x576"}

# 3. getThumbURL SIN width/height separados, SIN crs en params
url = vis_image.getThumbURL({"region": geometry, "format": "png", **size_params, **vis_params})
```

**Por qué funciona:**
- En EPSG:4326, GEE muestrea equiangularmente: 1° lat = 1° lon en espacio de píxeles.
- Un bbox `0.10666° × 0.08°` (ratio 4:3 en grados) → ratio 4:3 en píxeles.
- `dimensions="768x576"` (string) produce el canvas exacto sin padding.
- `scale=20` corresponde a la resolución de las bandas SWIR (B11/B12 a 20m).

**Archivos modificados:**
- `app/services/gee_service.py`: `get_thumbnail_url()` y `get_dnbr_thumbnail_url()`
- `tests/unit/test_thumbnail_pipeline.py`: tests reescritos + clases nuevas (`TestGetThumbnailUrlProjectionNormalization`, `TestBboxProjectionConsistency`)

### Verificación en producción

**Paso A — Reset cache episodio de prueba:**
```bash
docker exec -i forestguard-api python -c "
import os, sqlalchemy
from urllib.parse import quote_plus
user = os.environ['DB_USER']
password = quote_plus(os.environ['DB_PASSWORD'])
host = os.environ['DB_HOST']
port = os.environ.get('DB_PORT', '6543')
name = os.environ.get('DB_NAME', 'postgres')
url = f'postgresql://{user}:{password}@{host}:{port}/{name}'
engine = sqlalchemy.create_engine(url)
with engine.begin() as conn:
    r = conn.execute(sqlalchemy.text(\"\"\"
        UPDATE fire_episodes
        SET slides_data = NULL,
            last_gee_image_id = NULL,
            slides_status = 'pending'
        WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c'
    \"\"\"))
    print(f'Rows updated: {r.rowcount}')
"
```

**Paso B — Disparar regeneración:**
```bash
docker exec -it forestguard-worker-gee celery \
  -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}' \
  --queue=analysis
```

**Paso C — Monitorear:**
```bash
docker logs --tail 50 -f forestguard-worker-gee 2>&1 \
  | grep -iE "5bd52c45|succeeded|completed|error"
```

**Paso D — Diagnóstico de brillo post-regeneración:**
```bash
THUMB_URL=$(docker exec -i forestguard-api python -c "
import os, sqlalchemy
from urllib.parse import quote_plus
user = os.environ['DB_USER']
password = quote_plus(os.environ['DB_PASSWORD'])
host = os.environ['DB_HOST']
port = os.environ.get('DB_PORT', '6543')
name = os.environ.get('DB_NAME', 'postgres')
url = f'postgresql://{user}:{password}@{host}:{port}/{name}'
engine = sqlalchemy.create_engine(url)
with engine.connect() as conn:
    row = conn.execute(sqlalchemy.text(\"\"\"
        SELECT slides_data->0->>'thumbnail_url'
        FROM fire_episodes
        WHERE id = '5bd52c45-70c3-43f0-bccf-ccf7be86286c'
    \"\"\")).scalar()
    print(row or '')
")

curl -sL "\$THUMB_URL" -o /tmp/thumb_check.png
docker cp /tmp/thumb_check.png forestguard-api:/tmp/thumb_check.png

docker exec -i forestguard-api python -c "
from PIL import Image
import numpy as np, os
img = np.array(Image.open('/tmp/thumb_check.png').convert('RGB'), dtype=float)
h, w = img.shape[:2]
size_kb = os.path.getsize('/tmp/thumb_check.png') / 1024
left_b  = img[:, :5, :].mean()
right_b = img[:, -5:, :].mean()
ratio   = w / h
print(f'Tamaño:         {size_kb:.0f} KB')
print(f'Dimensiones:    ({w}, {h})')
print(f'Ratio:          {ratio:.4f}')
print(f'Brillo col izq: {left_b:.2f}')
print(f'Brillo col der: {right_b:.2f}')
ok = (left_b > 10 and right_b > 10
      and (w, h) == (768, 576)
      and 500 < size_kb < 1200)
print('-> ACEPTADO' if ok else '-> RECHAZADO')
"
```

**Criterio de aceptación:**
```
Dimensiones:    (768, 576)
Ratio:          1.3333
Brillo col izq: > 10.0
Brillo col der: > 10.0
Tamaño:         500–1200 KB
Tests:          todos pasan
Legacy code:    eliminado
```

---
