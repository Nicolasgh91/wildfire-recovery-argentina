# Tareas técnicas: renderizado local de thumbnails

> **Propósito:** guiar a Claude Code en la migración de `download_thumbnail` y `download_dnbr_thumbnail` desde `getThumbURL` (rendering server-side en GEE) a `computePixels` + rendering local (numpy/PIL).
> Este documento asume que la fase 1 (bugfix) y la fase 2 original (DRY helpers) ya están implementadas y deployadas.

---

## Estado previo

| Fase | Estado | Helpers disponibles |
|------|--------|-------------------|
| Fase 1 (bugfix) | ✅ Deployada | `_bbox_to_dimensions`, `ImageMetadata(Optional[date])`, sun_elevation unificado |
| Fase 2 (DRY) | ✅ Deployada | `_bbox_to_geometry`, `_thumb_size_params`, `_with_thumbnail_retry`, `_http_download_with_retry` |
| Fase 2b (rendering local) | ⏳ Este documento | — |

## Contexto del problema

Los thumbnails del carousel fallan con HTTP 500 en el endpoint `:getPixels` de GEE. Este endpoint realiza el rendering server-side (selección de bandas + vis_params + generación PNG). El error es opaco, no diagnosticable y afecta especialmente a `vis_type=SWIR`. La solución es descargar datos crudos con `computePixels` y renderizar localmente con numpy+PIL, eliminando la dependencia del endpoint `:getPixels` para los métodos de descarga.

---

## Restricciones

1. **RAM:** 947 MB efectivos en la VM. El rendering local agrega ~3.8 MB pico por thumbnail (despreciable).
2. **Cuota GEE:** 50K req/día. `computePixels` consume 1 req vs 2 del flujo actual (mejora).
3. **Dependencias:** solo usar numpy, Pillow y matplotlib.colors (ya instalados). No agregar paquetes nuevos.
4. **API pública:** las firmas de `download_thumbnail` y `download_dnbr_thumbnail` no cambian.
5. **Coexistencia:** `get_thumbnail_url` (que usa `getThumbURL`) se mantiene intacto para endpoints REST que devuelven URLs al frontend.
6. **Workers:** no modificar docker-compose.yml, Dockerfile.*, ni workflows de GitHub Actions.

---

## LR-00. Verificar prerequisito bloqueante

| Campo | Valor |
|-------|-------|
| **Prioridad** | P0 — bloqueante |
| **Esfuerzo** | 10 min |
| **Dependencias** | Ninguna |

**Objetivo:** confirmar que `ee.data.computePixels` está disponible en la versión de `earthengine-api` instalada en el contenedor `worker-gee`.

**Comandos a ejecutar en producción:**

```bash
# 1. Versión del SDK
docker exec forestguard-worker-gee pip show earthengine-api | grep Version
# Requiere >= 0.1.370

# 2. Verificar que computePixels existe
docker exec forestguard-worker-gee python -c "
import ee
print('computePixels disponible:', hasattr(ee.data, 'computePixels'))
print('Versión ee:', ee.__version__)
"

# 3. Verificar numpy, PIL, matplotlib.colors
docker exec forestguard-worker-gee python -c "
import numpy as np; print(f'numpy {np.__version__}')
from PIL import Image; print(f'Pillow OK')
from matplotlib import colors as mcolors; print(f'matplotlib.colors OK')
"
```

**Resultado esperado:** los tres comandos pasan sin error.

**Si `computePixels` no está disponible:**

```bash
# Verificar si getDownloadURL con NPY funciona como fallback
docker exec forestguard-worker-gee python -c "
import ee
# Solo verificar que el método existe (no ejecutar contra GEE)
img = ee.Image(1)
print('getDownloadURL disponible:', hasattr(img, 'getDownloadURL'))
"
```

**Decisión de ruta:**

- Si `computePixels` disponible → seguir con LR-01 usando `computePixels`.
- Si solo `getDownloadURL` disponible → seguir con LR-01 usando el fallback NPY (se documenta la variante en LR-01).
- Si ninguno de los dos → actualizar `earthengine-api` en `requirements.txt` (cambio mínimo, rebuild de imagen necesario).

