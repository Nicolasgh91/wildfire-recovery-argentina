# Tech debt: thumbnail pipeline tests

> Documento de deuda técnica para la suite de tests de thumbnails. Los hallazgos relevantes ya fueron consolidados en `docs/tasks/backlog.md`; mantener este archivo como detalle histórico mientras se ejecutan las correcciones.

> Reportado: 2026-03-04  
> Suite: `tests/unit/test_thumbnail_pipeline.py`  
> Estado: **12 tests fallidos pre-existentes** (no son regresiones)

---

## 1. TestApplyWatermark (3 fallos)

| Test | Error |
|---|---|
| `test_output_size_and_dimensions_preserved` | Watermark produce resultado < 10 KB (3094 bytes). Log: "suspiciously small, falling back to original" |
| `test_disable_watermark_logo_still_applies_text` | Mismo problema de tamaño |
| `test_metadata_with_none_values_skipped` | Mismo problema de tamaño |

**Causa raíz:** `apply_watermark()` en `app/utils/watermark.py` genera un resultado demasiado pequeño y activa su propio fallback interno. Los tests asumen un rango de 10-500 KB que no se cumple.

**Acción sugerida:** Auditar `apply_watermark()` — verificar si el fallback está enmascarando un bug en la generación del watermark (posible regresión en PIL/Pillow).

---

## 2. TestGetThumbnailUrlSizeParams (3 fallos)

| Test | Error |
|---|---|
| `test_wxh_string_passes_dimensions_string` | `captured.get("dimensions")` retorna `None` (dict vacío) |
| `test_int_passes_dimensions_legacy` | Ídem |
| `test_numeric_string_passes_dimensions_legacy` | Ídem |

**Causa raíz:** `get_thumbnail_url()` en `gee_service.py` fue refactorizado para usar `visualize()` + `clip()` + `getThumbURL()` (Fix 5). Los tests mockean `getThumbURL` via `img.getThumbURL` pero la cadena `visualize().updateMask().clip().getThumbURL()` produce un mock diferente al esperado — `captured` nunca se llena.

**Acción sugerida:** Actualizar los mocks para capturar los params del `getThumbURL` en el último eslabón de la cadena `visualize → updateMask → clip → getThumbURL`.

---

## 3. TestGetThumbnailUrlProjectionNormalization (6 fallos)

| Test | Error |
|---|---|
| `test_reproject_called_with_epsg4326_scale20` | `reproject` nunca se llama |
| `test_reproject_called_for_all_vis_types[RGB/SWIR/NBR/NDVI/FALSE_COLOR]` | Ídem |

**Causa raíz:** Misma refactorización de Fix 5: `get_thumbnail_url()` ya no llama a `reproject()` explícitamente. La normalización de proyección se delega a `visualize()` + `dimensions` en `getThumbURL`. Los tests esperan un flujo obsoleto.

**Acción sugerida:** Eliminar o reescribir estos tests para validar el flujo actual (`visualize → clip → getThumbURL` con `dimensions` como parámetro de escalado).
