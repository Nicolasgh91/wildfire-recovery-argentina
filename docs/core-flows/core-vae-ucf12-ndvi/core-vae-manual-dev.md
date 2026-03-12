## Core VAE / UC‑F12 / NDVI — Manual para devs/ops

Este manual describe cómo ejecutar y supervisar los análisis de vegetación (UC‑F12/UC‑06) y cambios de uso de suelo (UC‑08).

### 1. Componentes principales

- **Servicios**:
  - `app/services/vae_service.py` (`VAEService`).
  - `app/services/gee_service.py` (acceso GEE).
- **Workers**:
  - `workers/tasks/recovery.py`:
    - `analyze_recovery(fire_event_id)`.
    - `batch_recovery_monthly()`.
  - `workers/tasks/destruction.py`:
    - `detect_destruction(fire_event_id, months_window=12)`.
- **Tablas**:
  - `vegetation_monitoring` (recuperación NDVI).
  - `land_use_changes` (cambios de uso de suelo).

### 2. Requisitos previos

- Variables de entorno GEE configuradas (`GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_PRIVATE_KEY_PATH` o JSON).
- Worker `worker-gee` corriendo y escuchando al menos las colas:
  - `"gee"` (recovery batch).
  - `"vae"` (destruction, según configuración actual).
- Migración `2026_02_23_uc_f12_vae_monitoring.sql` aplicada (constraints + RLS).

### 3. Ejecución manual para un solo evento (testing)

Basado en `docs/archive/ndvi-uf12/uc-f12-testing-and-manual-workers.md`:

1. Obtener un `fire_event_id` válido:

```bash
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
events = db.execute(text(\"\"\"
    SELECT id, province, start_date
    FROM fire_events
    WHERE centroid IS NOT NULL
      AND start_date > NOW() - INTERVAL '12 months'
    ORDER BY start_date DESC
    LIMIT 5
\"\"\")).fetchall()
for e in events:
    print(f'ID: {e[0]} | Provincia: {e[1]} | Fecha: {e[2]}')
db.close()
"
```

2. Ejecutar análisis de recuperación para ese evento:

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.recovery.analyze_recovery \
  --args='["<FIRE_EVENT_ID>"]'
```

3. (Opcional) Ejecutar detección de destrucción:

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.destruction.detect_destruction \
  --args='["<FIRE_EVENT_ID>"]'
```

4. Verificar resultados en BD:

```sql
SELECT * 
FROM vegetation_monitoring
WHERE fire_event_id = '<FIRE_EVENT_ID>'
ORDER BY monitoring_date DESC;

SELECT * 
FROM land_use_changes
WHERE fire_event_id = '<FIRE_EVENT_ID>'
ORDER BY change_detected_at DESC;
```

### 4. Ejecución batch (monitoreo mensual)

Cuando esté configurado el schedule en Celery Beat, `batch_recovery_monthly` correrá solo. Para ejecución manual:

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.recovery.batch_recovery_monthly
```

Esto:

- Selecciona un subconjunto de eventos activos/en monitoreo.
- Encola `analyze_recovery` para cada uno en la cola `"gee"` respetando límites de cuota.

### 5. Endpoints relacionados

- `GET /api/v1/monitoring/recovery/{fire_event_id}`:
  - Devuelve la serie de `vegetation_monitoring` para el evento.
  - No llama GEE (solo lee BD).
  - Requiere autenticación.
- `GET /api/v1/monitoring/land-use-changes/{fire_event_id}`:
  - Devuelve filas de `land_use_changes` e indicador de violaciones.
  - Requiere autenticación.
- `POST /api/v1/monitoring/recovery/trigger`:
  - Dispara jobs de VAE para un conjunto de eventos.
  - Solo admin.

### 6. Checks de salud básicos

- Conteos básicos:

```sql
SELECT COUNT(*) FROM vegetation_monitoring;
SELECT COUNT(*) FROM land_use_changes;
```

- Últimos análisis por evento:

```sql
SELECT fire_event_id, MAX(monitoring_date) AS last_date
FROM vegetation_monitoring
GROUP BY fire_event_id
ORDER BY last_date DESC
LIMIT 20;
```

Si los workers corren pero no hay filas nuevas, revisar el runbook (`core-vae-runbook.md`) para diagnóstico de GEE/cuotas.
