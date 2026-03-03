## Core UI de Análisis y Mapas — Overview

Este flujo CORE describe cómo la UI consume los datos procesados (eventos, episodios, recurrencia, calidad, assets HD) y los presenta al usuario final.

### Alcance

- Páginas de exploración de incendios y mapas principales.
- Capas de mapa (eventos, episodios, heatmaps H3, áreas protegidas).
- Filtros y herramientas de análisis.
- Integración con exploración HD (descarga de imágenes, PDFs, etc.).

### Código principal

- `frontend/src/pages/Exploration.tsx`
- `frontend/src/components/fire-map.tsx`
- `frontend/src/components/map/MapView.tsx`
- `frontend/src/components/map/layers/EpisodeLayer.tsx`
- `frontend/src/components/map/layers/H3HeatmapLayer.tsx`
- `frontend/src/components/fires/fire-filters.tsx`
- `frontend/src/components/reliability-score.tsx`

### Documentos fuente relevantes

- `docs/frontend/README.md`
- `docs/frontend/routing_access_ruc.md`
- `docs/frontend/home-removal-incendios-urgentes.md`
- `docs/frontend/ui_debt_log.md`
- `docs/architecture/frontend/0_frontend_roadmap.md`

