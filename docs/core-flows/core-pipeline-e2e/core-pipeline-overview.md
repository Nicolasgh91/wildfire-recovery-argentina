## Core Pipeline End‑to‑End — Overview

Este flujo CORE resume el recorrido de los datos desde las **detecciones FIRMS crudas** hasta la **visualización en la UI**, incluyendo episodios, assets y análisis de vegetación.

### Alcance

- Ingesta FIRMS → `fire_detections`.
- Clustering → `fire_events`.
- Construcción de episodios → `fire_episodes`.
- Generación de thumbnails y assets HD.
- Análisis de vegetación (VAE / NDVI / UC‑F12).
- Exposición vía API y consumo por la UI.

### Código principal

- `scripts/maintenance/load_firms_incremental.py`
- `scripts/run_pipeline_manual.py`
- `workers/celery_app.py`
- Servicios y workers listados en los otros flujos CORE.

### Documentos fuente relevantes

- `docs/INDEX.md` (diagrama mermaid del pipeline core).
- `docs/Carrusel fix/flujo_ingesta_procesamiento.md`
- `docs/archive/ndvi-uf12/diagrams/uc-f12-data-flow-diagram-776569.md`
- `docs/archive/assets/assets-pipeline-technical-tasks.md`
- `docs/project/episodes/plan_episode_flow.md`
- `docs/flujo-deploy.md`
- `docs/infrastructure/deployment/DEPLOYMENT.md`

Un diagrama más detallado puede derivar del mermaid existente en `docs/INDEX.md`, alineado con los componentes reales del código.

