# Tareas técnicas: hardening del carrusel y estados de episodios

**Origen:** revisión arquitectónica del 2026-02-24  
**Ejecutor:** Claude Code  
**Rama sugerida:** `fix/carousel-hardening`

---

## Índice de tareas

| Fase | ID | Tarea | Esfuerzo | Dependencias |
|------|----|-------|----------|--------------|
| 0 | CFG-001 | Variables GEE en worker-analysis | 5 min | — |
| 0 | CFG-002 | Comentar variables legacy GCS | 10 min | — |
| 0 | SEC-001 | Autenticación en router monitoring | 5 min | — |
| 0 | SEC-002 | Sanitizar mensajes de error monitoring | 15 min | — |
| 1 | DB-001 | Insertar parámetro episode_temporal_window_hours | 5 min | — |
| 1 | DB-002 | Migración: COALESCE safety en last_seen_at | 10 min | — |
| 2 | CORE-001 | Refactorizar _resolve_episode_status | 30 min | DB-001, DB-002 |
| 2 | CORE-002 | Actualizar defaults canónicos | 10 min | — |
| 2 | CORE-003 | Filtro slides_data en endpoint de episodios | 20 min | — |
| 3 | WORK-001 | Redis lock en carousel worker | 25 min | — |
| 3 | WORK-002 | Retry con backoff por episodio | 25 min | — |
| 3 | WORK-003 | Escritura atómica de slides_data | 20 min | — |
| 3 | WORK-004 | Logging estructurado del carousel | 15 min | — |
| 4 | SEC-003 | Rate limiter en endpoints de generación | 30 min | — |
| 4 | SEC-004 | Hard cap page_size en endpoints de episodios | 10 min | — |
| 5 | SCRIPT-001 | Script de recálculo retroactivo | 25 min | CORE-001 |
| 5 | SCRIPT-002 | Script de verificación E2E | 10 min | Todo lo anterior |
| 6 | DOC-001 | Deprecar fire_events.slides_data | 10 min | — |
| 7 | TEST-001 | Unit tests de estados | 30 min | CORE-001 |
| 7 | TEST-002 | Unit tests de slides_data schema | 15 min | — |
| 7 | TEST-003 | Integration tests de endpoint carrusel | 30 min | CORE-003 |
| 7 | TEST-004 | Worker tests | 30 min | WORK-001..004 |
| 7 | TEST-005 | E2E frontend tests | 20 min | — |

---

## Fase 0: correctivos de configuración y seguridad crítica

### CFG-001: agregar variables GEE a worker-analysis

**Archivo:** `docker-compose.yml`  
**Servicio:** `worker-analysis`

**Contexto:** el carousel worker se ejecuta en `worker-analysis` pero este servicio no tiene las variables de Google Earth Engine. El worker falla silenciosamente con `processed: 0`.

**Instrucciones:**

1. Localizar el servicio `worker-analysis` en `docker-compose.yml`.
2. En la sección `environment`, agregar las siguientes variables justo después de `ENVIRONMENT`:

```yaml
      # Google Earth Engine (independiente del storage)
      GEE_PROJECT_ID: ${GEE_PROJECT_ID:-}
      GEE_SERVICE_ACCOUNT_EMAIL: ${GEE_SERVICE_ACCOUNT_EMAIL:-}
      GEE_PRIVATE_KEY_PATH: ${GEE_PRIVATE_KEY_PATH:-/run/secrets/gcp-sa.json}
```

**Verificación:**
```bash
grep -A 5 "GEE_PROJECT_ID" docker-compose.yml | head -20
# Debe aparecer dentro del bloque de worker-analysis
```

**Criterio de aceptación:** `worker-analysis` tiene las 3 variables GEE configuradas.

---

### CFG-002: comentar variables legacy GCS en todos los servicios

**Archivo:** `docker-compose.yml`  
**Servicios afectados:** `worker-ingestion`, `worker-clustering`, `worker-analysis`, `worker-reports`, `api`

**Contexto:** las variables `GOOGLE_APPLICATION_CREDENTIALS`, `GCS_SERVICE_ACCOUNT_JSON` y `GCS_PROJECT_ID` son legacy del antiguo backend GCS. OCI es el storage activo. Su presencia genera confusión operativa.

**Instrucciones:**

1. Buscar en **cada servicio** del `docker-compose.yml` las siguientes variables:
   - `GOOGLE_APPLICATION_CREDENTIALS`
   - `GCS_SERVICE_ACCOUNT_JSON`
   - `GCS_PROJECT_ID`
2. Comentarlas con un prefijo explicativo:

```yaml
      # LEGACY (GCS) — OCI es el storage backend activo
      # GOOGLE_APPLICATION_CREDENTIALS: ${GOOGLE_APPLICATION_CREDENTIALS:-/run/secrets/gcp-sa.json}
      # GCS_SERVICE_ACCOUNT_JSON: ${GCS_SERVICE_ACCOUNT_JSON:-/run/secrets/gcp-sa.json}
      # GCS_PROJECT_ID: ${GCS_PROJECT_ID:-}
```

**Verificación:**
```bash
grep -n "GOOGLE_APPLICATION_CREDENTIALS\|GCS_SERVICE_ACCOUNT_JSON\|GCS_PROJECT_ID" docker-compose.yml
# Todas las líneas deben estar comentadas (empezar con #)
```

**Criterio de aceptación:** ningún servicio tiene variables GCS activas; todas están comentadas con nota explicativa.

---

### SEC-001: agregar autenticación al router de monitoring

**Archivo:** `app/main.py`

**Contexto:** el router de monitoring está montado sin `dependencies=[Depends(get_current_user)]`, exponiendo datos de vegetación y cambios de uso del suelo sin autenticación. Esto viola la restricción de seguridad documentada.

**Instrucciones:**

1. Localizar en `app/main.py` el bloque donde se monta el router de monitoring. Buscar un patrón como:
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
)
```

2. Agregar la dependencia de autenticación:
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_user)],
)
```

3. Verificar que `get_current_user` esté importado. Buscar si ya está importado en el archivo (probablemente lo está, ya que otros routers como `reports` lo usan). Si no, agregar:
```python
from app.core.auth import get_current_user  # o la ruta correcta según el proyecto
```

**Verificación:**
```bash
grep -A 4 "monitoring.router" app/main.py
# Debe mostrar dependencies=[Depends(get_current_user)]
```

**Criterio de aceptación:** `GET /api/v1/monitoring/recovery/{id}` sin JWT retorna 401/403.

---

### SEC-002: sanitizar mensajes de error en monitoring