**Registrar el resultado** como comentario en el PR para trazabilidad.

---

## LR-01. Implementar download_raw_bands

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | LR-00 confirmado |

**Objetivo:** nuevo método que descarga bandas crudas de GEE como numpy array, sin rendering server-side.

**Implementación (variante computePixels):**

```python
import numpy as np

def download_raw_bands(
    self,
    image: ee.Image,
    bbox: Dict[str, float],
    bands: List[str],
    scale: float = None,
) -> np.ndarray:
    """Descarga bandas crudas como numpy array via computePixels.
    
    No usa el endpoint :getPixels (rendering server-side).
    GEE solo hace clip + reproject + envío de datos crudos.
    
    Args:
        image: imagen Sentinel-2 (con cloud mask si corresponde)
        bbox: dict con keys west, south, east, north
        bands: lista de bandas requeridas (e.g. ["B12", "B11", "B4"])
        scale: resolución en grados EPSG:4326 (default: _compute_safe_scale)
        
    Returns:
        np.ndarray con shape (H, W, len(bands)), dtype float32
        
    Raises:
        ee.EEException: si GEE no puede procesar la solicitud
        ValueError: si el bbox es inválido
    """
    self._ensure_authenticated()
    
    if scale is None:
        scale = _compute_safe_scale(bbox)
    
    geometry = _bbox_to_geometry(bbox)
    
    selected = image.select(bands).clip(geometry).reproject(
        crs="EPSG:4326", scale=scale
    )
    
    def _compute():
        return ee.data.computePixels({
            "expression": selected,
            "fileFormat": "NUMPY_NDARRAY",
        })
    
    result = self._rate_limited_request(_compute)
    
    # Guard: proteger contra arrays inesperadamente grandes
    if result.nbytes > 50_000_000:  # 50 MB
        raise ValueError(
            f"Array demasiado grande: {result.nbytes / 1e6:.1f} MB. "
            f"Bbox probablemente excede el límite esperado."
        )
    
    # Reemplazar NaN (píxeles enmascarados por nubes) con 0
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
```

**Implementación (variante fallback getDownloadURL + NPY):**

Solo implementar si LR-00 determinó que `computePixels` no está disponible:

```python
def download_raw_bands(self, image, bbox, bands, scale=None):
    """Fallback via getDownloadURL(format='NPY') + HTTP GET + np.load."""
    self._ensure_authenticated()
    
    if scale is None:
        scale = _compute_safe_scale(bbox)
    
    geometry = _bbox_to_geometry(bbox)
    selected = image.select(bands).clip(geometry).reproject(
        crs="EPSG:4326", scale=scale
    )
    
    def _get_url():
        return selected.getDownloadURL({
            "region": geometry,
            "scale": scale,
            "format": "NPY",
            "crs": "EPSG:4326",
        })
    
    url = self._rate_limited_request(_get_url)
    
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    
    result = np.load(io.BytesIO(response.content))
    
    if result.nbytes > 50_000_000:
        raise ValueError(f"Array demasiado grande: {result.nbytes / 1e6:.1f} MB")
    
    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
```

**Validación:**

```bash
# Verificar que el método existe y acepta la firma correcta
python -c "
from app.services.gee_service import GEEService
import inspect
sig = inspect.signature(GEEService.download_raw_bands)
params = list(sig.parameters.keys())
assert params == ['self', 'image', 'bbox', 'bands', 'scale'], f'Firma incorrecta: {params}'
print(f'download_raw_bands firma OK: {params}')
"
```

---

## LR-02. Implementar render_band_selection

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` (función a nivel de módulo) |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1 h |
| **Dependencias** | Ninguna (función pura) |

**Objetivo:** renderizar 3 bandas crudas como imagen RGB con stretch lineal y gamma correction. Cubre vis_types: RGB, FALSE_COLOR, SWIR, IMPACT, REALITY.

```python
from PIL import Image

