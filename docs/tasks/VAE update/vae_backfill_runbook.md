# Runbook operativo: backfill VAE y mantenimiento

Fecha: 2026-03-15
Contexto: ForestGuard — módulo VAE (vegetation_monitoring)

---

## 1. Backfill por año

### Ejecución

```bash
# Backfill de un año específico (régimen A, semestral para históricos)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "A", "target_year": YYYY}' \
  --queue vae

# Backfill régimen B (recientes, mensual, post dic-2025)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 50, "regime": "B"}' \
  --queue vae

# Backfill ambos regímenes (A primero, B con cap restante)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "both"}' \
  --queue vae
```

### Secuencia recomendada por año

```
2015 → completado (54 con datos, 1878 sin cobertura Sentinel-2)
2016 → en ejecución
2017 → pendiente (Sentinel-2B operativo, cobertura completa)
2018 → pendiente
2019 → pendiente
2020 → pendiente
2021 → pendiente
2022 → pendiente
2023 → pendiente
2024 → pendiente
2025 → pendiente (régimen B: mensual para post dic-2025)
```

### Notas

- `batch_size`: cantidad de eventos a procesar por ejecución. Para años con muchos eventos (2020, 2021) usar 100-200.
- `target_year`: filtra eventos por año de inicio del incendio.
- `optimize_frequency: true`: usa frecuencia anual para 2015-2018, semestral para 2019+.
- Cap diario: 5 000 req GEE. Si el batch excede el cap, se detiene y reporta cuántos procesó.
- Cada ejecución solo procesa eventos **cerrados** (`extinct`, `closed`) **sin datos** en `vegetation_monitoring`.

---

## 2. Recompute baselines

Actualiza el baseline NDVI con el método v2 (qualityMosaic, pico anual) para eventos que ya tienen datos pero con baseline viejo.

```bash
# Ejecutar (procesa batch_size eventos por ejecución)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.recompute_baselines \
  --kwargs='{"batch_size": 100}' \
  --queue vae

# Ejecutar múltiples veces hasta que reporte "status: done"
# Cada ejecución procesa eventos sin notes LIKE '%baseline_v2%'
```

---

## 3. Queries de monitoreo

### Estado general de vegetation_monitoring

```sql
SELECT
  COUNT(*) AS total_registros,
  COUNT(DISTINCT fire_event_id) AS eventos_unicos,
  COUNT(*) FILTER (WHERE ndvi_mean IS NOT NULL) AS con_datos,
  COUNT(*) FILTER (WHERE pending_reason IS NOT NULL) AS pendientes,
  COUNT(*) FILTER (WHERE baseline_ndvi IS NULL AND ndvi_mean IS NOT NULL) AS baseline_faltante
FROM vegetation_monitoring;
```

### Distribución de estados de recuperación

```sql
SELECT
  vm.recovery_status,
  COUNT(*) AS registros,
  COUNT(DISTINCT vm.fire_event_id) AS eventos,
  ROUND(AVG(vm.recovery_percentage)::numeric, 1) AS pct_promedio,
  ROUND(AVG(vm.baseline_ndvi)::numeric, 3) AS baseline_prom,
  ROUND(AVG(vm.months_after_fire)::numeric, 1) AS meses_prom
FROM vegetation_monitoring vm
WHERE vm.ndvi_mean IS NOT NULL
GROUP BY vm.recovery_status
ORDER BY pct_promedio DESC;
```

### Progreso de backfill por año

```sql
SELECT
  EXTRACT(YEAR FROM fe.start_date)::int AS año,
  COUNT(DISTINCT fe.id) AS eventos_cerrados,
  COUNT(DISTINCT fe.id) FILTER (
    WHERE fe.id IN (SELECT DISTINCT fire_event_id FROM vegetation_monitoring WHERE ndvi_mean IS NOT NULL)
  ) AS con_datos_vae,
  COUNT(DISTINCT fe.id) FILTER (
    WHERE fe.latest_recovery_status = 'no_satellite_coverage'
  ) AS sin_cobertura,
  COUNT(DISTINCT fe.id) FILTER (
    WHERE fe.id NOT IN (SELECT DISTINCT fire_event_id FROM vegetation_monitoring WHERE ndvi_mean IS NOT NULL)
    AND (fe.latest_recovery_status IS NULL OR fe.latest_recovery_status != 'no_satellite_coverage')
  ) AS pendientes_backfill
FROM fire_events fe
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
GROUP BY 1
ORDER BY 1;
```

### Puntos temporales por evento (verificar completitud de serie)

```sql
SELECT
  points_per_event,
  COUNT(*) AS eventos_con_esa_cantidad
FROM (
  SELECT fire_event_id, COUNT(*) AS points_per_event
  FROM vegetation_monitoring
  WHERE ndvi_mean IS NOT NULL
  GROUP BY fire_event_id
) sub
GROUP BY points_per_event
ORDER BY points_per_event;
```

