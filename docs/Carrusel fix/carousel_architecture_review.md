# Revisión arquitectónica: carrusel de episodios y estados

**Proyecto:** ForestGuard — wildfire monitoring & recovery  
**Fecha:** 2026-02-24  
**Alcance:** cruce de `detailed_carousel_and_states_flow.md`, `carousel_technical_tasks.md`, `data_ingestion_process.md` contra el schema real (v5) y documentación de proyecto.

---

## A) Resumen ejecutivo

### 5 hallazgos críticos

| # | Hallazgo | Severidad | Por qué importa |
|---|----------|-----------|------------------|
| 1 | `worker-analysis` carece de variables GEE en `docker-compose.yml` → el carousel worker no puede autenticarse con Earth Engine y procesa 0 episodios | Crítico | El carrusel está silenciosamente roto en producción; la UI muestra tarjetas vacías |
| 2 | `episode_temporal_window_hours` sigue en 96 h (4 días) → episodios pasan a `extinct` prematuramente mientras sus eventos aún están en `monitoring` (168 h / 7 días) | Crítico | Se pierden episodios candidatos al carrusel; la UI del home queda vacía sin causa aparente |
| 3 | `satellite_images` tiene FK solo a `fire_events(id)`, no a `fire_episodes(id)` → no hay relación directa entre episodio y sus imágenes; `slides_data` JSONB es el único nexo y no tiene integridad referencial | Alto | Si `slides_data` se corrompe o queda desincronizado, no hay forma de reconstruir qué imágenes pertenecen a qué episodio sin lógica adicional |
| 4 | Endpoints de monitoring (`/api/v1/monitoring/*`) montados sin `dependencies=[Depends(get_current_user)]` → datos de análisis VAE expuestos sin autenticación | Crítico | Violación directa de la restricción de seguridad documentada; cualquier usuario anónimo puede leer datos de vegetación y cambios de uso |
| 5 | No existe mecanismo de lock/idempotencia en el carousel worker → si dos ejecuciones corren simultáneamente (beat + manual), pueden generar thumbnails duplicados y sobreescribir `slides_data` de forma inconsistente | Alto | Race condition realista durante troubleshooting (se dispara manualmente mientras beat también ejecuta) |

### 5 quick wins de bajo riesgo

1. **Agregar variables GEE a `worker-analysis`** en `docker-compose.yml` (5 min, fix inmediato del carrusel).
2. **`INSERT ON CONFLICT` del parámetro `episode_temporal_window_hours = 720`** en `system_parameters` (1 query SQL).
3. **Agregar `dependencies=[Depends(get_current_user)]`** al router de monitoring en `main.py` (1 línea).
4. **Comentar variables legacy GCS** en todos los workers de `docker-compose.yml` (reduce confusión operativa).
5. **Agregar filtro `slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0`** al endpoint que alimenta el home, como defensa para que la UI nunca reciba episodios sin thumbnail.

### 3 riesgos de regresión más probables

1. **Cambiar `episode_temporal_window_hours` de 96 a 720** sin el script de recálculo retroactivo deja episodios históricamente extintos sin reactivar → el carrusel sigue vacío para datos anteriores al fix.
2. **Agregar autenticación a monitoring** rompe cualquier frontend o integración que ya consuma esos endpoints sin JWT (verificar si hay consumo público actual).
3. **Force refresh del carrusel** sin rate limit puede agotar la cuota diaria de GEE (50 000 req/día) si se ejecuta sobre muchos episodios candidatos simultáneamente.

---

## B) Matriz de contrato: estado → UI → backend → worker → storage

### Estados de episodio

