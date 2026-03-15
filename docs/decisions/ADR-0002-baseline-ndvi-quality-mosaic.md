# ADR-0002: Baseline NDVI por composite de máximo NDVI (quality mosaic)

Date: 2026-03-15  
Status: Accepted

## Contexto

El cálculo de baseline NDVI pre-incendio se hacía con una sola imagen en una ventana fija de 45–15 días antes del incendio (`get_best_image` + `calculate_ndvi`). Eso podía subrepresentar la capacidad ecológica en zonas con estacionalidad marcada.

## Decisión

Calcular el baseline como **composite de máximo NDVI (quality mosaic)** sobre los 12 meses anteriores al incendio (ventana 365 días), con fallback a 24 meses (730 días) si no hay imágenes suficientes. El quality mosaic selecciona por píxel el NDVI más alto en el período, capturando el pico de vegetación anual como referencia.

Implementación en `app/services/vae_service.py` (`_get_baseline_ndvi`):

- Ventanas: `[lookback_days, lookback_days * 2]` (default 365, 730).
- `get_sentinel_collection` → `collection.map(add_ndvi)` → `qualityMosaic('NDVI')` → `reduceRegion(Reducer.mean(), scale=30)`.
- Clave de estadísticas: `stats.get('NDVI') or stats.get('NDVI_mean')`.
- Si no hay datos válidos en ninguna ventana se lanza `BaselineNotAvailableError`.

## Consecuencias

- Baseline más representativo de la capacidad ecológica en regímenes estacionales.
- Un request GEE por ventana hasta obtener resultado; backfill de muchos eventos sigue acotado por cuota.
- `scale=30` en `reduceRegion` reduce coste de compute en GEE frente a resolución 10 m.
