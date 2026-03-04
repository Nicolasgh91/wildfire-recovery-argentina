# Tareas técnicas: patrón visualize() + batería de estrés

> **Propósito:** guiar a Claude Code en la refactorización de `get_thumbnail_url`, `get_dnbr_thumbnail_url`, `download_thumbnail` y `download_dnbr_thumbnail` para usar el patrón `.visualize()` + `getThumbURL(dimensions)`, eliminando el `reproject` manual que causa HTTP 500 en `:getPixels`.
> Incluye 5 tests de estrés con criterios de aceptación y reporte de salida.

---

## Estado previo

| Fase | Estado |
|------|--------|
| Fase 1 (bugfix: `_bbox_to_dimensions`, `Optional[date]`, sun_elevation, factory, dead code) | ✅ Deployada |
| Fase 2 (DRY: `_bbox_to_geometry`, `_thumb_size_params`, `_with_thumbnail_retry`, `_http_download_with_retry`) | ✅ Deployada |
| Fase 2c (este documento: patrón `visualize()` + tests de estrés) | ⏳ Pendiente |

## Diagnóstico raíz

El flujo actual construye la imagen así:

```python
vis_image = image.select(bands)           # bandas crudas, multi-banda
vis_image = vis_image.clip(geometry)       # recorte al bbox
vis_image = vis_image.reproject(           # ← FORZAR reproyección explícita
    crs="EPSG:4326", scale=safe_scale
)
url = vis_image.getThumbURL({              # pedir al servidor que renderice
    "region": geometry,
    "format": "png",
    **size_params,        # dimensions
    **vis_params,         # min, max, gamma, palette
})
```

El problema: `reproject()` fuerza a GEE a materializar todos los píxeles a la escala indicada **antes** de generar el thumbnail. Para imágenes SWIR (20m nativos) en bboxes de ~100 km², esto genera cómputos que exceden los recursos internos de `:getPixels`, resultando en HTTP 500.

La solución: delegar la composición completa a `.visualize()`, que produce una imagen RGB de 8 bits lista para renderizar, y dejar que `getThumbURL` con `dimensions` se encargue del resize sin necesidad de `reproject`:

```python
rendered = image.visualize(                # ← GEE pre-renderiza a RGB 8-bit
    bands=["B12", "B11", "B4"],
    min=[0, 0, 0],
    max=[5000, 5000, 5000],
    gamma=[1.0, 1.0, 1.0],
)
rendered = rendered.clip(geometry)         # recortar al bbox
# SIN reproject → GEE usa la resolución nativa y solo resizea al generar thumb

url = rendered.getThumbURL({
    "region": geometry,
    "dimensions": "768x384",               # _bbox_to_dimensions controla aspect ratio
    "format": "png",
    "crs": "EPSG:4326",                    # mantener proyección del pipeline
})
```

---

## Restricciones

1. **Firmas públicas:** no cambiar firmas de `get_thumbnail_url`, `get_dnbr_thumbnail_url`, `download_thumbnail`, `download_dnbr_thumbnail`.
2. **Proyección:** mantener `EPSG:4326` como CRS (todo el pipeline: PostGIS, Leaflet, OCI trabaja en 4326).
3. **Transparencia:** usar `format='png'` sin `.unmask()` para que los píxeles sin datos (nubes enmascaradas, borde de órbita) se rendericen como transparencia en el canal alpha.
4. **Dependencias:** no agregar paquetes nuevos. No usar numpy/PIL para rendering (todo server-side en GEE).
5. **Helpers de fase 2:** reutilizar `_bbox_to_geometry`, `_bbox_to_dimensions`, `_thumb_size_params`, `_with_thumbnail_retry`, `_http_download_with_retry`.

---

