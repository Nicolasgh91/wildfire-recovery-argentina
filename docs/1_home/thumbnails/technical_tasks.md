# Tareas técnicas: refactorización de gee_service.py

> **Propósito:** guiar a Claude Code en la ejecución de la refactorización de `app/services/gee_service.py` en 3 fases incrementales.
> Cada fase es desplegable de forma independiente. No iniciar una fase sin haber completado el gate de la anterior.

---

## Contexto

- **Archivo principal:** `app/services/gee_service.py` (~1370 líneas)
- **Consumidores directos:** `imagery_service.py`, `vae_service.py`, `ers_service.py`, `closure_report_service.py`, `exploration_hd_worker.py`, `app/api/routes/historical.py`
- **Infraestructura:** Oracle Cloud VM (947 MB RAM), 2 workers (`worker-fast`, `worker-gee`), deploy via `deploy-prod-vm.yml`
- **Problema origen:** thumbnails del carousel generados con franjas verticales vacías

---

## Resumen de fases

| Fase | Objetivo | Esfuerzo | Riesgo | Dependencia |
|------|----------|----------|--------|-------------|
| 1 | Bugfix + limpieza de código muerto | 4-6 h | Bajo | Ninguna |
| 2 | Eliminación de duplicación (DRY) | 6-8 h | Medio-bajo | Gate 1 |
| 3 | Separación de responsabilidades | 10-14 h | Medio | Gate 2 |

---

## Fase 1: corrección de bugs y limpieza

### F1-01. Fix thumbnails con franjas vacías

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | Ninguna |

**Problema:** cuando el aspect ratio del bbox del episodio no coincide con el de `dimensions` (p. ej. bbox 0.2° × 0.1° = 2:1 pero `dimensions="768x576"` = 4:3), GEE genera la imagen con el bbox real y la escala para ajustar a `dimensions`, creando franjas vacías en uno de los bordes.

**Cambios requeridos:**

1. Crear función `_bbox_to_dimensions(bbox: dict, max_dim: int = 768) -> str` que calcule `"WxH"` proporcional al aspect ratio del bbox, garantizando que ninguna dimensión exceda `max_dim`.

```python
def _bbox_to_dimensions(bbox: dict, max_dim: int = 768) -> str:
    """Calcula dimensions WxH respetando el aspect ratio del bbox.
    
    Garantiza que width y height <= max_dim y que el aspect ratio
    del thumbnail coincide con el del bbox, eliminando franjas vacías.
    """
    bbox_w = abs(bbox["east"] - bbox["west"])
    bbox_h = abs(bbox["north"] - bbox["south"])
    
    if bbox_w <= 0 or bbox_h <= 0:
        return f"{max_dim}x{max_dim}"
    
    aspect = bbox_w / bbox_h
    if aspect >= 1:
        w = max_dim
        h = max(1, round(max_dim / aspect))
    else:
        h = max_dim
        w = max(1, round(max_dim * aspect))
    
    return f"{w}x{h}"
```

2. En `get_thumbnail_url`, cuando el caller no pasa `dimensions` explícitamente o pasa un entero, usar `_bbox_to_dimensions` para generar el string `"WxH"` apropiado. Cuando el caller pasa un string `"WxH"` explícito, respetarlo (backward compatibility).

3. Aplicar la misma lógica en `get_dnbr_thumbnail_url`.

**Validación:**