### Completitud de campos

```sql
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE baseline_ndvi IS NOT NULL) AS con_baseline,
  COUNT(*) FILTER (WHERE ndvi_min IS NOT NULL) AS con_ndvi_detalle,
  COUNT(*) FILTER (WHERE cloud_cover_pct IS NOT NULL) AS con_cloud,
  COUNT(*) FILTER (WHERE vm.recovery_status IS NOT NULL) AS con_status,
  COUNT(*) FILTER (WHERE pending_reason IS NOT NULL) AS pendientes,
  COUNT(*) FILTER (WHERE months_after_fire <= 0) AS meses_invalidos
FROM vegetation_monitoring vm;
```

### Estado del cache en fire_events

```sql
SELECT
  CASE
    WHEN latest_recovery_status IS NOT NULL THEN latest_recovery_status
    ELSE 'sin_cache'
  END AS estado_cache,
  COUNT(*) AS eventos
FROM fire_events
WHERE status IN ('extinct', 'closed')
  AND start_date >= '2015-01-01'
GROUP BY 1
ORDER BY 2 DESC;
```

### Serie temporal de un evento específico

```sql
-- Reemplazar EVENT_ID con el UUID del evento
SELECT
  vm.monitoring_date,
  vm.months_after_fire,
  vm.baseline_ndvi,
  vm.ndvi_mean,
  vm.recovery_percentage,
  vm.recovery_status,
  vm.cloud_cover_pct
FROM vegetation_monitoring vm
WHERE vm.fire_event_id = 'EVENT_ID'
  AND vm.ndvi_mean IS NOT NULL
ORDER BY vm.monitoring_date ASC;
```

### Eventos candidatos para testing de UI (con mejor serie temporal)

```sql
SELECT
  vm.fire_event_id,
  fe.start_date,
  fe.province,
  fe.latest_recovery_status,
  COUNT(*) AS puntos_ndvi,
  ROUND(AVG(vm.baseline_ndvi)::numeric, 3) AS baseline,
  ROUND(MIN(vm.ndvi_mean)::numeric, 3) AS ndvi_min,
  ROUND(MAX(vm.ndvi_mean)::numeric, 3) AS ndvi_max
FROM vegetation_monitoring vm
JOIN fire_events fe ON fe.id = vm.fire_event_id
WHERE vm.ndvi_mean IS NOT NULL
  AND vm.baseline_ndvi IS NOT NULL
GROUP BY vm.fire_event_id, fe.start_date, fe.province, fe.latest_recovery_status
HAVING COUNT(*) >= 10
ORDER BY COUNT(*) DESC
LIMIT 10;
```

---

## 4. Mantenimiento

### Actualizar cache en fire_events

Ejecutar después de cada backfill o recompute para sincronizar el badge de la grilla:

```sql
UPDATE fire_events fe SET
  latest_recovery_status = sub.recovery_status,
  latest_recovery_pct = sub.recovery_percentage
FROM (
  SELECT DISTINCT ON (fire_event_id)
    fire_event_id, recovery_status, recovery_percentage
  FROM vegetation_monitoring
  WHERE recovery_status IS NOT NULL
  ORDER BY fire_event_id, monitoring_date DESC
) sub
WHERE fe.id = sub.fire_event_id
  AND (fe.latest_recovery_status IS DISTINCT FROM sub.recovery_status
    OR fe.latest_recovery_pct IS DISTINCT FROM sub.recovery_percentage);
```

### Limpiar registros pending sin datos

Ejecutar periódicamente para eliminar registros que solo ocupan espacio:

```sql
DELETE FROM vegetation_monitoring
WHERE pending_reason IS NOT NULL
  AND ndvi_mean IS NULL;
```

### Marcar eventos sin cobertura satelital

Para años donde Sentinel-2 no tenía cobertura (eventos pre-2016 sin datos):

```sql
UPDATE fire_events SET
  latest_recovery_status = 'no_satellite_coverage'
WHERE start_date < '2016-01-01'
  AND status IN ('extinct', 'closed')
  AND id NOT IN (
    SELECT DISTINCT fire_event_id FROM vegetation_monitoring WHERE ndvi_mean IS NOT NULL
  )
  AND (latest_recovery_status IS NULL OR latest_recovery_status != 'no_satellite_coverage');
```

### Verificar registros huérfanos

```sql
-- Registros con ndvi_mean pero sin baseline (no deberían existir)
SELECT COUNT(*) FROM vegetation_monitoring
WHERE ndvi_mean IS NOT NULL AND baseline_ndvi IS NULL;
-- Esperado: 0
```

---

## 5. Diagnóstico de problemas

### Worker no procesa tareas

