## Core Preproceso de Imágenes (thumbnails, watermark, fixes PNG)

Este flujo CORE cubre la generación y corrección de **thumbnails y assets de imágenes** usados en carrusel y vistas de detalle.

### Alcance

- Selección de escenas Sentinel‑2 vía GEE.
- Generación de thumbnails en distintos modos (RGB, SWIR, NBR).
- Aplicación de watermark (logo, fecha, metadatos).
- Detección y corrección de PNG corruptos.
- Regeneración de episodios/slides afectados.

### Código principal

- `app/services/imagery_service.py`
- `app/utils/watermark.py`
- `scripts/fix_corrupted_png.py`
- `scripts/deep_png_fix.py`
- `scripts/regenerate_fixed_episode.py`
- `scripts/regenerate_episode_no_watermark.py`
- `tests/unit/test_thumbnail_pipeline.py`

### Documentos fuente relevantes

- `docs/core-flows/core-preproceso-imagenes/core-preproceso-design.md`
- `docs/core-flows/core-preproceso-imagenes/core-preproceso-manual-dev.md`
- `docs/core-flows/core-preproceso-imagenes/core-preproceso-runbook.md`
- `docs/watermark_debugging_guide.md`

Para operación detallada y troubleshooting, ver `core-preproceso-manual-dev.md` y `core-preproceso-runbook.md`.

