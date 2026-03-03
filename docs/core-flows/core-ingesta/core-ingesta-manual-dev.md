## Core Ingesta FIRMS — Manual para devs/ops

Este manual describe **cómo ejecutar y operar** el pipeline de ingesta FIRMS.

### 1. Resumen del flujo

- **Objetivo**: mantener `fire_detections` y `fire_events` actualizados diariamente con datos FIRMS de Argentina.
- **Pipeline lógico**:
  1. Descarga FIRMS (últimos _N_ días).
  2. Filtrado por bounding box + confianza ≥ 50.
  3. Inserción deduplicada en `fire_detections`.
  4. Clustering incremental → `fire_events`.
  5. Cálculo de área y cruce legal con áreas protegidas.

### 2. Componentes técnicos

- Script canónico:
  - `scripts/maintenance/load_firms_incremental.py`
    - Función principal: `run_incremental_pipeline(days: int = 2, dry_run: bool = False)`.
- Worker Celery:
  - `workers/tasks/ingestion.py`
    - Tarea: `download_firms_daily(days=2, dry_run=False)`.

### 3. Ejecución en local

Requisitos mínimos:

- Variables de entorno:
  - `FIRMS_API_KEY` (API key de NASA FIRMS).
  - Credenciales de BD (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` o `DATABASE_URL`).
- Dependencias Python instaladas (incluyendo `h3` si la tabla `fire_detections` tiene `h3_index`).

Comandos típicos:

- Ejecución básica (últimos 2 días):

```bash
python scripts/maintenance/load_firms_incremental.py
```

- Cambiar ventana de días:

```bash
python scripts/maintenance/load_firms_incremental.py --days 3
```

- Simulación sin escribir en BD:

```bash
python scripts/maintenance/load_firms_incremental.py --days 2 --dry-run
```

### 4. Ejecución en workers (entornos remotos)

- Tarea Celery configurada:
  - Nombre: `workers.tasks.ingestion.download_firms_daily`
  - Cola: `ingestion`
  - Parámetros:
    - `days` (por defecto `2`).
    - `dry_run` (por defecto `False`).

Flujo típico:

1. Celery Beat dispara `download_firms_daily`.
2. La tarea llama internamente a `run_incremental_pipeline(...)`.
3. El resultado retorna un `dict` con métricas:
   - `records_inserted`, `duplicates_found`, `total_filtered`,
   - `events_created`, `areas_calculated`, `intersections`.

### 5. Checks de salud básicos

Tras una ejecución exitosa:

- Consultar conteo aproximado de nuevas detecciones:

```sql
SELECT COUNT(*) 
FROM fire_detections 
WHERE acquisition_date >= CURRENT_DATE - INTERVAL '3 days';
```

- Verificar nuevos eventos:

```sql
SELECT COUNT(*) 
FROM fire_events 
WHERE start_date >= CURRENT_DATE - INTERVAL '7 days';
```

- Verificar que los eventos tengan área estimada:

```sql
SELECT COUNT(*) 
FROM fire_events 
WHERE start_date >= CURRENT_DATE - INTERVAL '7 days'
  AND estimated_area_hectares IS NULL;
```

### 6. Relación con otros flujos CORE

- El output de este flujo (`fire_events`) alimenta:
  - **Episodios y carrusel** (pipeline de episodios y thumbnails).
  - **Análisis VAE / UC‑F12** (tablas de monitoreo de vegetación).
  - **Recurrencia y stats** (heatmaps H3 y endpoints de estadísticas).

Para investigar problemas en pasos posteriores, ver:

- `core-pipeline-e2e/core-pipeline-overview.md`
- `core-preproceso-imagenes/core-preproceso-overview.md`