| Estado | Quién lo setea | Transiciones válidas | Evento disparador | Campos obligatorios | Vista UI | Endpoint(s) | Tabla/columna | Ante fallas |
|--------|---------------|---------------------|-------------------|--------------------|---------|-----------| --------------|-------------|
| `active` | Worker clustering (`episode_service._resolve_episode_status`) | → `monitoring`, → `closed` | Al menos 1 evento asociado en estado `active` | `start_date`, `centroid_lat/lon`, `event_count ≥ 1` | Home (FireCard), mapa (marcador rojo) | `GET /fire-episodes?mode=active` | `fire_episodes.status` (CHECK constraint) | N/A — estado derivado de eventos |
| `monitoring` | Worker clustering | → `active` (rebrote), → `extinct`, → `closed` | Todos los eventos internos en `monitoring` o `extinct` AND `now() - last_seen_at < episode_temporal_window_hours` | `last_seen_at` NOT NULL | Home (FireCard amarillo), mapa (marcador naranja) | `GET /fire-episodes?mode=active` (incluye monitoring) | `fire_episodes.status`, `fire_episodes.last_seen_at` | Si `last_seen_at` es NULL → no puede calcular transición; queda en monitoring indefinidamente |
| `extinct` | Worker clustering | → `monitoring` (recálculo/rebrote), → `closed` | `now() - last_seen_at ≥ episode_temporal_window_hours` AND todos los eventos extintos | `end_date` debería setearse | Histórico, no visible en home | `GET /fire-episodes?mode=history` | `fire_episodes.status`, `fire_episodes.end_date` | N/A — estado terminal salvo recálculo |
| `closed` | Merge worker o acción manual | Terminal (sin transiciones de salida) | Episodio absorbido por otro (merge) o cierre manual | `episode_mergers.absorbing_episode_id` si fue merge | No visible | N/A | `fire_episodes.status`, `episode_mergers` | N/A |

### Estados de slides/thumbnails (implícitos, no modelados como enum)

| Condición | Quién la determina | UI esperada | Defensa actual | Gap |
|-----------|--------------------|-------------|----------------|-----|
| `slides_data IS NULL` o `[]` | Episodio nuevo sin procesamiento GEE | No debería mostrarse en home | **No documentada** — depende de si el endpoint filtra o si el frontend ignora | El endpoint `?mode=active` no filtra por `slides_data`; el frontend debe manejar el caso |
| `slides_data` con 3 objetos válidos | Carousel worker post-ejecución exitosa | FireCard con 3 slides (RGB/SWIR/NBR) | `slides_data` se sobreescribe completamente en cada run | OK si el write es atómico |
| `slides_data` con URLs expiradas o rotas | OCI bucket con retención/limpieza | Imagen rota en UI | **No hay verificación** de validez de URLs al servir | Gap: no hay health check de URLs |
| `gee_candidate = false` | Episodio con pocos focos, no significativo | No procesado por carrusel; no visible si depende de slides | Filtro en carousel worker | OK |

### Tabla de trazabilidad de datos

```
fire_episodes.slides_data (JSONB, cache UI)
  └── [{ type: "rgb", thumbnail_url: "...", satellite_image_id: "...", generated_at: "..." }, ×3]
        │
        └── satellite_images (source of truth para metadata)
              └── FK: fire_event_id → fire_events(id)  ← ⚠️ NO hay FK a fire_episodes
                    └── fire_episode_events (N:M) → fire_episodes
```

---

## C) Revisión crítica de lógica

### C1. Asimetría temporal evento/episodio (CRÍTICO — documentado pero no corregido)

**Evidencia:** `detailed_carousel_and_states_flow.md` §1.1 describe el GAP. `carousel_technical_tasks.md` Tarea 2 propone cambiar `episode_temporal_window_hours` de 96 a 720.

**Estado en schema v5:** la tabla `system_parameters` existe con la estructura correcta (`param_key` UNIQUE, `param_value` JSONB). Sin embargo, no hay evidencia de que el valor `720` esté insertado en producción.

**Impacto:** episodios pasan a `extinct` en 4 días mientras eventos sobreviven 7 días en `monitoring`. El carrusel filtra `status IN ('active', 'monitoring')`, así que estos episodios desaparecen prematuramente.

### C2. `satellite_images.fire_event_id` sin FK a episodio

**Evidencia schema v5:**
```sql
CONSTRAINT satellite_images_fire_event_id_fkey 
  FOREIGN KEY (fire_event_id) REFERENCES public.fire_events(id)
```

No existe `fire_episode_id` en `satellite_images`. El carousel worker elige un "evento representativo" del episodio y graba la imagen contra ese evento. Si el evento representativo cambia (por merge o recálculo), la relación se pierde.

**Mitigación actual:** `fire_episodes.slides_data` actúa como cache con `satellite_image_id` embebido. Esto funciona pero no tiene integridad referencial.

### C3. `slides_data` en AMBAS tablas: `fire_events` y `fire_episodes`

**Evidencia schema v5:**
- `fire_events.slides_data jsonb DEFAULT '[]'::jsonb`
- `fire_episodes.slides_data jsonb` (sin default)