## VZ-01. Refactorizar get_thumbnail_url con patrón visualize()

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` — método `get_thumbnail_url` |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 2 h |
| **Dependencias** | Helpers de fase 1 y 2 disponibles |

**Cambio principal:** reemplazar el bloque `select → clip → reproject → getThumbURL(vis_params)` por `visualize → clip → getThumbURL(dimensions)`.

**Código de referencia para el interior de `_get_url()`:**

```python
def _get_url():
    geometry = _bbox_to_geometry(bbox)
    vis_key = vis_type.upper()
    
    # --- Paso 1: construir imagen pre-renderizada con visualize() ---
    if vis_key == "NDVI":
        nir = image.select("B8")
        red = image.select("B4")
        index_img = nir.subtract(red).divide(nir.add(red))
        rendered = index_img.visualize(**{
            k: v for k, v in VIS_PARAMS["NDVI"].items() if k != "bands"
        })
    
    elif vis_key in ("NBR", "SCIENCE", "BURN_SEVERITY"):
        nir = image.select("B8")
        swir = image.select("B12")
        index_img = nir.subtract(swir).divide(nir.add(swir))
        vis_cfg = VIS_PARAMS.get(vis_key, VIS_PARAMS.get("NBR"))
        rendered = index_img.visualize(**{
            k: v for k, v in vis_cfg.items() if k != "bands"
        })
    
    elif vis_key in VIS_PARAMS and "bands" in VIS_PARAMS[vis_key]:
        cfg = VIS_PARAMS[vis_key]
        rendered = image.visualize(
            bands=cfg["bands"],
            **{k: v for k, v in cfg.items() if k != "bands"}
        )
    
    else:
        rendered = image.visualize(
            bands=BANDS["RGB"],
            min=0, max=3000,
        )
    
    # --- Paso 2: clip al bbox (sin reproject) ---
    rendered = rendered.clip(geometry)
    
    # --- Paso 3: generar URL con dimensions proporcional al bbox ---
    dim_str = _bbox_to_dimensions(bbox, max_dim=768)
    
    url = rendered.getThumbURL({
        "region": geometry,
        "dimensions": dim_str,
        "format": format,
        "crs": "EPSG:4326",
    })
    
    return url
```

**Lo que se elimina:**

- `_compute_safe_scale(bbox)` — ya no se necesita porque no hay `reproject`.
- `.reproject(crs="EPSG:4326", scale=safe_scale)` — eliminado; GEE usa resolución nativa.
- `vis_params` como kwargs separados en `getThumbURL` — ahora están dentro de `visualize()`.
- `_thumb_size_params(dimensions)` — reemplazado por `_bbox_to_dimensions` directo.

**Lo que se preserva:**

- `.clip(geometry)` — sigue siendo necesario para limitar el cómputo al bbox.
- `_bbox_to_geometry(bbox)` — helper de fase 2.
- `_bbox_to_dimensions(bbox, max_dim)` — helper de fase 1.
- `_with_thumbnail_retry` — encapsula el loop de retry (herencia de fase 2).
- `format='png'` por default — preserva transparencia en canal alpha.

**Nota sobre `resample`:** el parámetro se mantiene en la firma pero se ignora. `visualize()` + `dimensions` maneja el resample internamente. Documentar: `# resample ignorado: visualize() + dimensions maneja el rescalado internamente`.

**Validación:**

```bash
# 1. No queda .reproject dentro de get_thumbnail_url
grep -A 80 "def get_thumbnail_url" app/services/gee_service.py | grep -c "reproject"
# Debe retornar 0

# 2. Usa .visualize()
grep -A 80 "def get_thumbnail_url" app/services/gee_service.py | grep -c "\.visualize("
# Debe retornar >= 1

# 3. No pasa vis_params a getThumbURL (min/max/gamma/palette van en visualize)
grep -A 80 "def get_thumbnail_url" app/services/gee_service.py | grep "getThumbURL" | grep -c "vis_params"
# Debe retornar 0

# 4. Usa _bbox_to_dimensions
grep -A 80 "def get_thumbnail_url" app/services/gee_service.py | grep -c "_bbox_to_dimensions"
# Debe retornar 1
```

---

