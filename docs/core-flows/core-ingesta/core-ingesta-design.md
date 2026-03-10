## Core Ingesta FIRMS — Diseño técnico

### 1. Objetivo y principios

- Mantener la ingesta FIRMS:
  - **incremental**, **idempotente** y **reproducible**;
  - con fuerte control de **duplicados** y **calidad de datos**;
  - alineada con el pipeline E2E documentado en `docs/INDEX.md` y `core-pipeline-e2e/core-pipeline-overview.md`.

### 2. Arquitectura de alto nivel

- **Entrada**: API NASA FIRMS (CSV por satélite, últimos _N_ días).
- **Transformación** (según `scripts/maintenance/load_firms_incremental.py`):
  - Normalización de confianza (unificación VIIRS/MODIS a escala 0‑100).
  - Filtrado por bounding box Argentina.
  - Construcción de `detected_at` a partir de `acq_date` + `acq_time`.
  - Cálculo de `detection_hash` (hash fuerte) y `legacy_hash`.
  - Cálculo opcional de `h3_index` si la columna existe en BD.
- **Persistencia**:
  - Inserción en `fire_detections` evitando duplicados.
  - Clustering incremental → `fire_events` (vía `DetectionClusteringService`).
  - Cálculo de área y cruce legal con `protected_areas`.

### 3. Decisiones clave de implementación

- **Estrategia de deduplicación**:
  - No se usa `ON CONFLICT` en BD.
  - El script consulta primero los hashes existentes (`get_existing_hashes`) para las fechas del batch y filtra en memoria las detecciones ya vistas.
  - Esto es funcionalmente equivalente al diseño original, pero **menos atómico** si hubiera dos ejecuciones concurrentes.
- **Hash fuerte vs. legacy hash**:
  - Si la tabla tiene columna `detection_hash`, se usa como clave lógica principal y el hash SHA‑256 se construye con:
    - `satellite`, `instrument`, `detected_at`, `lat`, `lon`, `frp`, **`confidence`**.
  - Si no, se usa un hash `MD5` truncado (`legacy_hash`) sobre `lat|lon|fecha|hora|satélite`.
- **Resolución H3**:
  - Leída primero desde `H3_RESOLUTION` en entorno.
  - Si no está presente, se consulta `system_parameters` (`param_key = 'h3_resolution'`).
  - Si tampoco está disponible, se hace fallback a resolución 8.
- **Reuso de clustering canónico**:
  - En lugar de scripts legacy, la ingesta llama directamente a `DetectionClusteringService.run_clustering(days_back=...)`.
  - El servicio usa parámetros leídos de `system_parameters` y `clustering_versions`.

### 4. Estado de alineación doc ↔ código

Basado en `docs/Carrusel fix/auditoria_ingesta_vs_codigo.md` y revisión del código actual:

- `docs/Carrusel fix/flujo_ingesta_procesamiento.md`:
  - **Estado**: PARCIAL/OK.
  - Alineado con el pipeline funcional (ingesta → clustering → episodios → carrusel), pero describe una topología de workers legacy (workers dedicados por cola) ya consolidada en `worker-fast` y `worker-gee`.
- `docs/Carrusel fix/data_ingestion_process.md`:
  - **Estado**: PARCIAL.
  - El flujo conceptual de ingesta y carrusel sigue siendo válido, pero detalles de contenedores y variables de entorno se han actualizado. Para topología de workers y colas usar `docs/architecture/containers.md`.
- `docs/Carrusel fix/auditoria_ingesta_vs_codigo.md`:
  - **Estado**: HISTÓRICO/DISEÑO.
  - La auditoría sigue siendo útil para entender las decisiones tomadas, pero el source of truth actual es este documento y el código.

Gaps relevantes ya reflejados aquí:

- La deduplicación se hace por consulta previa de hashes, no por constraint UNIQUE.
- El hash incluye `confidence` como campo adicional.
- La topología de workers en Docker fue consolidada; cualquier referencia a `worker-ingestion`, `worker-analysis`, etc. debe leerse como histórica.

### 5. Referencias de diseño previas

- `docs/Carrusel fix/data_ingestion_process.md`
- `docs/Carrusel fix/flujo_ingesta_procesamiento.md`
- `docs/Carrusel fix/auditoria_ingesta_vs_codigo.md`
- `docs/UF-12/2_UC_F12_implementation_spec.md`
- `docs/UF-12/uc-f12-data-flow-diagram-776569.md`

En caso de cambios futuros en esquema o lógica de clustering/ingesta, actualizar primero este documento y luego reflejar los cambios en `core-ingesta-manual-dev.md`.