def _render_band_selection(
    bands_array: np.ndarray,
    vis_min: Union[list, int, float],
    vis_max: Union[list, int, float],
    gamma: Union[list, int, float, None] = None,
) -> Image.Image:
    """Renderiza 3 bandas como imagen RGB con stretch lineal y gamma.
    
    Args:
        bands_array: np.ndarray shape (H, W, 3), dtype float32
        vis_min: valor mínimo por banda (escalar o lista de 3)
        vis_max: valor máximo por banda (escalar o lista de 3)
        gamma: corrección gamma por banda (escalar, lista de 3, o None)
        
    Returns:
        PIL.Image.Image en modo RGB
    """
    # Normalizar min/max a arrays (H, W compatible)
    if isinstance(vis_min, (int, float)):
        vis_min = [vis_min] * 3
    if isinstance(vis_max, (int, float)):
        vis_max = [vis_max] * 3
    
    vmin = np.array(vis_min, dtype=np.float32).reshape(1, 1, 3)
    vmax = np.array(vis_max, dtype=np.float32).reshape(1, 1, 3)
    
    # Stretch lineal a [0, 1]
    denom = vmax - vmin
    denom = np.where(denom == 0, 1, denom)  # evitar división por cero
    normalized = np.clip((bands_array - vmin) / denom, 0, 1)
    
    # Gamma correction
    if gamma is not None:
        if isinstance(gamma, (int, float)):
            gamma = [gamma] * 3
        g = np.array(gamma, dtype=np.float32).reshape(1, 1, 3)
        # gamma > 0 siempre; evitar log domain error
        g = np.maximum(g, 0.01)
        normalized = np.power(normalized, 1.0 / g)
    
    # Convertir a uint8
    rgb_uint8 = (normalized * 255).astype(np.uint8)
    
    return Image.fromarray(rgb_uint8, mode="RGB")
```

**Validación:**

```bash
python -c "
import numpy as np
from app.services.gee_service import _render_band_selection

# Test 1: escalares para min/max/gamma
fake = np.random.uniform(0, 3000, (100, 200, 3)).astype(np.float32)
img = _render_band_selection(fake, 0, 3000, 1.2)
assert img.size == (200, 100), f'Size: {img.size}'
assert img.mode == 'RGB'
print('Test 1 OK: escalares')

# Test 2: listas para min/max (como SWIR)
img2 = _render_band_selection(fake, [0, 0, 0], [5000, 5000, 5000], [1.0, 1.0, 1.0])
assert img2.size == (200, 100)
print('Test 2 OK: listas')

# Test 3: sin gamma
img3 = _render_band_selection(fake, 0, 3000)
assert img3.size == (200, 100)
print('Test 3 OK: sin gamma')

# Test 4: valores extremos (NaN ya reemplazados por 0 en download_raw_bands)
extreme = np.zeros((50, 50, 3), dtype=np.float32)
img4 = _render_band_selection(extreme, 0, 3000)
assert img4.size == (50, 50)
# Todos los píxeles deben ser negro (0,0,0)
arr = np.array(img4)
assert arr.max() == 0, f'Expected all zeros, got max={arr.max()}'
print('Test 4 OK: valores extremos')
"
```

---

## LR-03. Implementar render_normalized_difference

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` (función a nivel de módulo) |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1 h |
| **Dependencias** | Ninguna (función pura) |

**Objetivo:** calcular un índice normalizado (NDVI, NBR, etc.) y aplicar un colormap. Cubre vis_types: NDVI, NBR, SCIENCE, BURN_SEVERITY.

```python
from matplotlib.colors import LinearSegmentedColormap

def _render_normalized_difference(
    band_a: np.ndarray,
    band_b: np.ndarray,
    vis_min: float,
    vis_max: float,
    palette: List[str],
) -> Image.Image:
    """Calcula índice normalizado (a-b)/(a+b) y aplica colormap.
    
    Args:
        band_a: np.ndarray shape (H, W), float32 — banda del numerador positivo (e.g. B8)
        band_b: np.ndarray shape (H, W), float32 — banda del numerador negativo (e.g. B4)
        vis_min: valor mínimo del rango de visualización
        vis_max: valor máximo del rango de visualización
        palette: lista de colores para el colormap (e.g. ["brown", "yellow", "green"])
        
    Returns:
        PIL.Image.Image en modo RGB
    """
    # Calcular índice normalizado
    sum_ab = band_a.astype(np.float64) + band_b.astype(np.float64)
    index = np.where(sum_ab != 0, (band_a - band_b) / sum_ab, 0).astype(np.float32)
    
    # Normalizar a [0, 1] según vis_min/vis_max
    denom = vis_max - vis_min
    if denom == 0:
        denom = 1.0
    normalized = np.clip((index - vis_min) / denom, 0, 1)
    
    # Crear y aplicar colormap
    cmap = LinearSegmentedColormap.from_list("custom", palette, N=256)
    colored = cmap(normalized)  # shape (H, W, 4) float [0,1] RGBA
    
    # Convertir a uint8 RGB (descartar alpha)
    rgb_uint8 = (colored[:, :, :3] * 255).astype(np.uint8)
    
    return Image.fromarray(rgb_uint8, mode="RGB")
```