```bash
# Test: verificar que el thumbnail no tiene franjas vacías
# Mock de bbox con aspect ratio 2:1
python -c "
from app.services.gee_service import _bbox_to_dimensions
bbox = {'west': -60.0, 'south': -27.0, 'east': -59.8, 'north': -27.1}
dims = _bbox_to_dimensions(bbox, max_dim=768)
print(f'bbox 2:1 -> dimensions: {dims}')
assert dims == '768x384', f'Expected 768x384, got {dims}'

# Bbox cuadrado
bbox2 = {'west': -60.0, 'south': -27.0, 'east': -59.9, 'north': -26.9}
dims2 = _bbox_to_dimensions(bbox2, max_dim=768)
print(f'bbox 1:1 -> dimensions: {dims2}')
assert dims2 == '768x768', f'Expected 768x768, got {dims2}'

# Bbox vertical
bbox3 = {'west': -60.0, 'south': -27.0, 'east': -59.95, 'north': -26.8}
dims3 = _bbox_to_dimensions(bbox3, max_dim=768)
print(f'bbox 1:4 -> dimensions: {dims3}')
w, h = dims3.split('x')
assert int(h) == 768, f'Expected height=768, got {h}'
print('Todos los tests pasaron')
"
```

**Regresión:** los thumbnails existentes en el carousel cambiarán de proporción. Ejecutar `force_refresh` del carousel post-deploy.

---

### F1-02. Fix acquisition_date Optional

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` (línea 204) |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 15 min |
| **Dependencias** | Ninguna |

**Cambio:** en el dataclass `ImageMetadata`, cambiar:

```python
# ANTES
acquisition_date: date

# DESPUÉS
acquisition_date: Optional[date] = None
```

**Validación:**

```bash
grep -n "acquisition_date" app/services/gee_service.py
# Verificar que dice Optional[date] = None

# Buscar consumidores que asuman non-None
grep -rn "acquisition_date" app/services/ --include="*.py" | grep -v "test" | grep -v "__pycache__"
# Para cada match: verificar que maneja None (o agregar guard)
```

**Regresión:** ninguna si los consumidores ya manejan None. Verificar `imagery_service.py` donde se formatea la fecha para `slides_data`.

---

### F1-03. Unificar sun_elevation

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` (método `get_collection_info`, línea 557) |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 15 min |
| **Dependencias** | Ninguna |

**Problema:** `get_collection_info` guarda zenith crudo (`MEAN_SOLAR_ZENITH_ANGLE`), pero `get_image_metadata` convierte a elevación (`90 - zenith`). El mismo campo tiene semántica distinta.

**Cambio:** en `get_collection_info`, línea 557:

```python
# ANTES
sun_elevation=props.get("MEAN_SOLAR_ZENITH_ANGLE", 0),

# DESPUÉS
sun_elevation=90 - props.get("MEAN_SOLAR_ZENITH_ANGLE", 0),
```

**Validación:**

```bash
# Verificar que ambos métodos calculan elevación
grep -n "sun_elevation" app/services/gee_service.py
# Ambos deben mostrar "90 - props.get(...)"

# Buscar consumidores que interpreten sun_elevation como zenith
grep -rn "sun_elevation" app/services/ workers/ --include="*.py" | grep -v "__pycache__"
```

---

### F1-04. Eliminar factory duplicada en historical.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/api/routes/historical.py` (líneas 114-117) |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 10 min |
| **Dependencias** | Ninguna |

**Cambio:**

1. Eliminar la función `get_gee_service()` local en `historical.py`.
2. Agregar import: `from app.services.gee_service import get_gee_service`
3. Verificar que las llamadas existentes siguen funcionando.

**Validación:**

```bash
# Verificar que no hay más factories duplicadas
grep -rn "def get_gee_service" app/ --include="*.py"
# Debe retornar SOLO app/services/gee_service.py
```

---

### F1-05. Eliminar código muerto

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 30 min |
| **Dependencias** | Ninguna |

**Cambios:**

1. **Eliminar `from functools import lru_cache`** (línea 30): no se usa en ningún punto del archivo.

2. **Eliminar función `_debug_log` y todas sus invocaciones** (líneas 38-54, y todas las líneas con `_debug_log` y `#region agent log` / `#endregion`):

```bash
# Listar todas las líneas a eliminar
grep -n "_debug_log\|#region agent log\|#endregion" app/services/gee_service.py
```

3. **Evaluar `ImageResult`** (líneas 224-232):