**Archivo:** `app/api/routes/monitoring.py`

**Contexto:** los `HTTPException` en este archivo exponen internals de GEE vía `str(e)` en el `detail`. Esto puede filtrar URLs internas, tokens de servicio o paths de infraestructura.

**Instrucciones:**

1. Buscar todos los bloques `except` que hagan `raise HTTPException(... detail=f"... {str(e)}")` o similar.
2. Reemplazar cada uno con el patrón:

```python
# ANTES (inseguro):
except Exception as e:
    raise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")

# DESPUÉS (seguro):
except Exception as e:
    logger.error(f"NDVI analysis failed for event {fire_event_id}: {e}", exc_info=True)
    raise HTTPException(
        status_code=503,
        detail="Servicio de análisis temporalmente no disponible. Intentá de nuevo más tarde."
    )
```

3. Asegurar que `logger` está importado al inicio del archivo:
```python
import logging
logger = logging.getLogger(__name__)
```

4. Aplicar el mismo patrón a **todos** los `except` del archivo que expongan `str(e)` en la respuesta HTTP. No solo el de NDVI; revisar también endpoints de land-use-changes y cualquier otro.

**Verificación:**
```bash
grep -n "str(e)" app/api/routes/monitoring.py
# No debe haber matches dentro de HTTPException.detail
# Sí puede haber matches dentro de logger.error (eso es correcto)
```

**Criterio de aceptación:** ningún `HTTPException` en monitoring.py incluye `str(e)` en su `detail`.

---

## Fase 1: correcciones de base de datos

### DB-001: insertar parámetro episode_temporal_window_hours

**Tipo:** migración SQL  
**Tabla:** `system_parameters`

**Contexto:** el default en código es 96 h (4 días), que causa extinción prematura de episodios. Debe ser 720 h (30 días). La tabla `system_parameters` ya existe con la estructura correcta.

**Instrucciones:**

Crear un archivo de migración SQL o ejecutar directamente. Si el proyecto usa Alembic, crear una migración. Si no, crear un script:

**Archivo a crear:** `scripts/migrations/set_episode_temporal_window.sql`

```sql
-- Corrige la ventana temporal de episodios de 4 días (96h) a 30 días (720h)
-- Esto permite que episodios en monitoring no se extingan prematuramente
INSERT INTO system_parameters (param_key, param_value, description, category)
VALUES (
    'episode_temporal_window_hours',
    '720'::jsonb,
    'Ventana temporal para declarar episodio extinto (en horas). 720h = 30 días.',
    'clustering'
)
ON CONFLICT (param_key) DO UPDATE
SET param_value = EXCLUDED.param_value,
    description = EXCLUDED.description,
    updated_at = NOW();
```

**Nota importante:** el campo `param_value` es de tipo `jsonb`. Verificar si el código lee el valor como `720` (número) o `"720"` (string). Ajustar el insert según corresponda. Si el servicio `episode_flow_parameters.py` hace `int(param_value)`, entonces `'720'::jsonb` es correcto (jsonb number). Si hace `json.loads()`, también funciona.

**Verificación:**
```sql
SELECT param_key, param_value, description
FROM system_parameters
WHERE param_key = 'episode_temporal_window_hours';
-- Debe retornar param_value = 720
```

**Criterio de aceptación:** el parámetro existe en `system_parameters` con valor 720.

---

### DB-002: safety en last_seen_at con COALESCE

**Archivo:** `app/services/episode_service.py` (o donde se implemente `_resolve_episode_status`)

**Contexto:** `fire_episodes.last_seen_at` puede ser NULL (no tiene NOT NULL ni default en el schema). Si la lógica de resolución de estados compara `now() - last_seen_at`, crashea con `TypeError`.

**Instrucciones:**

1. Localizar en `episode_service.py` (o el servicio equivalente) toda referencia a `last_seen_at` en cálculos temporales.
2. Reemplazar cada acceso directo con un fallback seguro:

```python
# ANTES:
elapsed = now - episode.last_seen_at

# DESPUÉS:
reference_date = episode.last_seen_at or episode.start_date
elapsed = now - reference_date
```

3. Si la comparación se hace en SQL (query directa), usar:
```sql
COALESCE(last_seen_at, start_date)
```

4. Adicionalmente, agregar un log de warning cuando `last_seen_at` es NULL para detectar datos inconsistentes:
```python
if episode.last_seen_at is None:
    logger.warning(f"Episode {episode.id} has NULL last_seen_at, using start_date as fallback")
```

**Verificación:**
```bash
grep -n "last_seen_at" app/services/episode_service.py
# Todo acceso a last_seen_at debe tener fallback a start_date
```

**Criterio de aceptación:** la lógica de estados no crashea si `last_seen_at` es NULL; usa `start_date` como fallback.

---

## Fase 2: lógica core de estados y endpoints

### CORE-001: refactorizar _resolve_episode_status

**Archivo:** `app/services/episode_service.py`  
**Método:** `_resolve_episode_status`

**Contexto:** este método es el single source of truth para el estado de un episodio. Debe implementar exactamente 3 reglas en orden de prioridad, desacoplando el ciclo de vida del evento del ciclo de vida del episodio.

**Instrucciones:**

1. Localizar el método `_resolve_episode_status` en `episode_service.py`.
2. Reemplazar la lógica existente con la siguiente implementación:

```python
from datetime import datetime, timezone, timedelta

def _resolve_episode_status(
    self,
    event_statuses: list[str],
    last_seen_at: datetime | None,
    start_date: datetime | None = None,
    window_hours: int | None = None,
) -> str:
    """Resuelve el estado de un episodio basándose en sus eventos y ventana temporal.

    Reglas (en orden de prioridad):
        1. Si al menos 1 evento está activo → 'active'
        2. Si pasó más tiempo que la ventana desde last_seen_at → 'extinct'
        3. En cualquier otro caso → 'monitoring'

    Args:
        event_statuses: lista de estados de los eventos asociados al episodio.
        last_seen_at: timestamp de la última actividad detectada.
        start_date: fallback si last_seen_at es None.
        window_hours: ventana temporal en horas. Si None, lee de system_parameters.

    Returns:
        Estado del episodio: 'active', 'monitoring' o 'extinct'.
    """
    # Regla 1: si hay al menos un evento activo, el episodio es activo
    if "active" in event_statuses:
        return "active"

    # Obtener ventana temporal
    if window_hours is None:
        window_hours = self._get_episode_window_hours()  # lee de system_parameters con fallback 720

    # Fecha de referencia con fallback seguro
    reference_date = last_seen_at or start_date
    if reference_date is None:
        logger.warning("Episode has no last_seen_at nor start_date, defaulting to monitoring")
        return "monitoring"

    # Asegurar timezone awareness
    now = datetime.now(timezone.utc)
    if reference_date.tzinfo is None:
        reference_date = reference_date.replace(tzinfo=timezone.utc)

    elapsed = now - reference_date
    window = timedelta(hours=window_hours)

    # Regla 2: si superó la ventana, extinto
    if elapsed >= window:
        return "extinct"

    # Regla 3: en cualquier otro caso, monitoring
    return "monitoring"
```