**Nota sobre matplotlib:** si `matplotlib` no está disponible en la imagen Docker, implementar la siguiente alternativa sin dependencia externa:

```python
def _manual_colormap(normalized: np.ndarray, palette: List[str]) -> np.ndarray:
    """Colormap manual via interpolación lineal en numpy.
    
    Reemplaza matplotlib.colors.LinearSegmentedColormap si no está instalado.
    """
    from PIL import ImageColor
    
    # Convertir colores a RGB float
    colors_rgb = []
    for c in palette:
        if c.startswith("#"):
            r, g, b = ImageColor.getrgb(c)
        else:
            # Colores con nombre: usar PIL
            r, g, b = ImageColor.getrgb(c)
        colors_rgb.append([r / 255.0, g / 255.0, b / 255.0])
    
    colors_arr = np.array(colors_rgb, dtype=np.float32)  # (N_colors, 3)
    n_colors = len(colors_arr)
    
    # Interpolar: mapear [0,1] a índice de color
    indices = normalized * (n_colors - 1)
    lower = np.floor(indices).astype(int)
    upper = np.minimum(lower + 1, n_colors - 1)
    frac = (indices - lower)[:, :, np.newaxis]  # (H, W, 1)
    
    result = colors_arr[lower] * (1 - frac) + colors_arr[upper] * frac
    return (result * 255).astype(np.uint8)
```

**Validación:**

```bash
python -c "
import numpy as np
from app.services.gee_service import _render_normalized_difference

# Test 1: NDVI con datos sintéticos
nir = np.random.uniform(500, 4000, (80, 120)).astype(np.float32)
red = np.random.uniform(100, 2000, (80, 120)).astype(np.float32)
img = _render_normalized_difference(nir, red, -0.2, 0.8, ['brown','yellow','green','darkgreen'])
assert img.size == (120, 80), f'Size: {img.size}'
assert img.mode == 'RGB'
print('Test 1 OK: NDVI')

# Test 2: NBR con paleta hex
b8 = np.random.uniform(500, 4000, (80, 120)).astype(np.float32)
b12 = np.random.uniform(100, 3000, (80, 120)).astype(np.float32)
img2 = _render_normalized_difference(b8, b12, -0.5, 0.5, ['#00FF00','#FFFF00','#FF7F00','#FF0000','#000000'])
assert img2.size == (120, 80)
print('Test 2 OK: NBR hex')

# Test 3: bandas idénticas (índice = 0 en todos los píxeles)
same = np.full((50, 50), 1000.0, dtype=np.float32)
img3 = _render_normalized_difference(same, same, -0.5, 0.5, ['green','yellow','red'])
assert img3.size == (50, 50)
print('Test 3 OK: bandas idénticas')

# Test 4: bandas con ceros (sum_ab = 0)
zeros = np.zeros((50, 50), dtype=np.float32)
img4 = _render_normalized_difference(zeros, zeros, -0.5, 0.5, ['green','red'])
assert img4.size == (50, 50)
print('Test 4 OK: bandas cero')
"
```

---

## LR-04. Refactorizar download_thumbnail

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1.5 h |
| **Dependencias** | LR-01, LR-02, LR-03 |

**Objetivo:** reemplazar el flujo `get_thumbnail_url → HTTP GET → bytes` por `download_raw_bands → render local → bytes`. La firma pública no cambia.