**Problema:** dos columnas `slides_data` en entidades diferentes. Los docs (`UC_F08R_technical_task.md` §5) aclaran que "el carrusel público debe usar episodios" y que `fire_events.slides_data` es legacy. Sin embargo, no hay constraint ni trigger que evite escritura en ambas.

**Recomendación:** deprecar `fire_events.slides_data` explícitamente (comentar en schema, agregar CHECK o trigger que prevenga escritura nueva).

### C4. Condición de carrera en ejecución del carousel worker

**Escenario:** Celery beat dispara `carousel-daily` a las 03:00 UTC. Un operador ejecuta `force_refresh: true` manualmente a las 03:01 UTC. Ambas instancias procesan los mismos episodios simultáneamente.

**Evidencia:** no hay lock distribuido (Redis SETNX, advisory lock PostgreSQL, ni Celery `solo` mode) documentado en `workers_documentation.md` ni en `carousel_technical_tasks.md`.

**Impacto:** doble descarga de thumbnails (desperdicio de cuota GEE), escritura no determinista de `slides_data` (la última en escribir gana, pero podría ser la ejecución con datos parciales).

### C5. Carousel worker queue mismatch

**Evidencia:**
- `workers_documentation.md`: `carousel_task.update_carousel` en queue `default`
- `data_ingestion_process.md`: carousel-daily en worker `analysis` (queue `analysis`)
- `celery_app.py` beat schedule: sin evidencia clara de routing

**Gap:** la documentación contradice sobre qué queue ejecuta el carousel. Si está en `default`, el `worker-analysis` no lo consume (consume `analysis`). Verificar configuración real de routing.

### C6. Campo `last_seen_at` puede ser NULL

**Evidencia schema v5:** `fire_episodes.last_seen_at timestamp with time zone` — sin NOT NULL ni default.

**Impacto:** si `last_seen_at` es NULL, la lógica de `_resolve_episode_status` que compara `now() - last_seen_at` crashea con `TypeError` o trata el episodio como eternamente en monitoring.

**Fix:** agregar `COALESCE(last_seen_at, start_date)` en la lógica, o migración que setee `last_seen_at = start_date` donde sea NULL.

---

## D) Seguridad

### D1. Endpoints de monitoring sin autenticación (CRÍTICO)

**Evidencia:** `UC_F12_critical_review.md` §2.1 — `app/main.py:236-240` monta el router sin `dependencies=[Depends(get_current_user)]`.

**Escenario de abuso:** cualquier usuario puede hacer `GET /api/v1/monitoring/recovery/{fire_event_id}` y obtener datos NDVI, estados de recuperación y cambios de uso del suelo sin JWT.

