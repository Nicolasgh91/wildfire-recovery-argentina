## Core Ingesta FIRMS — Runbook de troubleshooting

Guía rápida para diagnosticar y resolver problemas en el flujo de ingesta FIRMS.

### 1. La tarea Celery falla al iniciar

**Síntomas**:

- Logs de `download_firms_daily` con error inmediato.
- Mensajes de error relacionados a imports o variables de entorno.

**Checks**:

1. Verificar que los workers tienen acceso al código del repo:
   - Rutas válidas para `scripts/maintenance/load_firms_incremental.py`.
2. Confirmar variables de entorno mínimas:
   - `FIRMS_API_KEY` presente.
   - Credenciales de BD (`DB_HOST`/`DB_PASSWORD` o `DATABASE_URL`).

### 2. Error: `FIRMS_API_KEY no configurada`

**Síntoma**: excepción levantada en `run_incremental_pipeline`.

**Acción**:

- Revisar configuración de entorno en:
  - `.env` local.
  - Config de entorno en servidor (systemd, Docker, etc.).

### 3. No se insertan detecciones nuevas

**Síntomas**:

- Logs indican `Detecciones insertadas: 0`.
- Demasiados `duplicates` o `total_filtered` pequeño.

**Checks**:

1. Confirmar que FIRMS efectivamente devuelve datos:
   - Revisar logs de `download_firms_daily` para cada satélite.
2. Revisar filtros:
   - Bounding box Argentina (`ARG_BOUNDS`).
   - Umbral de confianza (≥ 50).
3. Comprobar rango de días:
   - Ejecutar con `--days 3` o mayor si corresponde.

### 4. Clustering o área fallan después de ingresar datos

**Síntomas**:

- Errores en `run_clustering_for_dates`, `run_area_calculation` o `run_legal_crossing`.

**Acción**:

1. Revisar logs de la ejecución manual:

```bash
python scripts/maintenance/load_firms_incremental.py --days 2
```

2. Si el fallo es puntual:
   - Revisar migraciones recientes que hayan cambiado `fire_events` o índices espaciales.

### 5. Verificación de consistencia mínima

- Consultar si hay detecciones recientes sin evento asociado:

```sql
SELECT COUNT(*) 
FROM fire_detections d
LEFT JOIN fire_events e ON d.fire_event_id = e.id
WHERE d.acquisition_date >= CURRENT_DATE - INTERVAL '3 days'
  AND e.id IS NULL;
```

- Si el número es alto, revisar:
  - Logs de clustering.
  - Cambios recientes en `DetectionClusteringService`.

### 6. Prevención

- Mantener `h3` instalado cuando la columna `h3_index` existe.
- Revisar periódicamente el log `logs/firms_incremental.log` en el servidor para anticipar problemas de cuotas o cambios en el esquema FIRMS.

