# VAE Backfill Commands - Ejecución por Año

Comandos para ejecutar el backfill VAE año por año, desde 2025 hacia atrás.

## Verificación de Integración

```bash
# Verificar que la tarea backfill esté registrada
docker compose exec worker-gee celery -A workers.celery_app inspect registered | findstr backfill

# Test con batch pequeño (2025)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 5, "target_year": 2025, "prioritize_protected": true}' -Q vae
```

## Ejecución por Año (2025 → 2015)

### Año 2025 (Episodios más recientes)
```bash
# Fase 1: 2025 - Todos los episodios (prioridad áreas protegidas)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 200, "target_year": 2025, "prioritize_protected": true, "optimize_frequency": false}' -Q vae

# Monitoreo progreso 2025
psql "$DATABASE_URL" -c "
SELECT 
    COUNT(*) as episodios_2025,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) as con_vae,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) as sin_vae
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND EXTRACT(YEAR FROM fe.start_date) = 2025;
"
```

### Año 2024
```bash
# Fase 2: 2024 - Todos los episodios
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 300, "target_year": 2024, "prioritize_protected": true, "optimize_frequency": false}' -Q vae
```

### Año 2023
```bash
# Fase 3: 2023 - Todos los episodios
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 300, "target_year": 2023, "prioritize_protected": true, "optimize_frequency": false}' -Q vae
```

### Año 2022
```bash
# Fase 4: 2022 - Todos los episodios
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 400, "target_year": 2022, "prioritize_protected": true, "optimize_frequency": false}' -Q vae
```

### Año 2021
```bash
# Fase 5: 2021 - Todos los episodios
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 300, "target_year": 2021, "prioritize_protected": true, "optimize_frequency": false}' -Q vae
```

### Año 2020
```bash
# Fase 6: 2020 - Año con más incendios, batch más grande
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "target_year": 2020, "prioritize_protected": true, "optimize_frequency": false}' -Q vae
```

### Años 2019-2018 (Transición a optimización de frecuencia)
```bash
# Año 2019 - Último año con frecuencia semestral completa
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 400, "target_year": 2019, "prioritize_protected": true, "optimize_frequency": false}' -Q vae

# Año 2018 - Primer año con optimización (anual para episodios antiguos)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 400, "target_year": 2018, "prioritize_protected": true, "optimize_frequency": true}' -Q vae
```

### Años 2017-2015 (Frecuencia anual optimizada)
```bash
# Año 2017 - Frecuencia anual
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "target_year": 2017, "prioritize_protected": true, "optimize_frequency": true}' -Q vae

# Año 2016 - Frecuencia anual
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "target_year": 2016, "prioritize_protected": true, "optimize_frequency": true}' -Q vae

# Año 2015 - Frecuencia anual (año más antiguo)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "target_year": 2015, "prioritize_protected": true, "optimize_frequency": true}' -Q vae
```

## Monitoreo General

```sql
-- Progreso general por año
SELECT 
    EXTRACT(YEAR FROM fe.start_date) as año,
    COUNT(*) as episodios_totales,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) as con_vae,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) as sin_vae,
    ROUND(
        (COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) * 100.0 / COUNT(*)), 2
    ) as pct_completado
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
GROUP BY EXTRACT(YEAR FROM fe.start_date)
ORDER BY año DESC;

-- Estimación de requests restantes por año
WITH yearly_estimates AS (
    SELECT 
        EXTRACT(YEAR FROM fe.start_date) as año,
        COUNT(DISTINCT fe.id) as episodios_sin_vae,
        CASE 
            WHEN EXTRACT(YEAR FROM fe.start_date) <= 2018 THEN
                -- Anual: ~9 puntos por episodio en promedio
                COUNT(DISTINCT fe.id) * 9 * 2
            ELSE
                -- Semestral: ~11 puntos por episodio en promedio  
                COUNT(DISTINCT fe.id) * 11 * 2
        END as estimated_requests
    FROM fire_events fe
    WHERE fe.status IN ('extinct', 'closed')
      AND fe.start_date >= '2015-01-01'
      AND NOT EXISTS (
          SELECT 1 FROM vegetation_monitoring vm 
          WHERE vm.fire_event_id = fe.id
      )
    GROUP BY EXTRACT(YEAR FROM fe.start_date)
)
SELECT 
    año,
    episodios_sin_vae,
    estimated_requests,
    ROUND(estimated_requests / 50000.0, 2) as dias_a_50k_req
FROM yearly_estimates
ORDER BY año DESC;
```

## Monitoreo de EECU y Queue

```bash
# Monitorear consumo EECU durante ejecución
docker compose exec worker-gee python -c "
from app.services.gee_service import GEEService
gee = GEEService()
usage = gee.get_current_month_usage()
print(f'EECU usage: {usage}/150 hours ({usage/150*100:.1f}%)')
"

# Verificar queue de Celery
docker compose exec worker-gee celery -A workers.celery_app inspect active -Q vae
docker compose exec worker-gee celery -A workers.celery_app inspect stats -Q vae
```

## Estrategia de Ejecución

1. **Iniciar con 2025**: Testear con el año más reciente
2. **Monitorear consumo**: Verificar EECU y GEE requests
3. **Ajustar batch sizes**: Según rendimiento observado
4. **Continuar descendente**: 2024 → 2023 → ... → 2015
5. **Pausas automáticas**: Si se acerca a límites de quota

## Parámetros Clave

- `batch_size`: Cantidad de episodios por ejecución (200-500 según año)
- `target_year`: Año específico a procesar
- `prioritize_protected`: true para priorizar áreas protegidas
- `optimize_frequency`: true para frecuencia anual en 2015-2018
