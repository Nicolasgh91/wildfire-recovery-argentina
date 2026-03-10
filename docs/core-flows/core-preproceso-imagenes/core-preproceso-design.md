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

- `docs/watermark_debugging_guide.md`
- `docs/core-flows/core-preproceso-imagenes/core-preproceso-overview.md`