```bash
# Buscar si ImageResult se instancia en algún punto
grep -rn "ImageResult(" app/ workers/ --include="*.py" | grep -v "__pycache__"
# Si no hay resultados, marcar como deprecated con docstring:
# """DEPRECATED: no se usa activamente. Candidato a eliminación en fase 3."""
```

4. **Eliminar import no usado** `from io import BytesIO` (línea 31) — verificar primero:

```bash
grep -n "BytesIO" app/services/gee_service.py
# Si solo aparece en el import, eliminar
```

5. **Eliminar import no usado** `import hashlib` (línea 24) — verificar primero:

```bash
grep -n "hashlib" app/services/gee_service.py
# Si solo aparece en el import, eliminar
```

**Validación:**

```bash
# Verificar que el archivo compila sin errores
python -c "from app.services.gee_service import GEEService; print('Import OK')"

# Verificar que no quedan referencias a _debug_log
grep -c "_debug_log" app/services/gee_service.py
# Debe retornar 0
```

---

### Gate 1: validación pre-deploy

Ejecutar antes de hacer merge del PR de fase 1:

```bash
# 1. El archivo compila
python -c "from app.services.gee_service import GEEService, get_gee_service, ImageMetadata; print('Imports OK')"

# 2. Todos los consumidores importan sin error
python -c "
from app.services.imagery_service import *
from app.services.vae_service import *
from app.services.ers_service import *
from app.services.closure_report_service import *
print('Consumidores OK')
"

# 3. No quedan debug logs
grep -c "_debug_log" app/services/gee_service.py  # Debe ser 0

# 4. No hay factory duplicada
grep -rn "def get_gee_service" app/ --include="*.py" | wc -l  # Debe ser 1

# 5. acquisition_date es Optional
grep "acquisition_date" app/services/gee_service.py | head -1  # Debe incluir Optional

# 6. sun_elevation es consistente
grep "sun_elevation" app/services/gee_service.py | grep -c "90 -"  # Debe ser 2

# 7. _bbox_to_dimensions existe y pasa tests básicos
python -c "
from app.services.gee_service import _bbox_to_dimensions
assert 'x' in _bbox_to_dimensions({'west':-60,'south':-27,'east':-59.8,'north':-27.1})
print('_bbox_to_dimensions OK')
"
```

---

## Fase 2: eliminación de duplicación (DRY)

> **Prerequisito:** gate 1 completado y fase 1 desplegada en producción.

### F2-01. Extraer helper _bbox_to_geometry

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 1 h |
| **Dependencias** | Gate 1 |

**Cambio:** crear función que centralice la construcción de geometrías:

```python
def _bbox_to_geometry(bbox: Dict[str, float]) -> "ee.Geometry.Rectangle":
    """Construye ee.Geometry.Rectangle a partir de un dict bbox.
    
    Args:
        bbox: dict con keys 'west', 'south', 'east', 'north'
        
    Returns:
        ee.Geometry.Rectangle
        
    Raises:
        ValueError: si el bbox es inválido (east <= west o north <= south)
    """
    if bbox["east"] <= bbox["west"]:
        raise ValueError(f"bbox inválido: east ({bbox['east']}) <= west ({bbox['west']})")
    if bbox["north"] <= bbox["south"]:
        raise ValueError(f"bbox inválido: north ({bbox['north']}) <= south ({bbox['south']})")
    
    return ee.Geometry.Rectangle(
        [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    )
```

**Reemplazar** todas las ocurrencias de `ee.Geometry.Rectangle([bbox["west"], ...])` en el archivo:

```bash
# Listar todas las ocurrencias
grep -n "ee.Geometry.Rectangle" app/services/gee_service.py
# Reemplazar cada una por: _bbox_to_geometry(bbox)
```

**Validación:**