3. Verificar que el método `_get_episode_window_hours` existe. Si no existe, crearlo:

```python
def _get_episode_window_hours(self) -> int:
    """Lee episode_temporal_window_hours de system_parameters con fallback a 720."""
    try:
        from app.services.episode_flow_parameters import get_parameter
        value = get_parameter("episode_temporal_window_hours")
        return int(value) if value is not None else 720
    except Exception:
        logger.warning("Could not read episode_temporal_window_hours, using default 720")
        return 720
```

4. Verificar que este método se invoque correctamente desde `update_episode_metrics` o cualquier otro caller, pasándole `episode.last_seen_at` y `episode.start_date`.

**Verificación:**
```bash
grep -n "_resolve_episode_status" app/services/episode_service.py
# Debe existir y tener la firma con last_seen_at, start_date, window_hours
```

**Criterio de aceptación:**
- Episodio con evento activo → retorna "active"
- Episodio sin eventos activos, dentro de ventana 720h → retorna "monitoring"
- Episodio sin eventos activos, fuera de ventana 720h → retorna "extinct"
- Episodio con `last_seen_at = None` → no crashea, usa fallback

---

### CORE-002: actualizar defaults canónicos

**Archivo:** `app/services/episode_flow_parameters.py`  
**Diccionario:** `CANONICAL_EPISODE_FLOW_DEFAULTS` (o el nombre equivalente)

**Instrucciones:**

1. Localizar el diccionario de defaults en `episode_flow_parameters.py`.
2. Modificar `episode_temporal_window_hours` de `96` a `720`:

```python
CANONICAL_EPISODE_FLOW_DEFAULTS = {
    "event_temporal_window_hours": 48,         # 2 días — ventana entre detecciones
    "event_monitoring_window_hours": 168,       # 7 días — vida de un evento en monitoring
    "episode_temporal_window_hours": 720,       # 30 días — vida de un episodio antes de extinct (CORREGIDO de 96)
    # ... otros parámetros existentes ...
}
```

3. **No tocar** `event_monitoring_window_hours` (debe permanecer en 168 o el valor actual).

**Verificación:**
```bash
grep "episode_temporal_window_hours" app/services/episode_flow_parameters.py
# Debe mostrar 720
```

**Criterio de aceptación:** el fallback en código es 720 h, alineado con el valor en `system_parameters`.

---

### CORE-003: filtro de slides_data en endpoint de episodios activos

**Archivo:** el archivo que implementa el endpoint de listado de episodios para el carrusel/home. Buscar en:
- `app/api/routes/episodes.py`
- `app/api/v1/fire_events.py`
- `app/api/v1/episodes.py`
- O el servicio que arma la query de episodios para `mode=active`

**Contexto:** el endpoint que alimenta el home debe retornar solo episodios que tengan thumbnails listos. Sin este filtro, el frontend puede recibir episodios sin imágenes y mostrar tarjetas vacías.

**Instrucciones:**

1. Localizar la query que se ejecuta cuando el frontend pide episodios activos (probablemente `GET /fire-episodes?mode=active` o similar).
2. Agregar la condición de filtro:

**Si la query es SQLAlchemy ORM:**
```python
# Agregar al filtro existente
query = query.filter(
    FireEpisode.status.in_(["active", "monitoring"]),
    FireEpisode.gee_candidate == True,
    # NUEVO: solo episodios con thumbnails listos
    FireEpisode.slides_data.isnot(None),
    func.jsonb_array_length(FireEpisode.slides_data) > 0,
)
```

**Si la query es SQL raw:**
```sql
AND slides_data IS NOT NULL
AND jsonb_array_length(slides_data) > 0
```

3. **Importante:** este filtro solo aplica cuando el modo es `active` (para el home/carrusel). No aplicarlo en modo `history` o queries administrativas.

**Verificación:**
```bash
# Buscar la query de episodios activos
grep -n "mode.*active\|status.*IN.*active.*monitoring" app/api/routes/episodes.py app/api/v1/*.py app/services/episode_service.py 2>/dev/null
# Luego verificar que la misma función incluye filtro de slides_data
```

**Criterio de aceptación:** `GET /fire-episodes?mode=active` (o equivalente) no retorna episodios con `slides_data` vacío o NULL.

---

## Fase 3: hardening del carousel worker

### WORK-001: Redis lock para evitar ejecuciones concurrentes

**Archivo:** `workers/tasks/carousel_task.py`

**Contexto:** si Celery beat y un trigger manual ejecutan el carousel simultáneamente, ambas instancias procesan los mismos episodios, desperdiciando cuota GEE y produciendo escrituras no deterministas.

**Instrucciones:**

1. Al inicio de la función principal del carousel task (probablemente `generate_carousel`), agregar un lock distribuido con Redis:

```python
import redis
import logging

logger = logging.getLogger(__name__)

CAROUSEL_LOCK_KEY = "carousel:generation_lock"
CAROUSEL_LOCK_TTL = 3600  # 1 hora máximo

def _acquire_lock() -> bool:
    """Intenta adquirir lock distribuido para ejecución del carrusel."""
    try:
        from app.core.config import settings
        r = redis.Redis.from_url(settings.REDIS_URL or "redis://redis:6379/0")
        acquired = r.set(CAROUSEL_LOCK_KEY, "running", nx=True, ex=CAROUSEL_LOCK_TTL)
        return bool(acquired)
    except Exception as e:
        logger.warning(f"Could not acquire carousel lock: {e}. Proceeding anyway.")
        return True  # Si Redis falla, no bloquear la ejecución

def _release_lock():
    """Libera el lock del carrusel."""
    try:
        from app.core.config import settings
        r = redis.Redis.from_url(settings.REDIS_URL or "redis://redis:6379/0")
        r.delete(CAROUSEL_LOCK_KEY)
    except Exception as e:
        logger.warning(f"Could not release carousel lock: {e}")
```

2. Integrar en la task principal:

```python
@celery_app.task(bind=True)
def generate_carousel(self, force_refresh: bool = False, **kwargs):
    if not _acquire_lock():
        logger.info("Carousel generation already in progress (lock held). Skipping.")
        return {"skipped": True, "reason": "lock_held"}

    try:
        # ... lógica existente del carousel ...
        result = _process_carousel(force_refresh=force_refresh)
        return result
    finally:
        _release_lock()
```

**Verificación:**
```bash
grep -n "CAROUSEL_LOCK\|acquire_lock\|release_lock" workers/tasks/carousel_task.py
# Debe existir la lógica de lock
```

**Criterio de aceptación:** dos ejecuciones simultáneas no procesan los mismos episodios; la segunda se salta con `skipped: True`.

---

### WORK-002: retry con backoff exponencial por episodio

**Archivo:** `workers/tasks/carousel_task.py` (o `app/services/imagery_service.py`)

**Contexto:** si GEE falla para un episodio específico, la tarea no debe abortar el batch completo. Debe reintentar con backoff y, tras 3 fallos, loguear el error y continuar con el siguiente episodio.

**Instrucciones:**

1. Localizar el loop principal que procesa episodios (probablemente en `imagery_service.py` dentro del método que genera thumbnails).
2. Envolver el procesamiento de cada episodio individual con retry:

```python
import time

MAX_RETRIES_PER_EPISODE = 3
BACKOFF_DELAYS = [30, 60, 120]  # segundos

def _process_single_episode(self, episode, force_refresh: bool = False) -> dict:
    """Procesa un episodio con retry y backoff."""
    for attempt in range(MAX_RETRIES_PER_EPISODE):
        try:
            result = self._generate_thumbnails_for_episode(episode, force_refresh)
            return {"status": "success", "episode_id": str(episode.id), **result}
        except Exception as e:
            delay = BACKOFF_DELAYS[attempt] if attempt < len(BACKOFF_DELAYS) else BACKOFF_DELAYS[-1]
            logger.warning(
                f"Carousel: episode {episode.id} attempt {attempt + 1}/{MAX_RETRIES_PER_EPISODE} "
                f"failed: {e}. Retrying in {delay}s."
            )
            if attempt < MAX_RETRIES_PER_EPISODE - 1:
                time.sleep(delay)
            else:
                logger.error(
                    f"Carousel: episode {episode.id} failed after {MAX_RETRIES_PER_EPISODE} attempts: {e}",
                    exc_info=True
                )
                return {"status": "error", "episode_id": str(episode.id), "error": str(e)}
```

3. **No** usar `self.retry()` de Celery para esto (eso reintenta la task completa). Los reintentos son **dentro** del loop por episodio.

**Verificación:**
```bash
grep -n "MAX_RETRIES_PER_EPISODE\|BACKOFF_DELAYS\|attempt.*failed" workers/tasks/carousel_task.py app/services/imagery_service.py
```

**Criterio de aceptación:** un fallo de GEE en un episodio no detiene el batch; se reintenta 3 veces con backoff 30s/60s/120s; tras 3 fallos, se loguea y continúa.

---

### WORK-003: escritura atómica de slides_data

**Archivo:** `app/services/imagery_service.py` (o donde se actualiza `fire_episodes.slides_data`)

**Contexto:** si la generación de thumbnails falla a mitad de camino (por ejemplo, se generan 2 de 3), `slides_data` podría quedar con datos parciales. La UI espera exactamente 3 slides.

**Instrucciones:**

1. Localizar el punto donde se actualiza `fire_episodes.slides_data` (probablemente cerca de las líneas 767-770 de `imagery_service.py`).
2. Asegurar que la escritura solo ocurre cuando los 3 thumbnails se generaron correctamente:

```python
def _update_episode_slides(self, episode_id, slides: list[dict], db_session):
    """Actualiza slides_data solo si tiene exactamente 3 slides completos.

    Args:
        episode_id: UUID del episodio.
        slides: lista de 3 dicts con type, thumbnail_url, satellite_image_id, generated_at.
        db_session: sesión de SQLAlchemy.
    """
    # Validación: deben ser exactamente 3 slides con todos los campos requeridos
    required_keys = {"type", "thumbnail_url", "satellite_image_id", "generated_at"}
    valid_types = {"rgb", "swir", "nbr"}

    if len(slides) != 3:
        logger.error(f"Episode {episode_id}: expected 3 slides, got {len(slides)}. Skipping update.")
        return False

    slide_types = set()
    for slide in slides:
        if not required_keys.issubset(slide.keys()):
            missing = required_keys - slide.keys()
            logger.error(f"Episode {episode_id}: slide missing keys {missing}. Skipping update.")
            return False
        if not slide.get("thumbnail_url"):
            logger.error(f"Episode {episode_id}: slide has empty thumbnail_url. Skipping update.")
            return False
        slide_types.add(slide["type"])

    if slide_types != valid_types:
        logger.error(f"Episode {episode_id}: slide types {slide_types} != {valid_types}. Skipping update.")
        return False

    # Escritura atómica: todo o nada
    episode = db_session.query(FireEpisode).filter_by(id=episode_id).first()
    if episode:
        episode.slides_data = slides
        episode.updated_at = datetime.now(timezone.utc)
        db_session.commit()
        logger.info(f"Episode {episode_id}: slides_data updated with 3 valid slides.")
        return True
    return False
```

3. En el flujo principal, acumular los 3 slides en una lista temporal antes de escribir:

```python
# En el loop de generación de thumbnails por episodio:
slides_buffer = []
for vis_type in ["rgb", "swir", "nbr"]:
    thumbnail_url = self._generate_and_upload_thumbnail(episode, vis_type, ...)
    if thumbnail_url:
        slides_buffer.append({
            "type": vis_type,
            "thumbnail_url": thumbnail_url,
            "satellite_image_id": str(sat_image.id),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

# Solo escribir si los 3 están listos
self._update_episode_slides(episode.id, slides_buffer, db)
```

**Criterio de aceptación:** `fire_episodes.slides_data` siempre tiene 0 o 3 slides; nunca 1 o 2.

---

### WORK-004: logging estructurado del carousel

**Archivo:** `workers/tasks/carousel_task.py`

**Instrucciones:**

1. Al finalizar el procesamiento del batch, emitir un log resumen con formato JSON:

```python
import json

def _log_carousel_summary(results: list[dict]):
    """Emite log estructurado con resumen de la ejecución del carrusel."""
    summary = {
        "event": "carousel_run_complete",
        "episodes_found": len(results),
        "processed": sum(1 for r in results if r.get("status") == "success"),
        "cache_hits": sum(1 for r in results if r.get("status") == "cache_hit"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "error_details": [
            {"episode_id": r["episode_id"], "error": r.get("error", "unknown")}
            for r in results if r.get("status") == "error"
        ],
    }
    logger.info(json.dumps(summary))
    return summary
```

