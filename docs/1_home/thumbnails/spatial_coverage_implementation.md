# Implementación: Cobertura espacial en get_best_image

**Fecha**: 2026-03-04  
**Estado**: ✅ Completado

## Resumen

Se agregó cobertura espacial como criterio de selección en `get_best_image` para priorizar imágenes con alta cobertura de datos válidos sobre el bbox, evitando seleccionar imágenes con baja cobertura espacial aunque tengan menor nubosidad.

## Problema resuelto

Antes: `get_best_image` podía seleccionar una imagen con 0.0001% de nubes pero solo 82% de cobertura espacial, cuando existía otra con 0.01% de nubes y 100% de cobertura.

Ahora: Una imagen con 100% de cobertura y 0.01% de nubes es seleccionada sobre una con 82% de cobertura y 0.0001% de nubes.

## Cambios implementados

### 1. Nuevo método `_calculate_spatial_coverage`

**Ubicación**: `app/services/gee_service.py:799-836`

Calcula el porcentaje de píxeles válidos sobre el bbox usando:
- Banda B4 (siempre presente en Sentinel-2)
- `reduceRegion()` con `scale=60m` para balance velocidad/precisión
- Retorna porcentaje de cobertura (0-100)

### 2. Modificación de `get_best_image`

**Ubicación**: `app/services/gee_service.py:838-1003`

**Nuevos parámetros**:
- `min_coverage: float = 95.0` - Umbral mínimo de cobertura espacial
- `max_candidates: int = 10` - Número de candidatas a evaluar
- `bbox: Optional[Dict[str, float]] = None` - Bounding box para evaluar cobertura

**Lógica implementada** (Camino A - evaluar top-N candidatas client-side):

1. **Si bbox no se proporciona**: usa lógica legacy (sin evaluación de cobertura) para mantener compatibilidad con callers existentes

2. **Si bbox se proporciona**:
   - Obtiene top-10 candidatas por nubosidad/fecha (server-side)
   - Trae candidatas a client-side con `.getInfo()`
   - Evalúa cobertura espacial de cada una (client-side)
   - Filtra por cobertura >= 95%
   - Entre las de alta cobertura, elige por criterio secundario (fecha o nubosidad)
   - Si ninguna cumple >= 95%, elige la de mayor cobertura disponible

**Criterios de selección** (en orden de prioridad):
1. Cobertura de datos válidos >= 95% (filtro preferencial)
2. Si target_date: imagen más cercana a esa fecha
3. Menor nubosidad (CLOUDY_PIXEL_PERCENTAGE)

### 3. Logging mejorado

El método ahora loguea automáticamente:
- Número de imágenes con cobertura >= 95%
- Imagen seleccionada con su cobertura y nubosidad
- Warnings cuando ninguna imagen cumple el umbral de cobertura

## Consumo de cuota GEE

- **Por llamada a `get_best_image` con bbox**: ~10 requests (1 para `getInfo()` + hasta 10 para cobertura)
- **Para 15 episodios del carousel**: 15 × 10 = 150 requests
- **Bien dentro de la cuota de 50K/día**

## Compatibilidad

✅ **Mantiene compatibilidad hacia atrás**: Todos los callers existentes que no especifican `bbox` funcionan sin cambios usando la lógica legacy.

✅ **No requiere cambios en callers**: El parámetro `bbox` es opcional.

## Testing

Se creó script de prueba: `scripts/test_spatial_coverage.py`

**Uso**:
```bash
python scripts/test_spatial_coverage.py
```

**Tests incluidos**:
1. get_best_image SIN bbox (lógica legacy)
2. get_best_image CON bbox (nueva lógica con cobertura)
3. Comparación de resultados entre ambos métodos

## Archivos modificados

1. **`app/services/gee_service.py`**:
   - Agregado método `_calculate_spatial_coverage` (38 líneas)
   - Modificado método `get_best_image` (130 líneas)
   - Actualizado docstring (25 líneas)
   - Total: ~193 líneas modificadas/agregadas

2. **`scripts/test_spatial_coverage.py`** (nuevo):
   - Script de validación (115 líneas)

## Próximos pasos

Para habilitar la evaluación de cobertura en los callers existentes, agregar el parámetro `bbox` en las llamadas a `get_best_image`:

**Ejemplo en `imagery_service.py`**:
```python
# Antes:
image = self._gee.get_best_image(collection)

# Después:
image = self._gee.get_best_image(collection, bbox=bbox)
```

**Callers a actualizar** (opcional, solo si se desea habilitar evaluación de cobertura):
- `app/services/imagery_service.py:602`
- `app/services/vae_service.py:725, 832, 866`
- `app/services/ers_service.py:950`
- `app/services/closure_report_service.py:227, 242, 260`

## Notas técnicas

- **No requiere mosaiquear imágenes** (sigue seleccionando una sola imagen)
- **No requiere cambios en el pipeline de rendering** (no afecta thumbnails)
- **No requiere `computePixels`** (todo con `reduceRegion` server-side)
- **Cambio quirúrgico** en la lógica de scoring de selección
- **Scale=60m** para balance entre velocidad y precisión en el filtrado