**Mapeo vis_type → bandas + estrategia de rendering:**

```python
# Constante a nivel de módulo (colocar cerca de VIS_PARAMS)
_VIS_BANDS = {
    "RGB":            {"bands": ["B4", "B3", "B2"],   "strategy": "band_selection"},
    "FALSE_COLOR":    {"bands": ["B8", "B4", "B3"],   "strategy": "band_selection"},
    "SWIR":           {"bands": ["B12", "B11", "B4"], "strategy": "band_selection"},
    "IMPACT":         {"bands": ["B12", "B8A", "B4"], "strategy": "band_selection"},
    "REALITY":        {"bands": ["B4", "B3", "B2"],   "strategy": "band_selection"},
    "NDVI":           {"bands": ["B8", "B4"],          "strategy": "normalized_diff"},
    "NBR":            {"bands": ["B8", "B12"],         "strategy": "normalized_diff"},
    "SCIENCE":        {"bands": ["B8", "B12"],         "strategy": "normalized_diff"},
    "BURN_SEVERITY":  {"bands": ["B8", "B12"],         "strategy": "normalized_diff"},
}
```

**Implementación del nuevo download_thumbnail:**

```python
def download_thumbnail(
    self,
    image: ee.Image,
    bbox: Dict[str, float],
    vis_type: str = "RGB",
    dimensions: Union[int, str] = 768,
    resample: Optional[str] = None,
    format: str = "png",
) -> bytes:
    """Descarga thumbnail como bytes PNG/JPG.
    
    Flujo: download_raw_bands → render local → resize → encode.
    Elimina la dependencia del endpoint :getPixels de GEE.
    
    Args:
        image: imagen Sentinel-2
        bbox: bounding box del episodio
        vis_type: tipo de visualización (RGB, SWIR, NDVI, NBR, etc.)
        dimensions: tamaño máximo en píxeles (int o string "WxH")
        resample: método de resample (no aplica en rendering local, se ignora)
        format: formato de salida ('png', 'jpg')
        
    Returns:
        bytes del thumbnail PNG/JPG
    """
    vis_key = vis_type.upper()
    vis_config = VIS_PARAMS.get(vis_key, VIS_PARAMS["RGB"])
    band_config = _VIS_BANDS.get(vis_key, _VIS_BANDS["RGB"])
    
    # Descargar bandas crudas
    raw = self.download_raw_bands(image, bbox, band_config["bands"])
    
    # Renderizar según estrategia
    if band_config["strategy"] == "normalized_diff":
        img = _render_normalized_difference(
            raw[:, :, 0],
            raw[:, :, 1],
            vis_config.get("min", -0.5),
            vis_config.get("max", 0.5),
            vis_config.get("palette", ["green", "yellow", "red"]),
        )
    else:
        img = _render_band_selection(
            raw,
            vis_config.get("min", 0),
            vis_config.get("max", 3000),
            vis_config.get("gamma", None),
        )
    
    # Resize al tamaño solicitado
    target_dims = _bbox_to_dimensions(bbox, max_dim=768)
    w, h = map(int, target_dims.split("x"))
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    
    # Encode a bytes
    buffer = io.BytesIO()
    save_format = "JPEG" if format.lower() in ("jpg", "jpeg") else "PNG"
    img.save(buffer, format=save_format)
    return buffer.getvalue()
```

**Notas de implementación:**

1. El parámetro `resample` se mantiene en la firma por backward compatibility pero no aplica en rendering local. Documentar con `# resample no aplica en rendering local (el resize usa LANCZOS)`.
2. El parámetro `dimensions` se procesa con `_bbox_to_dimensions` (de fase 1) para mantener aspect ratio correcto.
3. `_with_thumbnail_retry` y `_http_download_with_retry` (de fase 2) dejan de usarse en este método. No eliminarlos: siguen siendo usados por `get_thumbnail_url`.

**Validación:**