```bash
# Verificar que no quedan construcciones manuales de Rectangle con bbox
grep -c "ee.Geometry.Rectangle.*bbox" app/services/gee_service.py  # Debe ser 0

# Verificar que _bbox_to_geometry se usa en todos los métodos
grep -c "_bbox_to_geometry" app/services/gee_service.py  # Debe ser >= 8
```

---

### F2-02. Extraer helper _thumb_size_params

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 30 min |
| **Dependencias** | Gate 1 |

**Cambio:**

```python
def _thumb_size_params(dimensions: Union[int, str]) -> dict:
    """Normaliza el parámetro dimensions a dict para getThumbURL.
    
    - String con 'x' (ej: '768x576'): se pasa tal cual.
    - int o float: se convierte a entero.
    """
    if isinstance(dimensions, str) and "x" in dimensions.lower():
        return {"dimensions": dimensions}
    return {"dimensions": int(float(dimensions))}
```

**Reemplazar** los bloques duplicados en `get_thumbnail_url` y `get_dnbr_thumbnail_url`:

```bash
# Buscar los bloques a reemplazar
grep -n "isinstance(dimensions, str)" app/services/gee_service.py
# Cada bloque de 4 líneas se reemplaza por: size_params = _thumb_size_params(dimensions)
```

---

### F2-03. Extraer helper _with_thumbnail_retry

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | Gate 1 |

**Cambio:** extraer método que encapsule el loop de retry con backoff:

```python
def _with_thumbnail_retry(self, get_url_fn, context_label: str = "thumbnail"):
    """Ejecuta get_url_fn con retry y backoff para HTTP 500 de GEE.
    
    Args:
        get_url_fn: callable que genera la URL (se pasa a _rate_limited_request)
        context_label: etiqueta para logging (ej: 'NDVI', 'DNBR')
        
    Returns:
        str: URL del thumbnail
        
    Raises:
        La última excepción si se agotan los reintentos.
    """
    last_exc = None
    for attempt in range(GEE_THUMB_MAX_RETRIES + 1):
        try:
            return self._rate_limited_request(get_url_fn)
        except Exception as exc:
            status = getattr(getattr(exc, "resp", None), "status", None)
            is_500 = (
                _HttpError is not None
                and isinstance(exc, _HttpError)
                and status == 500
            )
            if is_500 and attempt < GEE_THUMB_MAX_RETRIES:
                wait = GEE_THUMB_BACKOFF_BASE ** attempt
                logger.warning(
                    "GEE thumbnail 500 (intento %d/%d) para %s. "
                    "Reintentando en %.1fs. Error: %s",
                    attempt + 1,
                    GEE_THUMB_MAX_RETRIES + 1,
                    context_label,
                    wait,
                    exc,
                )
                sleep(wait)
                last_exc = exc
                continue
            raise
    if last_exc is not None:
        raise last_exc
```

**Reemplazar** los 3 bloques de retry en:

1. `get_thumbnail_url` (líneas ~981-1004) → `return self._with_thumbnail_retry(_get_url, vis_type)`
2. `get_dnbr_thumbnail_url` (líneas ~843-865) → `return self._with_thumbnail_retry(_get_url, "DNBR")`
3. `download_thumbnail` (líneas ~1096-1131): aquí el retry es sobre HTTP GET, no sobre URL generation. Extraer como `_http_download_with_retry` (ver F2-04).

---

### F2-04. Extraer helper _http_download_with_retry

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 1 h |
| **Dependencias** | F2-03 |

**Cambio:**

```python
def _http_download_with_retry(
    self, url: str, context_label: str = "thumbnail", timeout: int = 60
) -> bytes:
    """Descarga bytes desde una URL de GEE con retry para 5xx.
    
    Args:
        url: URL del thumbnail de GEE
        context_label: etiqueta para logging
        timeout: timeout HTTP en segundos
        
    Returns:
        bytes: contenido de la respuesta
    """
    for attempt in range(GEE_THUMB_MAX_RETRIES + 1):
        response = requests.get(url, timeout=timeout)
        if response.status_code < 500:
            response.raise_for_status()
            return response.content
        if attempt < GEE_THUMB_MAX_RETRIES:
            wait = GEE_THUMB_BACKOFF_BASE ** attempt
            logger.warning(
                "GEE download 5xx (intento %d/%d) para %s. "
                "Reintentando en %.1fs. status=%s",
                attempt + 1,
                GEE_THUMB_MAX_RETRIES + 1,
                context_label,
                wait,
                response.status_code,
            )
            sleep(wait)
            continue
        response.raise_for_status()
    return response.content
```

