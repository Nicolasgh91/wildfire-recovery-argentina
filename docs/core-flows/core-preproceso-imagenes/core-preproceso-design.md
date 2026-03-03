## Core Preproceso de Imágenes — Diseño técnico

Documentará las decisiones clave de:

- Selección de escenas en `ImageryService` (priorización por nubes, fechas, calidad).
- Modos de visualización (RGB, SWIR, NBR) y sus parámetros (bandas, rangos, gamma, paletas).
- Estrategia de watermark:
  - Logo por defecto (`DEFAULT_WATERMARK_LOGO_PATH`).
  - Texto de fecha y metadatos.
  - Política de tamaños y posiciones.
- Estrategia de fixes de PNG:
  - Reparaciones “shallow” vs “deep”.
  - Scripts de regeneración de episodios.

Se apoyará en:

- `docs/Carrusel fix/revision_arquitectural_flujo_thumbnails.md`
- `docs/1_home/thumbnails/PNG_CORRUPTION_FIX_SUMMARY.md`
- `docs/1_home/thumbnails/WATERMARK_IMPLEMENTATION_SUMMARY.md`