2. Integrar al final de la task principal:

```python
# Al final de generate_carousel:
summary = _log_carousel_summary(results)
return summary
```

**Criterio de aceptación:** cada ejecución del carousel produce un log JSON con contadores de processed, cache_hits, errors.

---

## Fase 4: rate limiting y validación de inputs

### SEC-003: rate limiter en endpoints de generación de imágenes

**Archivos:**
- `app/api/v1/imagery.py` (endpoint `POST /imagery/refresh/{episode_id}`)
- `app/api/routes/monitoring.py` (endpoint `POST /monitoring/recovery/trigger` si existe)

**Contexto:** estos endpoints disparan operaciones costosas contra GEE. Sin rate limiting, un usuario puede agotar la cuota diaria de 50 000 requests. El límite definido es **5 requests cada 6 horas por usuario autenticado**.

**Instrucciones:**

1. Verificar si existe `app/core/rate_limiter.py`. Si existe, revisar si tiene una función `check_rate_limit` o similar que pueda parametrizarse.

2. **Si existe y es parametrizable**, crear un limiter específico para generación:

```python
# En el archivo del endpoint (imagery.py o monitoring.py)
from app.core.rate_limiter import create_rate_limiter

# 5 requests cada 6 horas (21600 segundos) por usuario autenticado
imagery_rate_limit = create_rate_limiter(
    max_requests=5,
    window_seconds=21600,  # 6 horas
    key_func=lambda request: f"imagery:{request.state.user_id}",  # por usuario
)
```

3. **Si no existe o no es parametrizable**, implementar un rate limiter basado en Redis:

```python
# app/core/imagery_rate_limiter.py
import time
import redis
from fastapi import HTTPException, Request, Depends
from app.core.auth import get_current_user

IMAGERY_RATE_LIMIT = 5          # máximo de requests
IMAGERY_RATE_WINDOW = 21600     # 6 horas en segundos

async def check_imagery_rate_limit(
    request: Request,
    current_user=Depends(get_current_user),
):
    """Rate limiter: 5 requests cada 6 horas por usuario autenticado.

    Protege endpoints que consumen cuota GEE (generación de imágenes satelitales).
    """
    user_id = str(current_user.id)
    key = f"rate:imagery:{user_id}"

    try:
        r = redis.Redis.from_url(request.app.state.redis_url or "redis://redis:6379/0")
        current_count = r.get(key)

        if current_count is not None and int(current_count) >= IMAGERY_RATE_LIMIT:
            ttl = r.ttl(key)
            hours_remaining = max(1, ttl // 3600)
            raise HTTPException(
                status_code=429,
                detail=f"Límite de generación de imágenes alcanzado ({IMAGERY_RATE_LIMIT} cada 6 horas). "
                       f"Intentá de nuevo en ~{hours_remaining}h.",
                headers={"Retry-After": str(ttl)},
            )

        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, IMAGERY_RATE_WINDOW)
        pipe.execute()

    except redis.RedisError as e:
        # Si Redis no está disponible, permitir la request pero loguear
        import logging
        logging.getLogger(__name__).warning(f"Rate limiter Redis error: {e}. Allowing request.")
```

4. Aplicar el limiter como dependencia en los endpoints:

```python
# En imagery.py:
@router.post(
    "/refresh/{episode_id}",
    dependencies=[Depends(check_imagery_rate_limit)],
)
async def refresh_episode_imagery(episode_id: str, ...):
    ...

# En monitoring.py (si existe POST /trigger):
@router.post(
    "/recovery/trigger",
    dependencies=[Depends(check_imagery_rate_limit)],
)
async def trigger_recovery_analysis(...):
    ...
```

**Verificación:**
```bash
grep -n "check_imagery_rate_limit\|imagery_rate_limit\|rate.*imagery" app/api/v1/imagery.py app/api/routes/monitoring.py app/core/imagery_rate_limiter.py 2>/dev/null
```

**Criterio de aceptación:**
- 5 requests seguidos → 200/202 (OK)
- 6to request → 429 con header `Retry-After`
- El límite es por usuario autenticado, no global
- Ventana de 6 horas (21600 segundos)

---

### SEC-004: hard cap de page_size en endpoints de episodios

**Archivos:** buscar en:
- `app/api/routes/episodes.py`
- `app/api/v1/fire_events.py`
- Cualquier endpoint que acepte `page_size` o `limit` para episodios

**Instrucciones:**

1. Localizar todos los parámetros de paginación (`page_size`, `limit`, `page`) en endpoints de episodios.
2. Asegurar que usen `Query` con validación:

```python
from fastapi import Query

@router.get("/fire-episodes")
async def list_episodes(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Items por página (máx 100)"),
    mode: str = Query("active", description="Modo: active, history"),
):
    ...
```

3. Si algún endpoint usa `limit` sin cap, agregar `le=100`:
```python
limit: int = Query(20, ge=1, le=100)
```

**Criterio de aceptación:** `page_size=101` o `limit=101` retorna HTTP 422.

---

## Fase 5: scripts de mantenimiento

### SCRIPT-001: recálculo retroactivo de episodios extintos prematuramente

**Archivo a crear:** `scripts/recalculate_episodes.py`

**Contexto:** episodios que fueron marcados como `extinct` por la ventana de 4 días deben ser re-evaluados con la nueva ventana de 30 días. Los que tengan `last_seen_at` dentro de los últimos 30 días deben transicionar a `monitoring`.

**Instrucciones:**

Crear el siguiente script:

```python
#!/usr/bin/env python3
"""Recalcula episodios extintos prematuramente por la ventana de 4 días.

Uso:
    docker exec -it forestguard-api python scripts/recalculate_episodes.py [--dry-run]

Este script:
1. Busca episodios con status='extinct' cuyo last_seen_at es < 30 días atrás.
2. Re-evalúa cada uno con la lógica corregida de _resolve_episode_status.
3. Los que correspondan pasan a 'monitoring'.
"""
import sys
import os
import argparse
import logging
from datetime import datetime, timezone, timedelta

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Recalcula episodios extintos prematuramente")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra qué haría sin modificar")
    args = parser.parse_args()

    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        cutoff_str = cutoff.isoformat()

        # Buscar episodios extintos cuyo last_seen_at es reciente (< 30 días)
        query = text("""
            SELECT id, status, last_seen_at, start_date,
                   COALESCE(last_seen_at, start_date) as reference_date
            FROM fire_episodes
            WHERE status = 'extinct'
              AND COALESCE(last_seen_at, start_date) > :cutoff
            ORDER BY COALESCE(last_seen_at, start_date) DESC
        """)

        result = db.execute(query, {"cutoff": cutoff_str})
        candidates = result.fetchall()

        logger.info(f"Found {len(candidates)} episodes extinct within last 30 days")

        reactivated = 0
        for row in candidates:
            ep_id = row.id
            ref_date = row.reference_date
            logger.info(f"  Episode {ep_id}: reference_date={ref_date}")

            if not args.dry_run:
                update = text("""
                    UPDATE fire_episodes
                    SET status = 'monitoring', updated_at = NOW()
                    WHERE id = :ep_id AND status = 'extinct'
                """)
                db.execute(update, {"ep_id": str(ep_id)})
                reactivated += 1

        if not args.dry_run:
            db.commit()
            logger.info(f"Reactivated {reactivated} episodes from 'extinct' to 'monitoring'")
        else:
            logger.info(f"DRY RUN: would reactivate {len(candidates)} episodes")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Verificación:**
```bash
# Dry run primero
docker exec -it forestguard-api python scripts/recalculate_episodes.py --dry-run

# Si el output es correcto, ejecutar en producción
docker exec -it forestguard-api python scripts/recalculate_episodes.py
```

**Criterio de aceptación:** episodios extintos con `last_seen_at` < 30 días transicionan a `monitoring`.

---

### SCRIPT-002: verificación end-to-end post-deploy

**Archivo a crear:** `scripts/verify_carousel.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "=== Verificación E2E del carrusel ==="
echo ""

# 1. Verificar variables GEE en worker-analysis
echo "1. Variables GEE en worker-analysis..."
docker exec forestguard-worker-analysis env | grep -q "GEE_PROJECT_ID" && \
  echo "   ✓ GEE_PROJECT_ID presente" || \
  echo "   ✗ GEE_PROJECT_ID FALTANTE"

docker exec forestguard-worker-analysis env | grep -q "GEE_SERVICE_ACCOUNT_EMAIL" && \
  echo "   ✓ GEE_SERVICE_ACCOUNT_EMAIL presente" || \
  echo "   ✗ GEE_SERVICE_ACCOUNT_EMAIL FALTANTE"