**Fix:**
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_user)],
)
```

**Riesgo del fix:** bajo. Verificar que el frontend ya envía JWT en las requests a monitoring.

### D2. Sin rate limiting en endpoints costosos (ALTO)

**Evidencia:** `0_master_plan.md` §9.2 — solo 6 endpoints tienen rate limiting. El endpoint `POST /api/v1/imagery/refresh/{episode_id}` y el trigger de monitoring no tienen protección.

**Escenario de abuso:** un usuario autenticado puede disparar refresh de imágenes en loop, agotando la cuota GEE (50 000 req/día) en minutos.

**Fix:** aplicar `rate_limiter.py` existente con límite de 5 req/hora por usuario en endpoints de generación.

### D3. Error messages exponen internals (BAJO)

**Evidencia:** `UC_F12_critical_review.md` §2.5 — `monitoring.py:423`:
```python
raise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")
```

**Fix:** loguear `str(e)` internamente, retornar mensaje genérico al usuario:
```python
logger.error(f"NDVI analysis failed: {e}", exc_info=True)
raise HTTPException(status_code=503, detail="Servicio de análisis temporalmente no disponible")
```

### D4. URLs de OCI sin validación de expiración

**Evidencia:** `data_ingestion_process.md` — las URLs en `slides_data` apuntan a OCI Object Storage. Si el bucket usa URLs pre-firmadas con expiración, las URLs embebidas en `slides_data` se vuelven inválidas.

**Escenario:** thumbnails generados hace 30 días con URLs que expiran en 7 días → imágenes rotas en la UI.

**Fix:** usar URLs públicas (si el bucket es público) o regenerar URLs firmadas al servir desde el endpoint (no embeber URLs firmadas en `slides_data`).

### D5. `page_size`/`limit` sin hard cap en endpoints de episodios

**Evidencia:** `0_master_plan.md` §9.1 — 2 endpoints sin hard caps.

**Fix:** agregar `Query(default=20, ge=1, le=100)` en todos los parámetros de paginación.

---

## E) Propuestas de mejora de código (priorizadas)

### Prioridad 1 — Correctivos inmediatos (< 1 hora total)

| # | Archivo | Cambio | Por qué | Riesgo |
|---|---------|--------|---------|--------|
| E1 | `docker-compose.yml` | Agregar `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH` a `worker-analysis` | El carousel worker no puede autenticarse con GEE | Bajo |
| E2 | SQL directo en prod | `INSERT INTO system_parameters ... VALUES ('episode_temporal_window_hours', '720', ...)` | Corrige extinción prematura de episodios | Bajo |
| E3 | `app/main.py` | Agregar `dependencies=[Depends(get_current_user)]` al router de monitoring | Seguridad: endpoints expuestos sin auth | Bajo |
| E4 | `docker-compose.yml` | Comentar variables `GOOGLE_APPLICATION_CREDENTIALS`, `GCS_*` en todos los workers | Elimina confusión operativa (legacy vs activo) | Bajo |

### Prioridad 2 — Estabilidad del carrusel (2-4 horas)

| # | Archivo | Cambio | Por qué | Riesgo |
|---|---------|--------|---------|--------|
| E5 | `app/services/episode_service.py` (`_resolve_episode_status`) | Refactorizar: `active` si hay eventos activos, `monitoring` si `now() - COALESCE(last_seen_at, start_date) < window`, `extinct` si excede window | Single source of truth para estado de episodio | Medio |
| E6 | Endpoint de episodios (API) | Agregar filtro `WHERE slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0` cuando `mode=active` | Defensa backend: UI nunca recibe episodios sin thumbnail | Bajo |
| E7 | Carousel worker | Agregar Redis lock (`SETNX carousel_lock 1 EX 3600`) al inicio; skip si lock existe | Previene race condition entre beat y ejecución manual | Bajo |
| E8 | `scripts/recalculate_episodes.py` | Crear script de recálculo retroactivo (Tarea 4 de `carousel_technical_tasks.md`) | Reactiva episodios extintos prematuramente | Medio |

### Prioridad 3 — Observabilidad y resiliencia (4-8 horas)

| # | Archivo | Cambio | Por qué | Riesgo |
|---|---------|--------|---------|--------|
| E9 | Carousel worker | Agregar logging estructurado: `{"event": "carousel_run", "episodes_found": N, "processed": M, "cache_hits": K, "errors": [...]}` | Sin esto, diagnosticar fallos requiere grep manual en logs no estructurados | Bajo |
| E10 | Carousel worker | Retry con backoff exponencial (30s, 60s, 120s) y max 3 reintentos por episodio; tras 3 fallos, marcar episodio con `gee_last_error` y continuar | Resiliencia ante fallos transitorios de GEE | Medio |
| E11 | Endpoint imagery | Rate limit de 5 req/hora por usuario en `POST /imagery/refresh/{id}` | Protege cuota GEE | Bajo |
| E12 | Schema | Deprecar `fire_events.slides_data` con comentario en schema y documentación | Elimina fuente de confusión sobre dónde vive la data del carrusel | Bajo |

---

## F) Paquete de tests de regresión

### Fixtures compartidos

```python
# tests/fixtures/carousel_fixtures.py
import pytest
from datetime import datetime, timezone, timedelta

@pytest.fixture
def episode_with_slides():
    """Episodio activo con 3 slides completos."""
    return {
        "id": "ep-001",
        "status": "active",
        "gee_candidate": True,
        "gee_priority": 10,
        "last_seen_at": datetime.now(timezone.utc) - timedelta(hours=2),
        "slides_data": [
            {"type": "rgb", "thumbnail_url": "https://oci.example.com/carousel/ep-001/rgb_2026-02-23.png",
             "satellite_image_id": "si-001", "generated_at": "2026-02-23T03:00:00Z"},
            {"type": "swir", "thumbnail_url": "https://oci.example.com/carousel/ep-001/swir_2026-02-23.png",
             "satellite_image_id": "si-002", "generated_at": "2026-02-23T03:00:00Z"},
            {"type": "nbr", "thumbnail_url": "https://oci.example.com/carousel/ep-001/nbr_2026-02-23.png",
             "satellite_image_id": "si-003", "generated_at": "2026-02-23T03:00:00Z"},
        ],
    }

