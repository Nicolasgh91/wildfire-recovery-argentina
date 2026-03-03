## Core Inferencia, Recurrencia y Exploración HD — Overview

Este flujo CORE cubre la **generación de indicadores y assets analíticos** a partir de los datos ya ingestados y agrupados.

### Alcance

- Cálculo de:
  - calidad de eventos (reliability score),
  - recurrencia H3 (heatmaps),
  - estadísticas agregadas de incendios.
- Gestión de investigaciones y exploraciones HD (selección de escenas Sentinel‑2 HD, generación de imágenes, almacenamiento).

### Código principal

- `app/services/quality_service.py`
- `app/services/recurrence_service.py`
- `app/services/exploration_service.py`
- `app/workers/exploration_hd_worker.py`
- `app/services/detection_clustering_service.py`

### Documentos fuente relevantes

- `docs/endpoints/fires-stats-workflow.md`
- `docs/assets-generation/tareas-tecnicas-assets-pipeline.md`
- `docs/assets-generation/503_implementation_plan.md`
- `docs/assets-generation/status_2026-02-22.md`