**Reemplazar** en `download_thumbnail` y `download_dnbr_thumbnail`:

```python
# download_thumbnail se reduce a:
def download_thumbnail(self, image, bbox, vis_type="RGB", dimensions=1024, resample=None, format="png"):
    url = self.get_thumbnail_url(image, bbox, vis_type, dimensions, resample, format)
    return self._http_download_with_retry(url, vis_type)

# download_dnbr_thumbnail se reduce a:
def download_dnbr_thumbnail(self, pre_image, post_image, bbox, dimensions=512, format="png"):
    url = self.get_dnbr_thumbnail_url(pre_image, post_image, bbox, dimensions=dimensions, format=format)
    return self._http_download_with_retry(url, "DNBR")
```

---

### Gate 2: validación pre-deploy

```bash
# 1. El archivo compila y los helpers existen
python -c "
from app.services.gee_service import (
    GEEService, get_gee_service,
    _bbox_to_geometry, _thumb_size_params, _bbox_to_dimensions
)
print('Imports OK')
"

# 2. No queda duplicación de bbox construction
grep -c "ee.Geometry.Rectangle.*bbox" app/services/gee_service.py  # Debe ser 0 (solo dentro de _bbox_to_geometry)

# 3. No queda duplicación de dimension parsing
grep -c "isinstance(dimensions, str)" app/services/gee_service.py  # Debe ser 0 (solo dentro de _thumb_size_params)

# 4. El retry loop aparece solo en los helpers
grep -c "GEE_THUMB_MAX_RETRIES" app/services/gee_service.py  # Debe ser <= 4 (declaración + 2 helpers)

# 5. Consumidores importan sin error
python -c "
from app.services.imagery_service import *
from app.services.vae_service import *
from app.services.ers_service import *
print('Consumidores OK')
"

# 6. Validación de _bbox_to_geometry con bbox inválido
python -c "
from app.services.gee_service import _bbox_to_geometry
try:
    _bbox_to_geometry({'west': -59, 'south': -27, 'east': -60, 'north': -26})
    print('ERROR: debería haber lanzado ValueError')
    exit(1)
except ValueError as e:
    print(f'Validación OK: {e}')
"
```

---

## Fase 3: separación de responsabilidades

> **Prerequisito:** gate 2 completado y fase 2 desplegada en producción.

### F3-01. Crear estructura de paquete gee/

| Campo | Valor |
|-------|-------|
| **Archivos** | `app/services/gee/` (nuevo paquete) |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 2 h |
| **Dependencias** | Gate 2 |

**Cambio:** crear la estructura de directorios:

```
app/services/gee/
├── __init__.py       # Re-exports para backward compatibility
├── models.py         # Dataclasses + excepciones
├── helpers.py        # _bbox_to_geometry, _thumb_size_params, _bbox_to_dimensions, _compute_safe_scale
├── auth.py           # GEEAuthenticator (autenticación + health_check)
├── collections.py    # GEECollectionService (búsqueda de imágenes)
├── indices.py        # GEEIndexService (NDVI, NBR, cloud cover)
├── thumbnails.py     # GEEThumbnailService (URLs + download)
└── timeseries.py     # GEETimeSeriesService (series temporales)
```

**`__init__.py` crítico para backward compatibility:**