@pytest.fixture
def episode_no_slides():
    """Episodio activo sin thumbnails (recién creado)."""
    return {
        "id": "ep-002",
        "status": "active",
        "gee_candidate": True,
        "gee_priority": 5,
        "last_seen_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "slides_data": None,
    }

@pytest.fixture
def episode_empty_slides():
    """Episodio con slides_data = [] (procesado pero sin imágenes)."""
    return {
        "id": "ep-003",
        "status": "monitoring",
        "gee_candidate": True,
        "slides_data": [],
    }

@pytest.fixture
def episode_extinct_premature():
    """Episodio extinto a los 4 días (bug de ventana temporal)."""
    return {
        "id": "ep-004",
        "status": "extinct",
        "last_seen_at": datetime.now(timezone.utc) - timedelta(days=10),
        # Con ventana de 720h (30 días), debería estar en monitoring
    }

@pytest.fixture
def episode_corrupt_slides():
    """Episodio con slides_data malformado."""
    return {
        "id": "ep-005",
        "status": "active",
        "slides_data": [{"type": "rgb"}],  # Falta thumbnail_url
    }
```

### F1. Unit tests

```python
# tests/unit/test_episode_status_resolver.py
"""Tests para _resolve_episode_status — single source of truth."""

class TestResolveEpisodeStatus:

    def test_active_when_any_event_active(self):
        """Si al menos 1 evento está activo → episodio active."""
        event_statuses = ["active", "monitoring", "extinct"]
        last_seen_at = datetime.now(timezone.utc)
        result = _resolve_episode_status(event_statuses, last_seen_at, window_hours=720)
        assert result == "active"

    def test_monitoring_within_window(self):
        """Todos los eventos en monitoring/extinct pero dentro de la ventana → monitoring."""
        event_statuses = ["monitoring", "extinct"]
        last_seen_at = datetime.now(timezone.utc) - timedelta(days=15)
        result = _resolve_episode_status(event_statuses, last_seen_at, window_hours=720)
        assert result == "monitoring"

    def test_extinct_beyond_window(self):
        """Todos extintos y fuera de ventana de 30 días → extinct."""
        event_statuses = ["extinct", "extinct"]
        last_seen_at = datetime.now(timezone.utc) - timedelta(days=35)
        result = _resolve_episode_status(event_statuses, last_seen_at, window_hours=720)
        assert result == "extinct"

    def test_monitoring_when_last_seen_is_none(self):
        """Si last_seen_at es None, usar start_date como fallback."""
        event_statuses = ["extinct"]
        result = _resolve_episode_status(event_statuses, last_seen_at=None, window_hours=720)
        # No debe crashear; debe retornar monitoring o extinct según fallback
        assert result in ("monitoring", "extinct")

    def test_old_4day_window_produces_premature_extinct(self):
        """Demuestra el bug: con window=96h, episodio de 5 días queda extinct."""
        event_statuses = ["monitoring"]  # Evento aún vivo
        last_seen_at = datetime.now(timezone.utc) - timedelta(days=5)
        result = _resolve_episode_status(event_statuses, last_seen_at, window_hours=96)
        assert result == "extinct"  # Bug: episodio muere antes que su evento
```

```python
# tests/unit/test_slides_data_schema.py
"""Validación del contrato de slides_data."""

VALID_SLIDE_TYPES = {"rgb", "swir", "nbr"}

def test_slides_data_has_exactly_3_entries(episode_with_slides):
    assert len(episode_with_slides["slides_data"]) == 3

def test_all_slide_types_present(episode_with_slides):
    types = {s["type"] for s in episode_with_slides["slides_data"]}
    assert types == VALID_SLIDE_TYPES

def test_each_slide_has_required_fields(episode_with_slides):
    required = {"type", "thumbnail_url", "satellite_image_id", "generated_at"}
    for slide in episode_with_slides["slides_data"]:
        assert required.issubset(slide.keys()), f"Slide missing fields: {required - slide.keys()}"

def test_corrupt_slides_detected(episode_corrupt_slides):
    """slides_data sin thumbnail_url debe ser detectado como inválido."""
    for slide in episode_corrupt_slides["slides_data"]:
        assert "thumbnail_url" not in slide or slide["thumbnail_url"] is None