# 2. Verificar parámetro en system_parameters
echo ""
echo "2. Parámetro episode_temporal_window_hours..."
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
r = db.execute(text(\"SELECT param_value FROM system_parameters WHERE param_key = 'episode_temporal_window_hours'\")).scalar()
print(f'   Valor: {r}')
assert r is not None, 'FALTANTE'
db.close()
"

# 3. Verificar candidatos
echo ""
echo "3. Estado de episodios..."
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
r = db.execute(text(\"\"\"
    SELECT status, count(*)
    FROM fire_episodes
    WHERE gee_candidate = true
    GROUP BY status
    ORDER BY status
\"\"\")).fetchall()
for row in r:
    print(f'   {row[0]}: {row[1]}')
db.close()
"

# 4. Verificar slides
echo ""
echo "4. Episodios con slides..."
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
total = db.execute(text(\"SELECT count(*) FROM fire_episodes WHERE status IN ('active','monitoring') AND gee_candidate\")).scalar()
with_slides = db.execute(text(\"SELECT count(*) FROM fire_episodes WHERE status IN ('active','monitoring') AND gee_candidate AND slides_data IS NOT NULL AND jsonb_array_length(slides_data) > 0\")).scalar()
print(f'   Candidatos: {total}, Con slides: {with_slides}')
db.close()
"

echo ""
echo "=== Verificación completada ==="
```

**Criterio de aceptación:** el script corre sin errores y muestra métricas coherentes.

---

## Fase 6: documentación

### DOC-001: deprecar fire_events.slides_data

**Archivos a modificar:**

1. **Schema/modelo SQLAlchemy** (probablemente `app/models/fire_event.py` o similar):
   - Agregar comentario al campo:
```python
slides_data = Column(JSONB, default=[], server_default='[]',
                     comment="DEPRECATED: usar fire_episodes.slides_data para el carrusel. "
                             "Este campo se mantiene por compatibilidad pero no debe escribirse.")
```

2. **Documentación del proyecto** (si existe `docs/` o `CLAUDE.md`):
   - Agregar nota:
```markdown
> **Nota:** `fire_events.slides_data` está deprecado. La fuente de verdad para el carrusel es
> `fire_episodes.slides_data` (cache UI, 3 slides) respaldado por `satellite_images` (metadata completa).
```

**Criterio de aceptación:** el campo está marcado como deprecated en modelo y documentación.

---

## Fase 7: tests de regresión

### TEST-001: unit tests de resolución de estados

**Archivo a crear:** `tests/unit/test_episode_status_resolver.py`

```python
"""Tests para _resolve_episode_status — single source of truth de estados de episodio."""
import pytest
from datetime import datetime, timezone, timedelta


class TestResolveEpisodeStatus:
    """Cada test valida una regla específica del resolver de estados."""

    def _resolve(self, event_statuses, last_seen_at=None, start_date=None, window_hours=720):
        """Helper que importa y ejecuta el resolver.

        Ajustar el import según la ubicación real del método.
        """
        from app.services.episode_service import EpisodeService
        # Si el método es estático o de instancia, ajustar:
        # Opción A: método estático
        # return EpisodeService._resolve_episode_status(event_statuses, last_seen_at, start_date, window_hours)
        # Opción B: necesita instancia (mock db)
        from unittest.mock import MagicMock
        service = EpisodeService(db=MagicMock())
        return service._resolve_episode_status(
            event_statuses=event_statuses,
            last_seen_at=last_seen_at,
            start_date=start_date,
            window_hours=window_hours,
        )

    def test_active_when_any_event_active(self):
        result = self._resolve(
            event_statuses=["active", "monitoring", "extinct"],
            last_seen_at=datetime.now(timezone.utc),
        )
        assert result == "active"

    def test_active_single_event(self):
        result = self._resolve(
            event_statuses=["active"],
            last_seen_at=datetime.now(timezone.utc),
        )
        assert result == "active"

    def test_monitoring_within_window(self):
        result = self._resolve(
            event_statuses=["monitoring", "extinct"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=15),
            window_hours=720,
        )
        assert result == "monitoring"

    def test_monitoring_all_extinct_but_recent(self):
        result = self._resolve(
            event_statuses=["extinct", "extinct"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=5),
            window_hours=720,
        )
        assert result == "monitoring"

    def test_extinct_beyond_window(self):
        result = self._resolve(
            event_statuses=["extinct", "extinct"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=35),
            window_hours=720,
        )
        assert result == "extinct"

    def test_extinct_exactly_at_window_boundary(self):
        result = self._resolve(
            event_statuses=["extinct"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(hours=720),
            window_hours=720,
        )
        assert result == "extinct"

    def test_monitoring_just_before_window_boundary(self):
        result = self._resolve(
            event_statuses=["extinct"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(hours=719),
            window_hours=720,
        )
        assert result == "monitoring"

    def test_fallback_to_start_date_when_last_seen_none(self):
        result = self._resolve(
            event_statuses=["extinct"],
            last_seen_at=None,
            start_date=datetime.now(timezone.utc) - timedelta(days=5),
            window_hours=720,
        )
        assert result == "monitoring"

    def test_no_crash_when_both_dates_none(self):
        result = self._resolve(
            event_statuses=["extinct"],
            last_seen_at=None,
            start_date=None,
            window_hours=720,
        )
        assert result == "monitoring"  # safe default

    def test_old_4day_bug_produces_premature_extinct(self):
        """Documenta el bug original: ventana de 96h extingue episodio en 5 días."""
        result = self._resolve(
            event_statuses=["monitoring"],
            last_seen_at=datetime.now(timezone.utc) - timedelta(days=5),
            window_hours=96,
        )
        assert result == "extinct"  # Bug: episodio muere antes que su evento
```

---

### TEST-002: unit tests de validación de slides_data

**Archivo a crear:** `tests/unit/test_slides_data_schema.py`

```python
"""Validación del contrato de slides_data."""
import pytest

VALID_SLIDE_TYPES = {"rgb", "swir", "nbr"}
REQUIRED_SLIDE_KEYS = {"type", "thumbnail_url", "satellite_image_id", "generated_at"}


@pytest.fixture
def valid_slides():
    return [
        {"type": "rgb", "thumbnail_url": "https://oci.example.com/rgb.png",
         "satellite_image_id": "si-001", "generated_at": "2026-02-23T03:00:00Z"},
        {"type": "swir", "thumbnail_url": "https://oci.example.com/swir.png",
         "satellite_image_id": "si-002", "generated_at": "2026-02-23T03:00:00Z"},
        {"type": "nbr", "thumbnail_url": "https://oci.example.com/nbr.png",
         "satellite_image_id": "si-003", "generated_at": "2026-02-23T03:00:00Z"},
    ]


@pytest.fixture
def incomplete_slides():
    return [{"type": "rgb"}]  # falta thumbnail_url y otros


@pytest.fixture
def duplicate_type_slides():
    return [
        {"type": "rgb", "thumbnail_url": "a.png", "satellite_image_id": "1", "generated_at": "t"},
        {"type": "rgb", "thumbnail_url": "b.png", "satellite_image_id": "2", "generated_at": "t"},
        {"type": "nbr", "thumbnail_url": "c.png", "satellite_image_id": "3", "generated_at": "t"},
    ]


def validate_slides(slides: list[dict]) -> tuple[bool, str]:
    """Replica la lógica de validación de _update_episode_slides."""
    if slides is None or len(slides) != 3:
        return False, f"Expected 3 slides, got {len(slides) if slides else 0}"
    types = set()
    for s in slides:
        if not REQUIRED_SLIDE_KEYS.issubset(s.keys()):
            return False, f"Missing keys: {REQUIRED_SLIDE_KEYS - s.keys()}"
        if not s.get("thumbnail_url"):
            return False, "Empty thumbnail_url"
        types.add(s["type"])
    if types != VALID_SLIDE_TYPES:
        return False, f"Types {types} != {VALID_SLIDE_TYPES}"
    return True, "OK"


class TestSlidesDataValidation:

    def test_valid_slides_pass(self, valid_slides):
        ok, msg = validate_slides(valid_slides)
        assert ok, msg

    def test_none_slides_fail(self):
        ok, _ = validate_slides(None)
        assert not ok

    def test_empty_slides_fail(self):
        ok, _ = validate_slides([])
        assert not ok

    def test_partial_slides_fail(self):
        ok, _ = validate_slides([{"type": "rgb", "thumbnail_url": "a.png",
                                   "satellite_image_id": "1", "generated_at": "t"}])
        assert not ok

    def test_incomplete_slide_fail(self, incomplete_slides):
        ok, _ = validate_slides(incomplete_slides)
        assert not ok

    def test_duplicate_types_fail(self, duplicate_type_slides):
        ok, _ = validate_slides(duplicate_type_slides)
        assert not ok

    def test_empty_thumbnail_url_fail(self, valid_slides):
        valid_slides[1]["thumbnail_url"] = ""
        ok, _ = validate_slides(valid_slides)
        assert not ok
```

---

### TEST-003: integration tests de endpoint carrusel

**Archivo a crear:** `tests/integration/test_carousel_endpoint.py`

```python
"""Tests de integración para el endpoint de episodios del carrusel.

Estos tests requieren una base de datos de test. Ajustar fixtures según
la infraestructura de testing del proyecto (pytest-asyncio, httpx, etc.).
"""
import pytest


class TestCarouselEndpoint:
    """Tests del endpoint que alimenta el home con episodios + thumbnails."""

    @pytest.mark.integration
    def test_active_episodes_have_slides(self, client, db_with_episodes):
        """GET /fire-episodes?mode=active solo retorna episodios con slides."""
        response = client.get("/api/v1/fire-episodes?mode=active")
        assert response.status_code == 200
        data = response.json()
        for ep in data.get("items", data.get("data", [])):
            assert ep.get("slides_data") is not None, f"Episode {ep['id']} has null slides_data"
            assert len(ep["slides_data"]) == 3, f"Episode {ep['id']} has {len(ep['slides_data'])} slides"

    @pytest.mark.integration
    def test_monitoring_endpoints_require_auth(self, client):
        """GET /monitoring/recovery/{id} sin JWT retorna 401."""
        response = client.get("/api/v1/monitoring/recovery/00000000-0000-0000-0000-000000000000")
        assert response.status_code in (401, 403)

    @pytest.mark.integration
    def test_page_size_hard_cap(self, client):
        """page_size > 100 retorna 422."""
        response = client.get("/api/v1/fire-episodes?page_size=101")
        assert response.status_code == 422

    @pytest.mark.integration
    def test_page_size_zero_rejected(self, client):
        """page_size = 0 retorna 422."""
        response = client.get("/api/v1/fire-episodes?page_size=0")
        assert response.status_code == 422

    @pytest.mark.integration
    def test_error_messages_no_internals(self, client, auth_headers):
        """Errores no exponen paths internos ni tokens."""
        # Provocar un error con un ID inválido
        response = client.get(
            "/api/v1/monitoring/recovery/not-a-uuid",
            headers=auth_headers,
        )
        if response.status_code >= 400:
            body = response.json()
            detail = str(body.get("detail", ""))
            assert "/run/secrets" not in detail
            assert "GEE_" not in detail
            assert "oci.oraclecloud.com" not in detail
```

---

### TEST-004: worker tests

**Archivo a crear:** `tests/worker/test_carousel_worker.py`

```python
"""Tests del carousel worker.

Estos tests requieren Redis para lock testing.
Ajustar mocks según la implementación real.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestCarouselWorkerLock:
    """Tests del mecanismo de lock distribuido."""

    @pytest.mark.worker
    def test_lock_prevents_concurrent_execution(self):
        """Segunda ejecución se salta si hay lock activo."""
        import redis
        r = redis.Redis.from_url("redis://localhost:6379/0")

        # Simular lock activo
        r.set("carousel:generation_lock", "running", nx=True, ex=3600)

        from workers.tasks.carousel_task import _acquire_lock
        assert not _acquire_lock()

        # Limpiar
        r.delete("carousel:generation_lock")

    @pytest.mark.worker
    def test_lock_released_after_execution(self):
        """El lock se libera al terminar la ejecución."""
        import redis
        r = redis.Redis.from_url("redis://localhost:6379/0")
        r.delete("carousel:generation_lock")  # asegurar limpio

        from workers.tasks.carousel_task import _acquire_lock, _release_lock
        assert _acquire_lock()
        _release_lock()
        assert r.get("carousel:generation_lock") is None


class TestCarouselWorkerProcessing:
    """Tests de procesamiento de episodios."""

    @pytest.mark.worker
    def test_gee_failure_does_not_crash_batch(self):
        """Fallo de GEE en un episodio no detiene el resto."""
        # Este test requiere mocking de GEEService e ImageryService
        # Estructura:
        # 1. Mock GEE para que falle en episodio 1, funcione en episodio 2
        # 2. Ejecutar carousel
        # 3. Verificar que episodio 2 fue procesado
        pass  # Implementar según estructura real de mocks

    @pytest.mark.worker
    def test_slides_data_never_partial(self):
        """slides_data tiene 0 o 3 slides, nunca parcial."""
        # Mock que falla en el tercer thumbnail
        # Verificar que slides_data no se actualiza con 2 slides
        pass  # Implementar según estructura real
```

---

### TEST-005: E2E frontend tests

**Archivo a crear:** `frontend/tests/e2e/carousel.spec.ts` (o `tests/e2e/carousel.spec.ts`)

```typescript
/**
 * Tests E2E del carrusel en el home.
 * Requiere Playwright configurado en el proyecto frontend.
 */
import { test, expect } from '@playwright/test';

test.describe('Carrusel del home', () => {

  test('no muestra tarjetas sin thumbnail', async ({ page }) => {
    await page.goto('/');
    // Esperar que carguen las tarjetas
    await page.waitForSelector('[data-testid="fire-card"], [data-testid="empty-state"]', {
      timeout: 10000,
    });

    const cards = page.locator('[data-testid="fire-card"]');
    const count = await cards.count();

    for (let i = 0; i < count; i++) {
      const img = cards.nth(i).locator('img').first();
      const src = await img.getAttribute('src');
      expect(src).toBeTruthy();
      expect(src).toMatch(/https?:\/\/.+/);
    }
  });

  test('cada tarjeta tiene 3 slides navegables', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('[data-testid="fire-card"]', { timeout: 10000 });

    const firstCard = page.locator('[data-testid="fire-card"]').first();
    const indicators = firstCard.locator(
      '[data-testid="slide-indicator"], [data-testid="carousel-dot"]'
    );
    // Debe haber indicadores para 3 slides
    await expect(indicators).toHaveCount(3);
  });

  test('layout responsive en mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.waitForSelector('[data-testid="fire-card"], [data-testid="empty-state"]', {
      timeout: 10000,
    });

    const card = page.locator('[data-testid="fire-card"]').first();
    if (await card.isVisible()) {
      const box = await card.boundingBox();
      expect(box!.width).toBeLessThanOrEqual(375);
    }
  });
});
```

---

## Orden de ejecución recomendado

```
Fase 0 (paralelo, sin dependencias):
  CFG-001 ──┐
  CFG-002 ──┤── Pueden ejecutarse todas en paralelo
  SEC-001 ──┤
  SEC-002 ──┘

Fase 1 (secuencial):
  DB-001 ──→ DB-002

Fase 2 (depende de fase 1):
  CORE-001 ──→ CORE-002 ──→ CORE-003

Fase 3 (paralelo entre sí, depende de fase 2):
  WORK-001 ──┐
  WORK-002 ──┤── Paralelos
  WORK-003 ──┤
  WORK-004 ──┘

Fase 4 (paralelo, independiente):
  SEC-003 ──┐
  SEC-004 ──┘

Fase 5 (depende de fase 2 + 3):
  SCRIPT-001 ──→ SCRIPT-002

Fase 6 (independiente):
  DOC-001

Fase 7 (depende de las fases que testea):
  TEST-001 ──┐
  TEST-002 ──┤
  TEST-003 ──┤── Paralelos
  TEST-004 ──┤
  TEST-005 ──┘
```

---

## Checklist de cierre post-ejecución

- [ ] `docker-compose.yml` — worker-analysis tiene GEE vars, GCS vars comentadas en todos los servicios
- [ ] `main.py` — monitoring router con `Depends(get_current_user)`
- [ ] `monitoring.py` — sin `str(e)` en HTTPException.detail
- [ ] `system_parameters` — `episode_temporal_window_hours = 720`
- [ ] `episode_flow_parameters.py` — default 720
- [ ] `episode_service.py` — `_resolve_episode_status` con 3 reglas, COALESCE en last_seen_at
- [ ] Endpoint episodios activos — filtra slides_data IS NOT NULL
- [ ] Carousel worker — Redis lock, retry con backoff, escritura atómica, log estructurado
- [ ] Rate limiter — 5 req / 6 horas por usuario en endpoints de generación
- [ ] Hard cap page_size ≤ 100 en endpoints de episodios
- [ ] `scripts/recalculate_episodes.py` — ejecutado con éxito (dry-run primero)
- [ ] `scripts/verify_carousel.sh` — ejecutado sin errores
- [ ] `fire_events.slides_data` — marcado deprecated
- [ ] Tests creados y ejecutables (ajustar imports según estructura real)