## VZ-02. Refactorizar get_dnbr_thumbnail_url con patrón visualize()

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` — método `get_dnbr_thumbnail_url` |
| **Prioridad** | P0 — crítico |
| **Esfuerzo** | 1 h |
| **Dependencias** | VZ-01 (mismo patrón) |

**Código de referencia para el interior de `_get_url()`:**

```python
def _get_url():
    geometry = _bbox_to_geometry(bbox)
    
    nbr_pre = pre_image.normalizedDifference(["B8", "B12"])
    nbr_post = post_image.normalizedDifference(["B8", "B12"])
    dnbr = nbr_pre.subtract(nbr_post)
    
    vis_cfg = VIS_PARAMS.get("DNBR", {"min": -0.5, "max": 0.5})
    rendered = dnbr.visualize(**{
        k: v for k, v in vis_cfg.items() if k != "bands"
    })
    rendered = rendered.clip(geometry)
    
    dim_str = _bbox_to_dimensions(bbox, max_dim=768)
    
    url = rendered.getThumbURL({
        "region": geometry,
        "dimensions": dim_str,
        "format": format,
        "crs": "EPSG:4326",
    })
    return url
```

**Lo que se elimina:** `_compute_safe_scale`, `.reproject()`, parsing manual de `size_params` y `vis_params`.

**Validación:**

```bash
grep -A 50 "def get_dnbr_thumbnail_url" app/services/gee_service.py | grep -c "reproject"
# Debe retornar 0

grep -A 50 "def get_dnbr_thumbnail_url" app/services/gee_service.py | grep -c "\.visualize("
# Debe retornar 1
```

---

## VZ-03. Simplificar download_thumbnail y download_dnbr_thumbnail

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P1 — alto |
| **Esfuerzo** | 30 min |
| **Dependencias** | VZ-01, VZ-02 |

**Objetivo:** estos métodos ya delegan a `get_thumbnail_url` / `get_dnbr_thumbnail_url` para obtener la URL y luego descargan vía HTTP. Con el nuevo patrón `visualize()`, el flujo no cambia pero los retry de descarga HTTP deben usar `_http_download_with_retry` (de fase 2):

```python
def download_thumbnail(self, image, bbox, vis_type="RGB", 
                       dimensions=768, resample=None, format="png"):
    """Descarga thumbnail como bytes PNG/JPG."""
    url = self.get_thumbnail_url(image, bbox, vis_type, dimensions, resample, format)
    return self._http_download_with_retry(url, context_label=vis_type)

def download_dnbr_thumbnail(self, pre_image, post_image, bbox, 
                            dimensions=512, format="png"):
    """Descarga thumbnail dNBR como bytes."""
    url = self.get_dnbr_thumbnail_url(pre_image, post_image, bbox, 
                                       dimensions=dimensions, format=format)
    return self._http_download_with_retry(url, context_label="DNBR")
```

**Validación:**

```bash
# download_thumbnail debe ser ~3-5 líneas (sin loop manual de retry)
grep -A 10 "def download_thumbnail" app/services/gee_service.py | grep -c "for attempt"
# Debe retornar 0

# Usa _http_download_with_retry
grep -A 10 "def download_thumbnail" app/services/gee_service.py | grep -c "_http_download_with_retry"
# Debe retornar 1
```

---

## VZ-04. Eliminar _compute_safe_scale si no tiene otros consumidores

| Campo | Valor |
|-------|-------|
| **Archivo** | `app/services/gee_service.py` |
| **Prioridad** | P2 — medio |
| **Esfuerzo** | 15 min |
| **Dependencias** | VZ-01, VZ-02 |

**Verificar:**

```bash
grep -n "_compute_safe_scale" app/services/gee_service.py
# Si solo aparece en su propia definición → eliminar
# Si otros métodos la usan (ej: calculate_ndvi, calculate_nbr) → mantener
```

Si `_compute_safe_scale` solo era usada por `get_thumbnail_url` y `get_dnbr_thumbnail_url`, eliminarla junto con la constante `GEE_THUMB_MAX_PIXELS`.

---

## VZ-05. Gate de validación pre-deploy

Ejecutar antes del merge:

```bash
# 1. Archivo compila
python -c "
from app.services.gee_service import GEEService, get_gee_service
from app.services.gee_service import _bbox_to_geometry, _bbox_to_dimensions
print('Imports OK')
"