```

### F2. Integration tests (backend)

```python
# tests/integration/test_carousel_endpoint.py
"""Tests de integración para el endpoint de episodios del carrusel."""

class TestCarouselEndpoint:

    def test_active_episodes_have_slides(self, client, db_with_episodes):
        """GET /fire-episodes?mode=active solo retorna episodios con slides."""
        response = client.get("/api/v1/fire-episodes?mode=active")
        assert response.status_code == 200
        for ep in response.json()["items"]:
            assert ep["slides_data"] is not None
            assert len(ep["slides_data"]) == 3

    def test_episode_without_slides_excluded(self, client, db_with_episode_no_slides):
        """Episodio activo sin slides NO aparece en modo active."""
        response = client.get("/api/v1/fire-episodes?mode=active")
        ids = [ep["id"] for ep in response.json()["items"]]
        assert "ep-002" not in ids

    def test_refresh_idempotent(self, client, auth_headers):
        """POST /imagery/refresh/{id} dos veces no duplica slides."""
        ep_id = "ep-001"
        client.post(f"/api/v1/imagery/refresh/{ep_id}", headers=auth_headers)
        client.post(f"/api/v1/imagery/refresh/{ep_id}", headers=auth_headers)
        response = client.get(f"/api/v1/fire-episodes/{ep_id}")
        assert len(response.json()["slides_data"]) == 3  # No 6

    def test_monitoring_requires_auth(self, client):
        """GET /monitoring/recovery/{id} sin JWT retorna 401."""
        response = client.get("/api/v1/monitoring/recovery/some-id")
        assert response.status_code == 401

    def test_page_size_hard_cap(self, client, auth_headers):
        """page_size > 100 retorna 422."""
        response = client.get("/api/v1/fire-episodes?page_size=101", headers=auth_headers)
        assert response.status_code == 422
```

### F3. Worker tests

```python
# tests/worker/test_carousel_worker.py
"""Tests del carousel worker."""

class TestCarouselWorker:

    def test_duplicate_execution_blocked(self, redis_client, mock_gee):
        """Ejecución duplicada se bloquea por Redis lock."""
        # Primera ejecución: adquiere lock
        result1 = generate_carousel.apply(kwargs={"force_refresh": False})
        assert result1.status == "SUCCESS"

        # Segunda ejecución inmediata: skip por lock
        result2 = generate_carousel.apply(kwargs={"force_refresh": False})
        assert result2.result["skipped"] is True

    def test_gee_failure_does_not_crash_batch(self, mock_gee_failing):
        """Fallo de GEE en un episodio no detiene el procesamiento del resto."""
        mock_gee_failing.side_effect = [Exception("GEE timeout"), mock_thumbnail_response]
        result = generate_carousel.apply(kwargs={"force_refresh": True})
        assert result.result["processed"] >= 1
        assert result.result["errors"] >= 1

    def test_cache_hit_skips_download(self, db_episode_with_same_gee_image):
        """Si last_gee_image_id coincide, skip descarga (cache hit)."""
        result = generate_carousel.apply()
        assert result.result["cache_hits"] >= 1

    def test_extinct_episodes_excluded(self, db_extinct_episode):
        """Episodios extintos no se procesan."""
        result = generate_carousel.apply()
        processed_ids = result.result.get("processed_ids", [])
        assert "ep-004" not in processed_ids

    def test_slides_data_atomic_write(self, db_episode, mock_gee):
        """slides_data se escribe completo (3 slides) o no se escribe."""
        # Simular fallo en el tercer thumbnail
        mock_gee.download_thumbnail.side_effect = [b"png1", b"png2", Exception("timeout")]
        result = generate_carousel.apply()
        # slides_data no debe quedar parcial (con 2 de 3)
        episode = db_session.query(FireEpisode).get("ep-001")
        assert episode.slides_data is None or len(episode.slides_data) == 3