```bash
# 1. Firma pública sin cambios
python -c "
from app.services.gee_service import GEEService
import inspect
sig = inspect.signature(GEEService.download_thumbnail)
params = list(sig.parameters.keys())
expected = ['self', 'image', 'bbox', 'vis_type', 'dimensions', 'resample', 'format']
assert params == expected, f'Firma cambió: {params} != {expected}'
print('Firma OK')
"

# 2. No hay uso de getThumbURL dentro de download_thumbnail
# (grep entre la definición de download_thumbnail y el siguiente método)
grep -A 50 "def download_thumbnail" app/services/gee_service.py | grep -c "getThumbURL"
# Debe retornar 0

# 3. download_thumbnail usa download_raw_bands
grep -A 50 "def download_thumbnail" app/services/gee_service.py | grep -c "download_raw_bands"
# Debe retornar 1
```

---

## LR-05. Refactorizar download_dnbr_thumbnail

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 1 h |
| **Dependencias** | LR-01, LR-03 |

**Objetivo:** reemplazar la descarga de dNBR renderizado server-side por cálculo local. Requiere 2 llamadas a `download_raw_bands` (pre + post).

```python
def download_dnbr_thumbnail(
    self,
    pre_image: ee.Image,
    post_image: ee.Image,
    bbox: Dict[str, float],
    dimensions: int = 512,
    format: str = "png",
) -> bytes:
    """Descarga thumbnail dNBR renderizado localmente.
    
    Descarga bandas NIR+SWIR de ambas imágenes, calcula dNBR
    localmente y aplica colormap.
    
    Args:
        pre_image: imagen Sentinel-2 pre-incendio
        post_image: imagen Sentinel-2 post-incendio
        bbox: bounding box del episodio
        dimensions: tamaño máximo en píxeles
        format: formato de salida ('png', 'jpg')
        
    Returns:
        bytes del thumbnail PNG/JPG
    """
    # Descargar bandas B8 (NIR) y B12 (SWIR2) de ambas imágenes
    pre_bands = self.download_raw_bands(pre_image, bbox, ["B8", "B12"])
    post_bands = self.download_raw_bands(post_image, bbox, ["B8", "B12"])
    
    # Calcular NBR = (B8 - B12) / (B8 + B12)
    eps = 1e-10
    pre_nbr = (pre_bands[:, :, 0] - pre_bands[:, :, 1]) / (
        pre_bands[:, :, 0] + pre_bands[:, :, 1] + eps
    )
    post_nbr = (post_bands[:, :, 0] - post_bands[:, :, 1]) / (
        post_bands[:, :, 0] + post_bands[:, :, 1] + eps
    )
    
    # dNBR = pre - post
    dnbr = (pre_nbr - post_nbr).astype(np.float32)
    
    # Renderizar con colormap de DNBR
    vis_config = VIS_PARAMS.get("DNBR", {"min": -0.5, "max": 0.5})
    palette = vis_config.get(
        "palette",
        ["#00FF00", "#FFFF00", "#FF7F00", "#FF0000", "#000000"],
    )
    
    normalized = np.clip(
        (dnbr - vis_config["min"]) / (vis_config["max"] - vis_config["min"]),
        0, 1,
    )
    cmap = LinearSegmentedColormap.from_list("dnbr", palette, N=256)
    colored = (cmap(normalized)[:, :, :3] * 255).astype(np.uint8)
    img = Image.fromarray(colored, mode="RGB")
    
    # Resize
    target_dims = _bbox_to_dimensions(bbox, max_dim=dimensions)
    w, h = map(int, target_dims.split("x"))
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    
    # Encode
    buffer = io.BytesIO()
    save_format = "JPEG" if format.lower() in ("jpg", "jpeg") else "PNG"
    img.save(buffer, format=save_format)
    return buffer.getvalue()
```

**Nota sobre cuota:** este método hace 2 llamadas a GEE (`download_raw_bands` × 2) vs 2 del flujo anterior (`get_dnbr_thumbnail_url` + `requests.get`). El consumo de cuota es equivalente.

**Validación:**

```bash
# 1. Firma sin cambios
python -c "
from app.services.gee_service import GEEService
import inspect
sig = inspect.signature(GEEService.download_dnbr_thumbnail)
params = list(sig.parameters.keys())
expected = ['self', 'pre_image', 'post_image', 'bbox', 'dimensions', 'format']
assert params == expected, f'Firma cambió: {params}'
print('Firma OK')
"

# 2. No hay uso de get_dnbr_thumbnail_url dentro de download_dnbr_thumbnail
grep -A 40 "def download_dnbr_thumbnail" app/services/gee_service.py | grep -c "get_dnbr_thumbnail_url"
# Debe retornar 0
```