# 2. Consumidores importan sin error
python -c "
from app.services.imagery_service import *
from app.services.vae_service import *
from app.services.ers_service import *
from app.services.closure_report_service import *
print('Consumidores OK')
"

# 3. No queda .reproject en métodos de thumbnail
grep -c "reproject" app/services/gee_service.py
# Anotar el número. Si solo aparece en calculate_ndvi / calculate_nbr → OK.
# NO debe aparecer en get_thumbnail_url ni get_dnbr_thumbnail_url.

# 4. .visualize() presente en ambos métodos de URL
grep -c "\.visualize(" app/services/gee_service.py
# Debe ser >= 2

# 5. getThumbURL no recibe vis_params (min/max/gamma/palette)
grep "getThumbURL" app/services/gee_service.py | grep -cE "min|max|gamma|palette"
# Debe retornar 0

# 6. format='png' se mantiene como default (transparencia)
grep "def get_thumbnail_url" app/services/gee_service.py
grep "def get_dnbr_thumbnail_url" app/services/gee_service.py
# Ambos deben mostrar format: str = "png"
```

---

## Batería de tests de estrés

> Estos tests se ejecutan en producción (VM) después del deploy. Cada test requiere autenticación GEE activa en el worker-gee. Consumo estimado de cuota: ~20 requests GEE en total.

### ST-01. Latitud extrema (Tierra del Fuego)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Validar que EPSG:4326 no distorsiona thumbnails en latitudes sur (-54°) |
| **Esfuerzo** | 10 min |

**Script de ejecución:**

```python
"""Ejecutar dentro del contenedor worker-gee:
docker exec forestguard-worker-gee python -c "<este_script>"
"""
import ee, requests, struct
from app.services.gee_service import GEEService, _bbox_to_dimensions

svc = GEEService()
svc.authenticate()

# Bbox simulado en Tierra del Fuego
bbox_tdf = {"west": -69.5, "south": -54.9, "east": -69.2, "north": -54.7}

# Buscar imagen reciente
collection = svc.get_sentinel_collection(bbox_tdf, "2025-06-01", "2025-12-31", max_cloud_cover=50)
info = collection.size().getInfo()
print(f"Imágenes disponibles en TdF: {info}")

if info > 0:
    best = svc.get_best_image(collection, None, prefer_low_cloud=True)
    
    # Generar thumbnail con el nuevo patrón
    url = svc.get_thumbnail_url(best, bbox_tdf, vis_type="RGB", dimensions=512)
    print(f"URL generada: {url[:80]}...")
    
    # Descargar y verificar dimensiones del PNG
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    png_bytes = resp.content
    
    # Leer dimensiones del header PNG (bytes 16-23)
    w = struct.unpack(">I", png_bytes[16:20])[0]
    h = struct.unpack(">I", png_bytes[20:24])[0]
    
    expected_dims = _bbox_to_dimensions(bbox_tdf, max_dim=512)
    exp_w, exp_h = map(int, expected_dims.split("x"))
    
    print(f"Dimensiones PNG: {w}x{h}")
    print(f"Dimensiones esperadas: {exp_w}x{exp_h}")
    
    aspect_real = abs(bbox_tdf["east"] - bbox_tdf["west"]) / abs(bbox_tdf["north"] - bbox_tdf["south"])
    aspect_img = w / h
    aspect_delta = abs(aspect_real - aspect_img) / aspect_real * 100
    
    print(f"Aspect ratio bbox: {aspect_real:.2f}")
    print(f"Aspect ratio PNG:  {aspect_img:.2f}")
    print(f"Delta: {aspect_delta:.1f}%")
    
    assert aspect_delta < 10, f"FALLO: distorsión de aspect ratio {aspect_delta:.1f}% > 10%"
    assert w > 0 and h > 0, "FALLO: dimensiones cero"
    print("ST-01 PASS")