```

### F4. E2E (frontend)

```typescript
// tests/e2e/carousel.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Carrusel del home', () => {

  test('no muestra tarjetas sin thumbnail', async ({ page }) => {
    await page.goto('/');
    const cards = page.locator('[data-testid="fire-card"]');
    const count = await cards.count();
    for (let i = 0; i < count; i++) {
      const img = cards.nth(i).locator('img');
      await expect(img).toHaveAttribute('src', /https?:\/\/.+\.png/);
    }
  });

  test('cada tarjeta tiene 3 slides navegables', async ({ page }) => {
    await page.goto('/');
    const firstCard = page.locator('[data-testid="fire-card"]').first();
    // Verificar indicadores de slide (dots o similar)
    const dots = firstCard.locator('[data-testid="slide-indicator"]');
    await expect(dots).toHaveCount(3);
  });

  test('tarjetas responsive en mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 }); // iPhone X
    await page.goto('/');
    const card = page.locator('[data-testid="fire-card"]').first();
    const box = await card.boundingBox();
    expect(box!.width).toBeLessThanOrEqual(375);
  });

  test('slide muestra tipo de visualización', async ({ page }) => {
    await page.goto('/');
    const firstCard = page.locator('[data-testid="fire-card"]').first();
    // Navegar al slide SWIR
    await firstCard.locator('[data-testid="slide-next"]').click();
    const label = firstCard.locator('[data-testid="slide-type-label"]');
    await expect(label).toContainText(/rgb|swir|nbr/i);
  });
});
```

---

## G) Criterios de aceptación (checklist de cierre)

### Infraestructura y configuración

- [ ] `worker-analysis` tiene variables `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH` en `docker-compose.yml`
- [ ] Variables legacy GCS comentadas en todos los workers
- [ ] `system_parameters` contiene `episode_temporal_window_hours = 720`
- [ ] Celery beat schedule confirma `carousel-daily` a las 03:00 UTC en queue `analysis`

### Backend y datos

- [ ] `_resolve_episode_status` implementa las 3 reglas: active > monitoring (dentro de ventana) > extinct (fuera de ventana)
- [ ] `COALESCE(last_seen_at, start_date)` usado en toda comparación temporal
- [ ] Endpoint `GET /fire-episodes?mode=active` filtra `slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0`
- [ ] Endpoint `POST /imagery/refresh/{id}` es idempotente (misma request no duplica thumbnails)
- [ ] Router de monitoring tiene `dependencies=[Depends(get_current_user)]`
- [ ] Errores de GEE no exponen internals en la respuesta HTTP

### Worker

- [ ] Carousel worker adquiere Redis lock antes de ejecutar; skip si lock activo
- [ ] Cada episodio procesado genera exactamente 3 slides (RGB, SWIR, NBR) o 0 (fallo atómico)
- [ ] Cache hit: si `last_gee_image_id` no cambió, skip descarga
- [ ] Reintentos: 3 intentos con backoff (30s, 60s, 120s) por episodio; tras 3 fallos, log + continuar con siguiente
- [ ] Log estructurado al finalizar: `episodes_found`, `processed`, `cache_hits`, `errors`

### Frontend

- [ ] Home no muestra FireCards sin imagen (validación defensiva en componente)
- [ ] Cada FireCard renderiza 3 slides navegables
- [ ] Layout no se rompe en viewport mobile (375px)
- [ ] Slide muestra label de tipo (RGB/SWIR/NBR)

### Documentación

- [ ] `fire_events.slides_data` marcado como deprecated en documentación
- [ ] Fuente de verdad definida: `satellite_images` (metadata) + `fire_episodes.slides_data` (cache UI)
- [ ] `detailed_carousel_and_states_flow.md` actualizado para reflejar implementación final

---

## Drift detectado entre documentación y código

| Aspecto | Docs dicen | Schema/código dice | Fuente canónica | Acción |
|---------|-----------|-------------------|-----------------|--------|
| Queue del carousel | `workers_documentation.md`: queue `default` | `data_ingestion_process.md`: queue `analysis` | **Código** (verificar `celery_app.py` routing) | Actualizar documentación |
| Horario carousel | `detailed_carousel_and_states_flow.md`: 00:00 ART | `data_ingestion_process.md`: 03:00 UTC (= 00:00 ART) | Coinciden (diferente representación) | OK |
| `slides_data` en fire_events | `UC_F08R_technical_task.md` §5: "no eliminar columnas ahora" | Schema v5: columna existe con default `[]` | **Mantener pero deprecar** | Agregar comentario deprecation |
| `episode_temporal_window_hours` | Docs: 720 (30 días) | Código default: 96 (4 días) | **Docs** — el código tiene el bug | Corregir código + insertar en system_parameters |
