## Core UI de Análisis y Mapas — Diseño técnico

### 1. Rutas y pantallas clave

Según `docs/frontend/README.md` y el código actual:

- `/home`: resumen inicial con grid de episodios activos.
- `/map`: mapa principal de episodios e indicadores.
- `/exploracion`: flujo guiado de investigación HD (selección de eventos, fechas pre/post, generación de assets).
- `/fires/:id`: detalle de incendio (vista por evento o episodio).
- `/fires/history`: histórico y dashboard de incendios.

La matriz de acceso por ruta está definida en `docs/frontend/routing_access_ruc.md` y se mantiene alineada con el enrutador.

### 2. Mapa y capas de análisis

Componentes principales:

- `FireMap` (`frontend/src/components/fire-map.tsx`):
  - Wrapper que pasa `fires` y contexto al mapa.
- `MapView` (`frontend/src/components/map/MapView.tsx`):
  - Composición de capas:
    - `FireMarkers`: marcadores de incendios individuales (no detallado aquí).
    - `EpisodeLayer`: polígonos H3 por episodio, con popup y link a `/fires/{event_or_episode_id}`.
    - `H3HeatmapLayer`: heatmap de recurrencia a partir de celdas H3 (`intensity 0–1`).
    - `ProtectedAreas`: overlay de áreas protegidas.
- `EpisodeLayer`:
  - Convierte `episodes` (incluyendo severidad, hectáreas, provincia, flags de área protegida) en `FeatureCollection`.
  - Renderiza polígonos H3 con estilo según `MapSeverity`/`MapStatus` y popups ricos que enlazan a detalle.
- `H3HeatmapLayer`:
  - Usa `leaflet.glify` para renderizar heatmap GPU‑based en función de `intensity` e `getHeatmapColor`.

### 3. Filtros y listados de incendios

- `FireFilters` (`frontend/src/components/fires/fire-filters.tsx`):
  - Filtros por:
    - provincia,
    - estado (`active`/`historical`/`all`),
    - rango de fechas,
    - texto libre,
    - orden (fecha, área, FRP).
  - Incluye botón de export a CSV y sección de filtros avanzados (rango de fechas).
- Los filtros se aplican sobre endpoints:
  - `GET /api/v1/fires`,
  - `GET /api/v1/fires/stats`,
  - `GET /api/v1/fires/export`.

### 4. Exploración HD y flujos guiados

- Página `Exploration.tsx`:
  - Orquesta un flujo multi‑paso para:
    - buscar eventos (`searchFireEvents` + `groupEventsByEpisode`),
    - previsualizar timeline de fechas pre/post,
    - crear una exploración (`createExploration`),
    - cotizar y generar assets HD (`getExplorationQuote`, `generateExploration`),
    - listar y descargar assets (`getExplorationAssets`).
  - Usa lazily `FireMap` para ubicar eventos/episodios en el mapa como parte del flujo.

### 5. Indicadores de calidad y confiabilidad

- `ReliabilityScore` (`frontend/src/components/reliability-score.tsx`):
  - Muestra un score 0–100 como barra de progreso y número grande.
  - Colores:
    - ≥ 80: primario,
    - 60–79: accent,
    - < 60: destructive.
  - Texto base en inglés pero integrado con `useI18n` para el título.

### 6. Estado de la documentación UI

- `docs/frontend/README.md`:
  - **Estado**: OK/canónico.
  - Lista rutas y contratos usados por frontend; alineado con el código actual.
- `docs/frontend/routing_access_ruc.md`:
  - **Estado**: OK.
  - Matriz de acceso por ruta consistente con descripción de rutas y flags.
- `docs/frontend/home-removal-incendios-urgentes.md`:
  - **Estado**: HISTÓRICO local.
  - Documenta la eliminación de una sección específica de la home; se mantiene como registro de cambio.

Este documento actúa como pivot técnico entre esos archivos y los componentes reales de mapa, filtros, exploración y detalle.