```python
"""Paquete GEE — backward compatible con app.services.gee_service."""

from app.services.gee.models import (
    ImageMetadata, NDVIResult, ImageResult,
    GEEError, GEEAuthenticationError, GEEImageNotFoundError,
    GEERateLimitError, GEEServiceUnavailableError,
)
from app.services.gee.service import GEEService
from app.services.gee.factory import get_gee_service

__all__ = [
    "GEEService", "get_gee_service",
    "ImageMetadata", "NDVIResult", "ImageResult",
    "GEEError", "GEEAuthenticationError", "GEEImageNotFoundError",
    "GEERateLimitError", "GEEServiceUnavailableError",
]
```

---

### F3-02. Extraer models.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/models.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 30 min |
| **Dependencias** | F3-01 |

**Mover a `models.py`:**

- Dataclasses: `ImageMetadata`, `NDVIResult`, `ImageResult`
- Excepciones: `GEEError`, `GEEAuthenticationError`, `GEEImageNotFoundError`, `GEERateLimitError`, `GEEServiceUnavailableError`
- Constantes de configuración: `SENTINEL2_COLLECTION`, `SENTINEL2_CLOUD_PROB`, `BANDS`, `VIS_PARAMS`, `CALLS_PER_SECOND`, `CALLS_PER_DAY`, `GEE_THUMB_*`

---

### F3-03. Extraer helpers.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/helpers.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 30 min |
| **Dependencias** | F3-01 |

**Mover a `helpers.py`:**

- `_compute_safe_scale`
- `_bbox_to_geometry`
- `_bbox_to_dimensions`
- `_thumb_size_params`

---

### F3-04. Extraer auth.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/auth.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | F3-02, F3-03 |

**Crear clase `GEEAuthenticator`:**

- Método `authenticate()` con las 4 opciones de credenciales
- Método `_ensure_authenticated()`
- Método `_ensure_ee_available()`
- Método `health_check()`
- Estado: `_initialized`, `_project_id`, `_service_account_json`

**No incluir** rate limiting ni circuit breaker (eso va en el servicio base).

---

### F3-05. Extraer collections.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/collections.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 1 h |
| **Dependencias** | F3-04 |

**Crear clase `GEECollectionService`:**

- `get_sentinel_collection(bbox, start_date, end_date, max_cloud_cover)`
- `get_collection_info(collection)`
- `get_best_image(collection, target_date, prefer_low_cloud, max_cloud_cover)`
- `apply_cloud_mask(image)`
- `get_image_by_id(image_id)`
- `get_image_metadata(image)`

Recibe `authenticator` y `rate_limiter` por constructor.

---

### F3-06. Extraer indices.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/indices.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 1 h |
| **Dependencias** | F3-04 |

**Crear clase `GEEIndexService`:**

- `calculate_ndvi(image, bbox, scale)`
- `calculate_nbr(image, bbox, scale)`
- `get_image_cloud_cover(image)`

Recibe `authenticator` y `rate_limiter` por constructor.

---

### F3-07. Extraer thumbnails.py con Strategy pattern

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/thumbnails.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 2.5 h |
| **Dependencias** | F3-04, F3-03 |

**Crear clase `GEEThumbnailService`:**

- `get_thumbnail_url(image, bbox, vis_type, dimensions, resample, format)`
- `get_dnbr_thumbnail_url(pre_image, post_image, bbox, dimensions, format)`
- `get_download_url(image, bbox, bands, scale, format)`
- `download_thumbnail(image, bbox, vis_type, dimensions, resample, format)`
- `download_dnbr_thumbnail(pre_image, post_image, bbox, dimensions, format)`
- `_with_thumbnail_retry(get_url_fn, context_label)`
- `_http_download_with_retry(url, context_label, timeout)`

**Implementar Strategy para vis_type:**