else:
    print("ST-01 SKIP: no hay imágenes Sentinel-2 en TdF para el rango")
```

**Criterio de aceptación:** el delta de aspect ratio entre el bbox geográfico y el PNG generado debe ser < 10%. La imagen no debe verse "achatada" verticalmente.

**Reporte de salida:**

```
ST-01 | Latitud extrema (Tierra del Fuego)
Estado:     [ PASS | FAIL | SKIP ]
Bbox:       west=-69.5, south=-54.9, east=-69.2, north=-54.7
Dims PNG:   WxH
Aspect bbox: X.XX
Aspect PNG:  X.XX
Delta:      X.X%
Notas:      
```

---

### ST-02. Borde de órbita (swath edge)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Validar que píxeles sin datos en borde de órbita se renderizan como transparencia PNG, sin error ni franjas negras sólidas |
| **Esfuerzo** | 15 min |

**Script de ejecución:**

```python
"""Ejecutar dentro del contenedor worker-gee"""
import ee, requests, struct
from PIL import Image
import io
from app.services.gee_service import GEEService

svc = GEEService()
svc.authenticate()

# Bbox amplio que cruza el borde de órbita de Sentinel-2
# (zona central de Argentina, amplia para captar swath edge)
bbox_edge = {"west": -66.0, "south": -33.0, "east": -64.5, "north": -32.5}

# Imagen específica (elegir una donde se sepa que el bbox cruza el borde)
# Alternativa: usar un bbox intencionalmente desplazado
collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
    .filterBounds(ee.Geometry.Rectangle([-66.0, -33.0, -64.5, -32.5])) \
    .filterDate("2025-10-01", "2025-10-15") \
    .sort("CLOUDY_PIXEL_PERCENTAGE") \
    .limit(1)

info = collection.size().getInfo()
print(f"Imágenes: {info}")

if info > 0:
    img = collection.first()
    url = svc.get_thumbnail_url(img, bbox_edge, vis_type="SWIR", dimensions=512)
    print(f"URL: {url[:80]}...")
    
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    
    # Verificar que es PNG con canal alpha
    pil_img = Image.open(io.BytesIO(resp.content))
    print(f"Modo: {pil_img.mode}")
    print(f"Size: {pil_img.size}")
    
    has_alpha = pil_img.mode in ("RGBA", "LA", "PA")
    if has_alpha:
        import numpy as np
        alpha = np.array(pil_img.split()[-1])
        transparent_pct = (alpha == 0).sum() / alpha.size * 100
        opaque_pct = (alpha == 255).sum() / alpha.size * 100
        print(f"Píxeles transparentes: {transparent_pct:.1f}%")
        print(f"Píxeles opacos: {opaque_pct:.1f}%")
        
        # Debe haber ALGO transparente (borde) y ALGO opaco (datos)
        has_both = transparent_pct > 0.1 and opaque_pct > 10
        print(f"Tiene ambos (datos + transparencia): {has_both}")
    else:
        print("NOTA: PNG sin canal alpha. Verificar si GEE retornó RGB puro.")
        transparent_pct = 0
        has_both = False
    
    assert resp.status_code == 200, f"FALLO: status {resp.status_code}"
    print("ST-02 PASS (sin error 500)")
else:
    print("ST-02 SKIP: no hay imágenes para el rango")
```

**Criterio de aceptación:** GEE no retorna error 500. Si el bbox cruza el borde de órbita, los píxeles sin datos aparecen como transparencia (alpha=0) en el PNG, no como franjas negras sólidas. Si la imagen cubre todo el bbox, se acepta como PASS igualmente (no hubo borde de órbita).

**Reporte de salida:**

```
ST-02 | Borde de órbita (swath edge)
Estado:           [ PASS | FAIL | SKIP ]
Bbox:             west=-66.0, south=-33.0, east=-64.5, north=-32.5
HTTP status:      200
Modo PNG:         RGBA | RGB
Transparentes:    X.X%
Opacos:           X.X%
Tiene ambos:      true | false
Notas:            
```

---

### ST-03. Geometría anómala (ratio extremo)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Validar que un bbox largo y estrecho (50:1) produce un thumbnail proporcional sin distorsión |
| **Esfuerzo** | 10 min |

**Script de ejecución:**

```python
"""Ejecutar dentro del contenedor worker-gee"""
import ee, requests, struct
from app.services.gee_service import GEEService, _bbox_to_dimensions