---

## LR-06. Agregar imports necesarios

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` (cabecera) |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 5 min |
| **Dependencias** | LR-01 |

**Verificar** que los siguientes imports existen en la cabecera del archivo. Agregar los faltantes:

```python
import io
import numpy as np
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap
```

**Validación:**

```bash
grep -n "import numpy" app/services/gee_service.py
grep -n "from PIL" app/services/gee_service.py
grep -n "LinearSegmentedColormap" app/services/gee_service.py
grep -n "import io" app/services/gee_service.py
# Cada uno debe retornar al menos 1 resultado
```

---

## LR-07. Preservar get_thumbnail_url y get_dnbr_thumbnail_url

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 15 min |
| **Dependencias** | LR-04, LR-05 |

**Objetivo:** confirmar que `get_thumbnail_url` y `get_dnbr_thumbnail_url` (que usan `getThumbURL`) no fueron modificados. Estos métodos siguen siendo usados por endpoints REST que devuelven URLs al frontend.

**Agregar docstring aclaratorio** al inicio de cada método:

```python
def get_thumbnail_url(self, image, bbox, vis_type="RGB", ...):
    """Genera URL temporal de thumbnail renderizado server-side por GEE.
    
    Usa el endpoint :getPixels de GEE. La URL es válida por ~2 horas.
    
    NOTA: para descarga de bytes (carousel, reportes), usar download_thumbnail()
    que usa rendering local y no depende de :getPixels.
    """
```

```python
def get_dnbr_thumbnail_url(self, pre_image, post_image, bbox, ...):
    """Genera URL temporal de thumbnail dNBR renderizado server-side por GEE.
    
    NOTA: para descarga de bytes, usar download_dnbr_thumbnail()
    que usa rendering local.
    """
```

**Validación:**

```bash
# get_thumbnail_url sigue usando getThumbURL
grep -A 80 "def get_thumbnail_url" app/services/gee_service.py | grep -c "getThumbURL"
# Debe retornar 1

# get_dnbr_thumbnail_url sigue usando getThumbURL
grep -A 50 "def get_dnbr_thumbnail_url" app/services/gee_service.py | grep -c "getThumbURL"
# Debe retornar 1
```

---

## LR-08. Test de regresión con datos reales (1 test E2E manual)

| Campo | Valor |
|-------|-------|
| **Ejecución** | En producción (VM) |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 30 min |
| **Dependencias** | LR-04, LR-05 deployados |

**Objetivo:** verificar que el carousel genera thumbnails válidos con el nuevo flujo.

**Paso 1: forzar regeneración de un episodio con slides existentes (sabemos que tiene imagen Sentinel-2):**

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}'
```

**Paso 2: monitorear logs buscando el nuevo flujo:**

```bash
docker logs --tail 100 -f forestguard-worker-gee 2>&1 | grep -iE "download_raw_bands|render|computePixels|carousel"
```

**Paso 3: verificar que no hay errores `:getPixels` en los métodos de descarga:**

```bash
docker logs forestguard-worker-gee 2>&1 | tail -200 | grep -c "getPixels"
# Debe ser 0 en líneas de download_thumbnail/download_dnbr_thumbnail
# Puede aparecer en get_thumbnail_url (endpoints REST), eso es esperado
```

**Paso 4: verificar que los thumbnails se subieron a OCI:**

```sql
SELECT id,
       slides_status,
       jsonb_array_length(slides_data) AS num_slides,
       updated_at
FROM fire_episodes
WHERE slides_status = 'ready'
ORDER BY updated_at DESC
LIMIT 5;
```

**Paso 5: verificar visualmente un thumbnail:**

```sql
SELECT slides_data->0->>'thumbnail_url' AS url
FROM fire_episodes
WHERE slides_status = 'ready'
ORDER BY updated_at DESC
LIMIT 1;
```

