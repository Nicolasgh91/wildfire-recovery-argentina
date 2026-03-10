## Core Ingesta FIRMS y Agrupamiento Inicial

Este flujo CORE cubre desde la **descarga incremental diaria de FIRMS** hasta la **creación de eventos de incendio** listos para ser usados por el resto de la plataforma.

### Alcance

- Descarga de detecciones térmicas desde NASA FIRMS.
- Normalización y filtrado (confianza, bounding box Argentina).
- Inserción en `fire_detections` evitando duplicados.
- Clustering incremental para generar `fire_events`.
- Cruce legal incremental con áreas protegidas.

### Código principal

- `scripts/maintenance/load_firms_incremental.py` — pipeline incremental FIRMS (script canónico).
- `workers/tasks/ingestion.py` — tarea Celery `download_firms_daily` que orquesta la ingesta real en producción.
- `app/services/detection_clustering_service.py` — clustering espacio‑temporal (ST‑DBSCAN) sobre `fire_detections`.

### Documentos fuente relevantes

- `docs/architecture/data_ingestion_flow.md`
- `docs/UF-12/2_UC_F12_implementation_spec.md`
- `docs/UF-12/uc-f12-data-flow-diagram-776569.md`

Para detalles operativos y troubleshooting, ver `core-ingesta-manual-dev.md` y `core-ingesta-runbook.md` en este mismo directorio.

