# indice de documentacion

Ultima actualizacion: 22 de febrero de 2026.

Este indice separa documentacion vigente (canonica) de documentacion historica (archivo).

## documentacion canonica actual

### producto

- `docs/product/README.md` - hub canonico de producto
- `docs/product/casos-de-uso-y-estado.md` - fuente unica de casos de uso y estado
- `docs/product/estado-real-del-producto.md` - semaforo de estado y top 5 de cierre
- `docs/product/diferenciacion-mercado.md` - relevamiento externo con citas
- `docs/product/matriz-inconsistencias-2026-02-22.md` - diagnostico de consistencia

### flujos CORE (datos → UI)

- `docs/core-flows/README.md` - mapa de documentos por flujo CORE
- `docs/core-flows/core-ingesta/core-ingesta-overview.md` - ingesta FIRMS → fire_detections/fire_events
- `docs/core-flows/core-preproceso-imagenes/core-preproceso-overview.md` - thumbnails, watermark y fixes PNG
- `docs/core-flows/core-vae-ucf12-ndvi/core-vae-overview.md` - VAE / UC‑F12 / NDVI
- `docs/core-flows/core-inferencia-y-hd/core-inferencia-overview.md` - recurrencia, calidad, exploracion HD
- `docs/core-flows/core-ui-analisis/core-ui-overview.md` - UI de analisis, mapas y capas
- `docs/core-flows/core-pipeline-e2e/core-pipeline-overview.md` - pipeline end‑to‑end de datos

### experiencia frontend

- `docs/frontend/README.md` - rutas, estado por pantalla y caveats
- `docs/frontend/routing_access_ruc.md` - matriz de acceso por ruta

### contratos API y auth

- `docs/backend/api/auth_matrix.md` - matriz de autenticacion por endpoint

### infraestructura y operacion

- `docs/infrastructure/deployment/DEPLOYMENT.md` - guia de despliegue
- `docs/flujo-deploy.md` - flujo resumido de deploy y troubleshooting operativo

### referencia de marca

- `docs/brand.md` - configuracion de branding (Vestigia)

## documentacion historica (archivo)

- `docs/archive/` - roadmaps, planes tecnicos y reportes historicos migrados

Regla:

- si una ruta vieja fue migrada, el archivo original queda como puente con link al archivo y al canónico.

## reglas de lectura rapida

1. si queres entender el producto hoy: empezar por `README.md` y `docs/product/estado-real-del-producto.md`.
4. si queres validar estado real contra codigo: usar `docs/product/casos-de-uso-y-estado.md` + `docs/backend/api/auth_matrix.md`.
5. si queres contexto historico: ir a `docs/archive/`.

## Flujo de Datos y Agrupamiento (Pipeline Core)

A continuación, se detalla el ciclo de vida real de los datos desde la ignición térmica hasta la visualización en el frontend.

```mermaid
flowchart TD
    %% Estilos
    classDef external fill:#f9d0c4,stroke:#333,stroke-width:2px;
    classDef worker fill:#d4e6f1,stroke:#333,stroke-width:2px;
    classDef service fill:#d5f5e3,stroke:#333,stroke-width:2px;
    classDef db fill:#fcf3cf,stroke:#333,stroke-width:2px;
    classDef legacy fill:#fadbd8,stroke:#e74c3c,stroke-width:2px,stroke-dasharray: 5 5;

    %% Nodos
    NASA[NASA FIRMS API]:::external
    IngestionWorker["Ingestion Worker\n(workers/tasks/ingestion.py)"]:::worker
    FireService["FireService\n(Guarda detecciones térmicas)"]:::service
    FireDetections[("Tabla:\nfire_detections")]:::db

    ClusteringWorker["Clustering Task\n(workers/tasks/clustering_task.py)"]:::worker
    DetectionClustService["DetectionClusteringService\n(Espacial-Temporal DBSCAN)"]:::service
    FireEvents[("Tabla:\nfire_events\n(micro-incendios)")]:::db

    MergeWorker["Merge Task\n(workers/tasks/episode_merge_task.py)"]:::worker
    ClusteringService["ClusteringService\n(Agrupación de macro-episodios)"]:::service
    EpisodeService["EpisodeService\n(Métricas y Ventana Temporal)"]:::service
    FireEpisodes[("Tabla:\nfire_episodes\n(macro-episodios)")]:::db

    CarouselWorker["Carousel Worker\n(workers/tasks/carousel_task.py)"]:::worker
    ImageryService["ImageryService\n(Filtra Top 20 Candidates)"]:::service
    GEEService["GEEService\n(Google Earth Engine API)"]:::external
    Storage["Cloud Storage\n(R2/S3)"]:::db

    Frontend[Frontend Carousel]:::external

    %% Flujo 1: Ingesta
    NASA -- "FIRMS CSV" --> IngestionWorker
    IngestionWorker -- "Valida y clasifica" --> FireService
    FireService -- "Insert/Upsert" --> FireDetections

    %% Flujo 2: Clustering (Detections -> Events)
    FireDetections -- "Cron Batch" --> ClusteringWorker
    ClusteringWorker -- "Orquesta" --> DetectionClustService
    DetectionClustService -- "Asigna Detecciones (Cluster ID)" --> FireEvents

    %% Flujo 3: Episodios (Events -> Episodes)
    FireEvents -- "Nuevos Eventos" --> MergeWorker
    MergeWorker -- "Orquesta" --> ClusteringService
    ClusteringService -- "DBSCAN de proximidad" --> EpisodeService
    EpisodeService -- "Asignación Pivot" --> FireEpisodes
    EpisodeService -. "Recálculo (Area, FRP)" .-> FireEpisodes

    %% Flujo 4: Carousel Imagery
    FireEpisodes -- "Cron Diario" --> CarouselWorker
    CarouselWorker -- "Orquesta" --> ImageryService
    ImageryService -- "Consulta activos/candidates" --> GEEService
    GEEService -- "Renderiza Thumbnails" --> Storage
    Storage -- "URLs servidas" --> Frontend

    %% Subgraph Legacy Notes
    subgraph "Scripts Históricos (Reemplazados / Peligrosos)"
        direction TB
        L1[scripts/legacy/legacy_aggregate_fire_episodes.py]:::legacy
        L2[scripts/legacy/legacy_cluster_fire_events_parallel.py]:::legacy
        L3[scripts/legacy/legacy_consolidate_events.py]:::legacy
        L1 -. "Hacía TRUNCATE de Links" .-> FireEpisodes
        L2 -. "Reemplazado por clustering_task" .-> FireEvents
    end
```