Abrir la URL en un navegador y confirmar que no hay franjas vacías ni artefactos visuales.

**Paso 6: comparar RAM del worker:**

```bash
docker stats --no-stream forestguard-worker-gee --format '{{.MemUsage}}'
# Comparar con el valor de LR-00. Delta esperado: < 10 MB.
```

---

## Gate de validación final

Ejecutar antes de considerar la migración completa:

```bash
# 1. Archivo compila y todos los métodos existen
python -c "
from app.services.gee_service import (
    GEEService, get_gee_service,
    _render_band_selection, _render_normalized_difference,
    _bbox_to_geometry, _bbox_to_dimensions,
)
svc = GEEService.__new__(GEEService)
assert hasattr(svc, 'download_raw_bands')
assert hasattr(svc, 'download_thumbnail')
assert hasattr(svc, 'download_dnbr_thumbnail')
assert hasattr(svc, 'get_thumbnail_url')
assert hasattr(svc, 'get_dnbr_thumbnail_url')
print('Todos los métodos existen')
"

# 2. Consumidores importan sin error
python -c "
from app.services.imagery_service import *
from app.services.vae_service import *
from app.services.ers_service import *
from app.services.closure_report_service import *
print('Consumidores OK')
"

# 3. _VIS_BANDS cubre todos los vis_types de VIS_PARAMS
python -c "
from app.services.gee_service import VIS_PARAMS, _VIS_BANDS
missing = set(VIS_PARAMS.keys()) - set(_VIS_BANDS.keys()) - {'DNBR'}  # DNBR usa método propio
if missing:
    print(f'FALTA en _VIS_BANDS: {missing}')
    exit(1)
print(f'_VIS_BANDS cubre {len(_VIS_BANDS)} vis_types. OK')
"

# 4. get_thumbnail_url sigue usando getThumbURL (no fue modificado)
grep -c "getThumbURL" app/services/gee_service.py
# Debe retornar >= 2 (uno en get_thumbnail_url, uno en get_dnbr_thumbnail_url)

# 5. download_thumbnail NO usa getThumbURL
grep -A 40 "def download_thumbnail" app/services/gee_service.py | grep "getThumbURL" && echo "ERROR: download_thumbnail aún usa getThumbURL" || echo "OK: download_thumbnail usa rendering local"

# 6. download_dnbr_thumbnail NO usa get_dnbr_thumbnail_url
grep -A 40 "def download_dnbr_thumbnail" app/services/gee_service.py | grep "get_dnbr_thumbnail_url" && echo "ERROR" || echo "OK"

# 7. Rendering local produce PNGs válidos (test sintético)
python -c "
import numpy as np
from app.services.gee_service import _render_band_selection, _render_normalized_difference

# Band selection
img1 = _render_band_selection(
    np.random.uniform(0, 5000, (100, 150, 3)).astype(np.float32),
    [0, 0, 0], [5000, 5000, 5000], [1.0, 1.0, 1.0]
)
assert img1.size == (150, 100) and img1.mode == 'RGB'

# Normalized difference
img2 = _render_normalized_difference(
    np.random.uniform(500, 4000, (100, 150)).astype(np.float32),
    np.random.uniform(100, 2000, (100, 150)).astype(np.float32),
    -0.2, 0.8, ['brown', 'yellow', 'green', 'darkgreen']
)
assert img2.size == (150, 100) and img2.mode == 'RGB'
print('Rendering local OK')
"
```

---

## Roadmap actualizado

| Fase | Tarea | Estado |
|------|-------|--------|
| 1 | Bugfix + limpieza | ✅ Deployada |
| 2 | DRY helpers (bbox, dims, retry) | ✅ Deployada |
| **2b** | **Rendering local (este documento)** | **⏳ Pendiente** |
| 3 | Separación en paquete gee/ | ⏳ Pendiente (post-2b) |

Después de completar 2b, los helpers de retry (`_with_thumbnail_retry`, `_http_download_with_retry`) quedan en uso solo por `get_thumbnail_url` y `get_dnbr_thumbnail_url`. En la fase 3, cuando se extraiga `thumbnails.py`, estos helpers migran con los métodos que los usan.