```bash
# Verificar que worker-gee consume cola vae
docker compose exec worker-gee celery -A workers.celery_app inspect active_queues 2>/dev/null | grep vae

# Verificar tareas registradas
docker compose exec worker-gee celery -A workers.celery_app inspect registered 2>/dev/null | grep -i "recovery\|backfill\|recompute"

# Verificar cola en Redis
docker compose exec redis redis-cli LLEN vae

# Ver tareas activas
docker compose exec worker-gee celery -A workers.celery_app inspect active 2>/dev/null
```

### Ejecutar analyze_recovery manualmente (diagnóstico)

```bash
# Reemplazar EVENT_ID y TARGET_DATE
docker compose exec worker-gee python -c "
from workers.tasks.recovery import analyze_recovery
result = analyze_recovery('EVENT_ID', 'TARGET_DATE')
print(result)
"
```

### Error ST_X(geography)

Si aparece `function st_x(geography) does not exist`, verificar que el cast `::geometry` está aplicado en `recovery.py`:

```bash
docker compose exec worker-gee grep -n "::geometry" /app/workers/tasks/recovery.py
# Esperado: múltiples líneas con ST_X(...::geometry), ST_Y, ST_XMin, etc.
```

### Error "Image with no bands" en baseline

Significa que no hay imágenes Sentinel-2 en la ventana de búsqueda. Causas comunes: evento pre-2016 sin cobertura, zona remota, o ventana temporal demasiado estrecha. El worker lo maneja con `BaselineNotAvailableError` y crea registro pending.

### Error "unregistered task"

```bash
# Verificar que el módulo está importado
docker compose exec worker-gee python -c "
from workers.tasks.backfill import backfill_historical_recovery, recompute_baselines
print('OK: ambas tareas importables')
"

### Docker logs en tiempo real
docker compose logs -f worker-gee

# Si falla, restart worker
docker compose restart worker-gee

docker compose exec worker-gee \
  celery -A workers.celery_app result ID-DE-INCENDIO
```

### Worker GEE OOM (exit 137)

Si el contenedor `forestguard-worker-gee` sale con **código 137**, el kernel lo terminó por falta de memoria (OOM kill). El worker tiene por defecto `mem_limit: 256M` en `docker-compose.yml`. Las tareas de backfill (GEE + series temporales) pueden picos de RAM; si 137 es recurrente, valorar subir el límite.

**Comprobar si un backfill estaba en curso**

- Tras el OOM, la tarea que se estaba ejecutando se pierde (no hay retry automático del mismo batch). La cola `vae` puede seguir teniendo mensajes si la tarea se encoló como múltiples chunks.
- Ver si quedan tareas en cola: `docker compose exec redis redis-cli LLEN vae`
- Ver progreso en BD (cuántos eventos del año ya tienen datos): usar la query "Progreso de backfill por año" de la sección 3.

**Reiniciar worker y re-lanzar backfill 2016 (o el año afectado)**

```bash
# 1. Reiniciar el worker
docker compose restart worker-gee

# 2. Esperar a que esté healthy (healthcheck celery inspect ping)
docker compose ps worker-gee

# 3. Re-lanzar backfill del año que estaba en curso (ej. 2016)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "target_year": 2016, "prioritize_protected": true, "optimize_frequency": true}' \
  -Q vae
```

La tarea solo procesa eventos que aún **no** tienen datos en `vegetation_monitoring`, por lo que es idempotente: no duplica trabajo ya hecho.

**Monitorear RAM**

```bash
# Uso de memoria del contenedor en tiempo real
docker stats forestguard-worker-gee --no-stream

# Logs recientes del worker (buscar OOM o errores de memoria)
docker compose logs --tail 200 worker-gee
```

Si 137 se repite con 256M, en `docker-compose.yml` (servicio `worker-gee`) subir `mem_limit` y `deploy.resources.limits.memory` (por ejemplo a 512M) y volver a desplegar.

---

## 6. Resumen de regímenes de backfill

| Régimen | Eventos | Frecuencia puntos | Fecha de corte |
|---|---|---|---|
| A — históricos | Cerrados pre dic-2025 | Semestral | `start_date < 2025-12-01` |
| B — recientes | Cerrados post dic-2025 | Mensual | `start_date >= 2025-12-01` |
| Anual (optimizado) | 2015-2018 con `optimize_frequency` | Anual | Solo con flag explícito |

## 7. Resumen de métodos de baseline

| Paso | Ventana | Método | Cuándo se usa |
|---|---|---|---|
| 1 | 365 días pre-incendio | qualityMosaic (max NDVI anual) | Default |
| 2 | 730 días pre-incendio | qualityMosaic (max NDVI 2 años) | Fallback si paso 1 falla |
| 3 | 180-540 días post-incendio | qualityMosaic (max NDVI post-fire) | Fallback para eventos sin cobertura pre-incendio |