svc = GEEService()
svc.authenticate()

# Bbox extremo: ~50km largo × ~1km ancho (a lo largo de la RN40)
bbox_strip = {"west": -70.05, "south": -42.5, "east": -70.04, "north": -42.0}

ancho = abs(bbox_strip["east"] - bbox_strip["west"])
alto = abs(bbox_strip["north"] - bbox_strip["south"])
ratio = alto / ancho  # ~50:1 vertical
print(f"Bbox: {ancho:.4f}° × {alto:.4f}° → ratio {ratio:.1f}:1")

dims = _bbox_to_dimensions(bbox_strip, max_dim=768)
w, h = map(int, dims.split("x"))
print(f"Dimensions calculadas: {dims} (w={w}, h={h})")

# Verificar que se respeta el ratio
assert h == 768, f"FALLO: altura debe ser 768 (max_dim), got {h}"
assert w >= 1, f"FALLO: ancho debe ser >= 1, got {w}"
assert w < 50, f"FALLO: ancho debe ser estrecho (<50px), got {w}"

img_ratio = h / w
ratio_delta = abs(ratio - img_ratio) / ratio * 100
print(f"Ratio bbox: {ratio:.1f}:1")
print(f"Ratio dims: {img_ratio:.1f}:1")
print(f"Delta: {ratio_delta:.1f}%")

# Intentar generar thumbnail real
collection = svc.get_sentinel_collection(bbox_strip, "2025-06-01", "2025-12-31", max_cloud_cover=50)
count = collection.size().getInfo()
print(f"Imágenes: {count}")

if count > 0:
    best = svc.get_best_image(collection, None, prefer_low_cloud=True)
    url = svc.get_thumbnail_url(best, bbox_strip, vis_type="RGB", dimensions=768)
    
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    
    png_w = struct.unpack(">I", resp.content[16:20])[0]
    png_h = struct.unpack(">I", resp.content[20:24])[0]
    print(f"PNG real: {png_w}x{png_h}")
    
    assert png_w >= 1 and png_h >= 1, "FALLO: dimensiones cero"
    assert resp.status_code == 200, f"FALLO: status {resp.status_code}"
    print("ST-03 PASS")
else:
    assert ratio_delta < 15, f"FALLO: delta de ratio {ratio_delta:.1f}% > 15%"
    print("ST-03 PASS (solo cálculo, sin imagen)")
```

**Criterio de aceptación:** `_bbox_to_dimensions` produce dimensiones donde el lado mayor = `max_dim` (768) y el menor es proporcional al ratio del bbox. El thumbnail resultante no está estirado a un cuadrado.

**Reporte de salida:**

```
ST-03 | Geometría anómala (ratio 50:1)
Estado:          [ PASS | FAIL ]
Bbox:            0.01° × 0.50° → ratio 50:1
Dims calculadas: Wx768
Ratio delta:     X.X%
PNG real:        WxH (si se generó)
Notas:           
```

---

### ST-04. Alta nubosidad (cloud masking + transparencia)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Verificar que los píxeles enmascarados por nubes se renderizan como transparencia PNG, no como negro ni ruido |
| **Esfuerzo** | 15 min |

**Script de ejecución:**

```python
"""Ejecutar dentro del contenedor worker-gee"""
import ee, requests
from PIL import Image
import numpy as np
import io
from app.services.gee_service import GEEService

svc = GEEService()
svc.authenticate()

# Buscar imagen con alta nubosidad en zona conocida
bbox_cloudy = {"west": -65.0, "south": -35.0, "east": -64.5, "north": -34.5}

collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
    .filterBounds(ee.Geometry.Rectangle([-65.0, -35.0, -64.5, -34.5])) \
    .filterDate("2025-06-01", "2025-08-31") \
    .filter(ee.Filter.gt("CLOUDY_PIXEL_PERCENTAGE", 60)) \
    .sort("CLOUDY_PIXEL_PERCENTAGE", False) \
    .limit(1)

count = collection.size().getInfo()
print(f"Imágenes con >60% nubes: {count}")

if count > 0:
    img = collection.first()
    cloud_pct = img.getInfo()["properties"].get("CLOUDY_PIXEL_PERCENTAGE", 0)
    print(f"Nubosidad: {cloud_pct:.1f}%")
    
    # Aplicar cloud mask (como hace el pipeline)
    masked = svc.apply_cloud_mask(img)
    
    url = svc.get_thumbnail_url(masked, bbox_cloudy, vis_type="RGB", dimensions=512)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    
    pil_img = Image.open(io.BytesIO(resp.content))
    print(f"Modo: {pil_img.mode}, Size: {pil_img.size}")
    
    if pil_img.mode == "RGBA":
        alpha = np.array(pil_img.split()[-1])
        transparent_pct = (alpha == 0).sum() / alpha.size * 100
        print(f"Píxeles transparentes: {transparent_pct:.1f}%")
        
        # Con 60%+ de nubes enmascaradas, debería haber >30% de transparencia
        assert transparent_pct > 5, (
            f"FALLO: solo {transparent_pct:.1f}% transparente con {cloud_pct:.0f}% nubes. "
            f"¿Cloud mask está funcionando?"
        )
        
        # Verificar que NO hay franjas negras sólidas (RGB=0,0,0 con alpha=255)
        rgba = np.array(pil_img)
        black_opaque = (
            (rgba[:,:,0] == 0) & (rgba[:,:,1] == 0) & 
            (rgba[:,:,2] == 0) & (rgba[:,:,3] == 255)
        ).sum() / rgba[:,:,0].size * 100
        print(f"Píxeles negro opaco: {black_opaque:.1f}%")
        
        # No más de 5% de negro opaco sólido (algo de sombra es normal)
        assert black_opaque < 5, (
            f"FALLO: {black_opaque:.1f}% de negro opaco. "
            f"¿.unmask(0) se está aplicando accidentalmente?"
        )
        print("ST-04 PASS")
    else:
        print(f"NOTA: PNG modo {pil_img.mode} (sin alpha). GEE no preservó transparencia.")
        print("ST-04 PASS (sin error, pero verificar visualmente)")
else:
    print("ST-04 SKIP: no se encontró imagen con >60% nubes")
```

**Criterio de aceptación:** los huecos dejados por cloud masking se renderizan como píxeles transparentes (alpha=0), no como negro sólido. No debe haber más de 5% de píxeles negro opaco (RGB=0,0,0 con alpha=255).

**Reporte de salida:**

```
ST-04 | Alta nubosidad (cloud masking)
Estado:             [ PASS | FAIL | SKIP ]
Nubosidad imagen:   XX%
Modo PNG:           RGBA | RGB
Transparentes:      X.X%
Negro opaco:        X.X%
Notas:              
```

---

### ST-05. Concurrencia y memoria (15 episodios)

| Campo | Valor |
|-------|-------|
| **Objetivo** | Confirmar que el procesamiento de 15 episodios consecutivos no genera memory leaks en el worker-gee |
| **Esfuerzo** | 20 min (incluye espera de procesamiento) |

**Paso 1: registrar RAM baseline:**

```bash
docker stats --no-stream forestguard-worker-gee --format '{{.MemUsage}}'
# Anotar valor: ej. "185MiB / 947MiB"
```

**Paso 2: forzar regeneración de todos los episodios candidatos:**

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.carousel_task.generate_carousel \
  --kwargs='{"force_refresh": true}'
```

**Paso 3: monitorear RAM cada 30 segundos durante el procesamiento:**

```bash
for i in $(seq 1 20); do
  echo "$(date +%H:%M:%S) $(docker stats --no-stream forestguard-worker-gee --format '{{.MemUsage}}')"
  sleep 30
done
```

