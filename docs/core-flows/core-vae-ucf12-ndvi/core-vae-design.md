## Core VAE / UC‑F12 / NDVI — Diseño técnico

### 1. Objetivo

Proveer un **motor de análisis de vegetación** (VAE) que:

- Calcule y persista la recuperación post‑incendio (UC‑06/UC‑F12) en `vegetation_monitoring`.
- Detecte cambios de uso de suelo y posibles violaciones legales en `land_use_changes`.
- Exponga resultados vía endpoints de `monitoring` sin llamar a GEE en tiempo real (workers como únicos consumidores de GEE).

### 2. Arquitectura lógica

- **Capa GEE**:
  - `app/services/gee_service.py` obtiene colecciones Sentinel‑2, compone imágenes con filtros de nubes y devuelve valores NDVI agregados.
- **Motor VAE**:
  - `app/services/vae_service.py`:
    - `analyze_recovery(...)` construye `RecoveryAnalysis` a partir de baseline + NDVI actual.
    - `detect_land_use_change(...)` construye `LandUseAnalysis` (tipo de cambio, severidad, violación potencial).
- **Workers**:
  - `workers/tasks/recovery.py`:
    - `analyze_recovery(fire_event_id)`:
      - Obtiene `fire_events` (centroide, fecha).
      - Reutiliza baseline desde `vegetation_monitoring` si existe; si no, lo calcula con VAE (1 req GEE).
      - Consulta NDVI del mes actual con nubes (`_get_current_ndvi_with_cloud`) (1 req GEE).
      - Calcula `recovery_percentage` y `recovery_status` (_classify_recovery).
      - UPSERT en `vegetation_monitoring` con `ON CONFLICT (fire_event_id, monitoring_date)`.
    - `batch_recovery_monthly()` encola `analyze_recovery` para eventos activos/en monitoreo con límites seguros de cuota GEE.
  - `workers/tasks/destruction.py`:
    - `detect_destruction(fire_event_id, months_window=12)`:
      - Obtiene geometría y área estimada del evento.
      - Llama `VAEService.detect_land_use_change(...)`.
      - UPSERT en `land_use_changes` (`UNIQUE (fire_event_id, change_detected_at)`).
- **Schema y RLS**:
  - `database/migrations/2026_02_23_uc_f12_vae_monitoring.sql`:
    - Añade constraints de idempotencia:
      - `UNIQUE (fire_event_id, monitoring_date)` en `vegetation_monitoring`.
      - `UNIQUE (fire_event_id, change_detected_at)` en `land_use_changes`.
    - Añade FK `land_use_changes.monitoring_record_id → vegetation_monitoring(id)`.
    - Habilita RLS y políticas:
      - `SELECT` para `authenticated`.
      - `ALL` para `service_role` (workers).
- **API**:
  - `app/api/routes/monitoring.py`:
    - `GET /monitoring/recovery/{fire_event_id}`:
      - Solo lee `vegetation_monitoring` (0 llamadas GEE).
      - Si no hay filas, retorna `pending` y puede encolar un análisis.
    - `GET /monitoring/land-use-changes/{fire_event_id}`:
      - Lee `land_use_changes` y devuelve listado + `violation_count`.
    - `POST /monitoring/recovery/trigger`:
      - Admin‑only, dispara workers para un set de eventos.

### 3. Estrategia de cuotas GEE

Basada en `docs/archive/ndvi-uf12/uc-f12-gee-optimization-analysis.md` y `docs/ndvi/gee_quota_mitigation_spec_on_ndvi.md`:

- Un evento típico requiere:
  - Baseline NDVI (`_get_baseline_ndvi`) → 1 request.
  - NDVI actual mensual (`_get_current_ndvi_with_cloud`) → 1 request.
  - Detección de uso de suelo → 1–2 requests adicionales.
- Con workers y batching:
  - **Backfill histórico** se ejecuta en episodios/eventos representativos para reducir de ~180k a ~10k requests (≈17× menos).
  - **Monitoreo estable**:
    - 10–20 episodios en carrusel actualizados semanalmente consumen < 0.2% de la cuota diaria.
- Principio:
  - **Endpoints HTTP nunca llaman GEE**; toda la cuota se gasta en workers controlados y medidos.

### 4. Alineación docs ↔ código

- `docs/archive/ndvi-uf12/uc-f12-as-is-analysis-2026-02-24.md`:
  - **Estado**: HISTÓRICO.
  - Describe el estado previo al refactor de cuotas GEE y visibilidad progresiva.
- `docs/archive/ndvi-uf12/uc-f12-implementation-spec.md` y `docs/archive/ndvi-uf12/uc-f12-gee-optimization-analysis.md`:
  - **Estado**: DISEÑO/OK (con matices).
  - Siguen siendo fuente para decisiones de arquitectura de workers y cuotas, pero varias partes se han refinado (por ejemplo, decisión de mantener endpoints `monitoring` privados).
- `docs/ndvi/analisis_ndvi.md` y `hoja_de_ruta_ndvi_gee_v2.md`:
  - **Estado**: DISEÑO/ROADMAP.
  - Definen roadmap de UI y comportamiento de `NdviChart`; el código actual respeta la separación “snapshot público vs timeline autenticado”.

En caso de cambios futuros (por ejemplo, agregar endpoints agregados por episodio o modificar la fórmula de `recovery_percentage`), actualizar este archivo y luego reflejarlo en `core-vae-manual-dev.md` y la documentación de NDVI correspondiente.