```python
from abc import ABC, abstractmethod
from typing import Protocol

class VisualizationStrategy(Protocol):
    """Protocolo para estrategias de visualización."""
    def prepare_image(self, image: "ee.Image") -> "ee.Image": ...
    def get_vis_params(self) -> dict: ...

class BandSelectionStrategy:
    """Selecciona bandas y aplica vis_params de VIS_PARAMS."""
    def __init__(self, vis_key: str):
        self.vis_key = vis_key
    
    def prepare_image(self, image):
        return image.select(VIS_PARAMS[self.vis_key]["bands"])
    
    def get_vis_params(self):
        return {k: v for k, v in VIS_PARAMS[self.vis_key].items() if k != "bands"}

class NormalizedDifferenceStrategy:
    """Calcula índice normalizado entre dos bandas."""
    def __init__(self, band_a: str, band_b: str, vis_key: str):
        self.band_a = band_a
        self.band_b = band_b
        self.vis_key = vis_key
    
    def prepare_image(self, image):
        a = image.select(self.band_a)
        b = image.select(self.band_b)
        return a.subtract(b).divide(a.add(b))
    
    def get_vis_params(self):
        return VIS_PARAMS.get(self.vis_key, {"min": -0.5, "max": 0.5}).copy()

# Registry
VIS_STRATEGIES = {
    "NDVI": NormalizedDifferenceStrategy("B8", "B4", "NDVI"),
    "NBR": NormalizedDifferenceStrategy("B8", "B12", "NBR"),
    "SCIENCE": NormalizedDifferenceStrategy("B8", "B12", "NBR"),
    "BURN_SEVERITY": NormalizedDifferenceStrategy("B8", "B12", "BURN_SEVERITY"),
    "RGB": BandSelectionStrategy("RGB"),
    "FALSE_COLOR": BandSelectionStrategy("FALSE_COLOR"),
    "SWIR": BandSelectionStrategy("SWIR"),
    "IMPACT": BandSelectionStrategy("IMPACT"),
    "REALITY": BandSelectionStrategy("REALITY"),
}
```

---

### F3-08. Extraer timeseries.py

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/timeseries.py` |
| **Prioridad** | P3 — bajo |
| **Esfuerzo** | 1 h |
| **Dependencias** | F3-05 |

**Crear clase `GEETimeSeriesService`:**

- `get_temporal_series(bbox, start_date, end_date, interval_months, max_cloud_cover)`
- `get_annual_series_for_fire(bbox, fire_date, years_after, pre_fire_days)`

Recibe `collection_service` por constructor para buscar imágenes.

---

### F3-09. Crear GEEService como fachada

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee/service.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | F3-04 a F3-08 |

**GEEService queda como Facade que compone y delega:**

```python
class GEEService:
    """Fachada orquestadora de servicios GEE.
    
    Mantiene la API pública original delegando a sub-servicios especializados.
    Los consumidores pueden usar esta fachada o inyectar sub-servicios directamente.
    """
    
    def __init__(self, service_account_json=None, project_id=None):
        self._auth = GEEAuthenticator(service_account_json, project_id)
        self._collections = GEECollectionService(self._auth)
        self._indices = GEEIndexService(self._auth)
        self._thumbnails = GEEThumbnailService(self._auth)
        self._timeseries = GEETimeSeriesService(self._auth, self._collections)
    
    # Delegar todos los métodos públicos originales
    def authenticate(self): return self._auth.authenticate()
    def get_sentinel_collection(self, *a, **kw): return self._collections.get_sentinel_collection(*a, **kw)
    def calculate_ndvi(self, *a, **kw): return self._indices.calculate_ndvi(*a, **kw)
    def get_thumbnail_url(self, *a, **kw): return self._thumbnails.get_thumbnail_url(*a, **kw)
    # ... etc para cada método público
```

---

### F3-10. Crear redirect en gee_service.py original

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 15 min |
| **Dependencias** | F3-09 |

**Reemplazar** el contenido completo de `app/services/gee_service.py` por un redirect:

```python
"""Backward compatibility redirect.

Este archivo redirige todos los imports al nuevo paquete app.services.gee.
Los consumidores existentes que hacen:
    from app.services.gee_service import GEEService
seguirán funcionando sin cambios.
"""