**Paso 4: verificar resultados en base de datos:**

```sql
SELECT 
    slides_status,
    COUNT(*) AS total,
    COUNT(*) FILTER (
        WHERE updated_at > NOW() - INTERVAL '1 hour'
    ) AS actualizados_ultima_hora
FROM fire_episodes
WHERE gee_candidate = true
  AND status IN ('active', 'monitoring')
GROUP BY slides_status;
```

**Paso 5: verificar que no hay errores OOM en logs:**

```bash
docker logs forestguard-worker-gee 2>&1 | tail -500 | grep -ciE "oom|killed|memory"
# Debe retornar 0
```

**Paso 6: RAM final:**

```bash
docker stats --no-stream forestguard-worker-gee --format '{{.MemUsage}}'
```

**Criterio de aceptación:**

1. RAM final no excede RAM baseline + 30 MB.
2. No hay mensajes OOM ni killed en logs.
3. Al menos 10 de 15 episodios terminaron con `slides_status='ready'` (los que fallen deben ser por `GEEImageNotFoundError`, no por 500 ni OOM).
4. Los thumbnails generados tienen URLs públicas válidas en OCI.

**Reporte de salida:**

```
ST-05 | Concurrencia y memoria (15 episodios)
Estado:              [ PASS | FAIL ]
RAM baseline:        XXX MiB
RAM pico:            XXX MiB
RAM final:           XXX MiB
Delta RAM:           +XX MiB
Episodios procesados: XX / 15
  - ready:           XX
  - failed:          XX (motivo: ...)
  - pending:         XX
Errores OOM:         0
Tiempo total:        XX min
Notas:               
```

---

## Reporte consolidado de estrés

Al completar los 5 tests, llenar el siguiente reporte y adjuntarlo al PR:

```
═══════════════════════════════════════════════════════════════
REPORTE DE TESTS DE ESTRÉS — Fase 2c (patrón visualize)
Fecha:          YYYY-MM-DD HH:MM UTC
Commit:         <hash>
Ejecutado por:  Claude Code / manual
═══════════════════════════════════════════════════════════════

ST-01 | Latitud extrema       | [ PASS | FAIL | SKIP ]
ST-02 | Borde de órbita       | [ PASS | FAIL | SKIP ]
ST-03 | Geometría anómala     | [ PASS | FAIL | SKIP ]
ST-04 | Alta nubosidad        | [ PASS | FAIL | SKIP ]
ST-05 | Concurrencia/memoria  | [ PASS | FAIL ]

Resultado global: [ APROBADO | RECHAZADO ]

Condición de aprobación:
  - ST-01 a ST-04: al menos 3 de 4 en PASS (SKIP cuenta como neutral)
  - ST-05: obligatorio PASS
  - Ninguno en FAIL

Observaciones:
  (espacio para notas, URLs de thumbnails verificados, etc.)

═══════════════════════════════════════════════════════════════
```

---

## Restricciones para Claude Code

1. **No usar** `.unmask(0)` — los píxeles sin datos deben preservar transparencia vía `format='png'`.
2. **No usar** `EPSG:3857` — mantener `EPSG:4326` en todo el pipeline.
3. **No usar** `reproject()` en los métodos de thumbnail refactorizados. Dejar que `visualize()` + `dimensions` manejen la resolución.
4. **No cambiar** firmas públicas de ningún método.
5. **No agregar** dependencias nuevas a `requirements.txt`.
6. **No modificar** `docker-compose.yml`, `Dockerfile.*`, ni workflows.
7. **Mantener** `_with_thumbnail_retry` para el retry de `get_thumbnail_url` / `get_dnbr_thumbnail_url` (error en generación de URL).
8. **Mantener** `_http_download_with_retry` para el retry de `download_thumbnail` / `download_dnbr_thumbnail` (error en descarga HTTP).
9. **Cada test de estrés** consume cuota GEE (~4 requests por test). Ejecutarlos en horario de baja actividad.