# Re-export todo desde el nuevo paquete
from app.services.gee import *  # noqa: F401, F403
from app.services.gee import (
    GEEService,
    get_gee_service,
    ImageMetadata,
    NDVIResult,
    ImageResult,
    GEEError,
    GEEAuthenticationError,
    GEEImageNotFoundError,
    GEERateLimitError,
    GEEServiceUnavailableError,
)

# Helpers que algunos consumidores podrían importar directamente
from app.services.gee.helpers import (
    _bbox_to_geometry,
    _bbox_to_dimensions,
    _thumb_size_params,
    _compute_safe_scale,
)
```

---

### Gate 3: validación pre-deploy

```bash
# 1. Backward compatibility: imports originales funcionan
python -c "
from app.services.gee_service import GEEService, get_gee_service, ImageMetadata
from app.services.gee_service import GEEError, GEEAuthenticationError
from app.services.gee_service import _bbox_to_geometry, _bbox_to_dimensions
print('Backward compatibility OK')
"

# 2. Imports directos al nuevo paquete funcionan
python -c "
from app.services.gee import GEEService, get_gee_service
from app.services.gee.models import ImageMetadata, NDVIResult
from app.services.gee.thumbnails import GEEThumbnailService
from app.services.gee.indices import GEEIndexService
from app.services.gee.collections import GEECollectionService
from app.services.gee.auth import GEEAuthenticator
from app.services.gee.helpers import _bbox_to_geometry
print('Direct imports OK')
"

# 3. Todos los consumidores importan sin error
python -c "
from app.services.imagery_service import *
from app.services.vae_service import *
from app.services.ers_service import *
from app.services.closure_report_service import *
print('Consumidores OK')
"

# 4. El archivo original es solo redirect
wc -l app/services/gee_service.py  # Debe ser < 40 líneas

# 5. El paquete nuevo tiene la estructura correcta
find app/services/gee/ -name "*.py" | sort
# Debe listar: __init__.py, auth.py, collections.py, helpers.py,
#              indices.py, models.py, service.py, thumbnails.py, timeseries.py

# 6. GEEService delega correctamente (verificar que no hay lógica directa)
grep -c "ee\." app/services/gee/service.py  # Debe ser 0 (toda la lógica ee está en sub-servicios)
```

---

## Post-deploy de cada fase

```bash
# Ejecutar después de cada deploy exitoso

# 1. Health check de la API
curl -fsS https://forestguard.com/health

# 2. Verificar que el carousel funciona
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}'

# 3. Monitorear logs del worker
docker logs --tail 50 -f forestguard-worker-gee

# 4. Verificar thumbnails generados
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
r = db.execute(text(
    \"SELECT id, jsonb_array_length(slides_data) as slides \"
    \"FROM fire_episodes WHERE slides_data IS NOT NULL \"
    \"ORDER BY updated_at DESC LIMIT 5\"
)).fetchall()
for row in r:
    print(f'Episode {row[0]}: {row[1]} slides')
db.close()
"
```

---

## Restricciones para Claude Code

1. **No agregar dependencias** nuevas a `requirements.txt`. Todo se resuelve con las dependencias existentes.
2. **No modificar** `docker-compose.yml`, `Dockerfile.*`, ni workflows de GitHub Actions.
3. **No cambiar** firmas de métodos públicos de `GEEService`. Los consumidores no deben necesitar cambios (excepto imports en fase 3).
4. **No hacer** llamadas reales a GEE en tests. Usar mocks de `ee` module.
5. **Mantener** el rate limiting (`@sleep_and_retry`, `@limits`) y el circuit breaker (`gee_circuit`) sin modificación.
6. **Preservar** los invariantes documentados en `test_gee_contract_mock.py`: scale en grados, clip antes de reproject, etc.
7. **Cada fase** se hace en un PR separado. No acumular fases.