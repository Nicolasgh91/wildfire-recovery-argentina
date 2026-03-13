-- 1. Conteo total de episodios cerrados por año (desde 2015)

Consulta: 

SELECT 
    EXTRACT(YEAR FROM fe.start_date) AS año,
    COUNT(*) AS episodios_cerrados,
    MIN(fe.start_date) AS primer_episodio,
    MAX(fe.start_date) AS ultimo_episodio
FROM fire_events fe
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
GROUP BY EXTRACT(YEAR FROM fe.start_date)
ORDER BY año;

Resultado: 

[
  {
    "año": "2015",
    "episodios_cerrados": 1932,
    "primer_episodio": "2015-01-01 00:00:00+00",
    "ultimo_episodio": "2015-12-31 00:00:00+00"
  },
  {
    "año": "2016",
    "episodios_cerrados": 2732,
    "primer_episodio": "2016-01-01 00:00:00+00",
    "ultimo_episodio": "2016-12-31 00:00:00+00"
  },
  {
    "año": "2017",
    "episodios_cerrados": 3253,
    "primer_episodio": "2017-01-01 00:00:00+00",
    "ultimo_episodio": "2017-12-31 00:00:00+00"
  },
  {
    "año": "2018",
    "episodios_cerrados": 3076,
    "primer_episodio": "2018-01-01 00:00:00+00",
    "ultimo_episodio": "2018-12-31 00:00:00+00"
  },
  {
    "año": "2019",
    "episodios_cerrados": 2187,
    "primer_episodio": "2019-01-01 00:00:00+00",
    "ultimo_episodio": "2019-12-31 00:00:00+00"
  },
  {
    "año": "2020",
    "episodios_cerrados": 6395,
    "primer_episodio": "2020-01-02 00:00:00+00",
    "ultimo_episodio": "2020-12-31 00:00:00+00"
  },
  {
    "año": "2021",
    "episodios_cerrados": 2892,
    "primer_episodio": "2021-01-01 00:00:00+00",
    "ultimo_episodio": "2021-12-31 00:00:00+00"
  },
  {
    "año": "2022",
    "episodios_cerrados": 5041,
    "primer_episodio": "2022-01-01 00:00:00+00",
    "ultimo_episodio": "2022-12-31 00:00:00+00"
  },
  {
    "año": "2023",
    "episodios_cerrados": 2587,
    "primer_episodio": "2023-01-01 00:00:00+00",
    "ultimo_episodio": "2023-12-31 00:00:00+00"
  },
  {
    "año": "2024",
    "episodios_cerrados": 2767,
    "primer_episodio": "2024-01-01 00:00:00+00",
    "ultimo_episodio": "2024-12-30 00:00:00+00"
  },
  {
    "año": "2025",
    "episodios_cerrados": 2476,
    "primer_episodio": "2025-01-01 00:00:00+00",
    "ultimo_episodio": "2025-12-31 00:00:00+00"
  },
  {
    "año": "2026",
    "episodios_cerrados": 476,
    "primer_episodio": "2026-01-01 00:00:00+00",
    "ultimo_episodio": "2026-02-11 05:08:00+00"
  }
]


-- 2. Episodios que ya tienen datos VAE vs los que faltan

Consulta:

SELECT 
    CASE WHEN fe.start_date < '2025-12-01' THEN 'historico_2015+' ELSE 'reciente' END AS regimen,
    COUNT(DISTINCT fe.id) AS total_episodios,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) AS con_monitoreo_vae,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) AS sin_monitoreo_vae,
    ROUND(
        (COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) * 100.0 / 
         COUNT(DISTINCT fe.id)), 2
    ) AS pct_sin_monitoreo
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
GROUP BY regimen
ORDER BY regimen;

Resultado:

[
  {
    "regimen": "historico_2015+",
    "total_episodios": 35183,
    "con_monitoreo_vae": 0,
    "sin_monitoreo_vae": 35183,
    "pct_sin_monitoreo": "100.00"
  },
  {
    "regimen": "reciente",
    "total_episodios": 631,
    "con_monitoreo_vae": 10,
    "sin_monitoreo_vae": 621,
    "pct_sin_monitoreo": "98.42"
  }
]


-- 3. Estimación detallada de GEE requests requeridos

Consulta:
WITH episodios_para_backfill AS (
    SELECT 
        fe.id,
        fe.start_date,
        CASE 
            WHEN fe.start_date < '2025-12-01' THEN 'historico'
            ELSE 'reciente'
        END AS regimen,
        -- Calcular puntos de análisis necesarios
        CASE 
            WHEN fe.start_date < '2025-12-01' THEN
                -- Semestral desde fecha del incendio hasta hoy
                EXTRACT(YEAR FROM AGE(CURRENT_DATE, fe.start_date)) * 2 + 
                CASE 
                    WHEN EXTRACT(MONTH FROM fe.start_date) <= 6 THEN 2 
                    ELSE 1 
                END
            ELSE
                -- Mensual desde Dec 2025 hasta hoy
                EXTRACT(MONTH FROM AGE(CURRENT_DATE, '2025-12-01')) + 1
        END AS puntos_analisis
    FROM fire_events fe
    WHERE fe.status IN ('extinct', 'closed')
      AND fe.start_date >= '2015-01-01'
      AND NOT EXISTS (
          SELECT 1 FROM vegetation_monitoring vm 
          WHERE vm.fire_event_id = fe.id
      )
)
SELECT 
    regimen,
    COUNT(*) AS episodios,
    SUM(puntos_analisis) AS total_puntos_analisis,
    SUM(puntos_analisis) * 2 AS estimated_gee_requests,  -- 2 req por punto (baseline + current)
    ROUND(SUM(puntos_analisis) * 2.0 / 5000, 2) AS dias_procesamiento_5000_req,
    ROUND(AVG(puntos_analisis), 1) AS promedio_puntos_por_episodio
FROM episodios_para_backfill
GROUP BY regimen
ORDER BY regimen;


Resultado:

[
  {
    "regimen": "historico",
    "episodios": 35183,
    "total_puntos_analisis": "401055",
    "estimated_gee_requests": "802110",
    "dias_procesamiento_5000_req": "160.42",
    "promedio_puntos_por_episodio": "11.4"
  },
  {
    "regimen": "reciente",
    "episodios": 621,
    "total_puntos_analisis": "2484",
    "estimated_gee_requests": "4968",
    "dias_procesamiento_5000_req": "0.99",
    "promedio_puntos_por_episodio": "4.0"
  }
]


-- 4. Distribución por áreas protegadas (prioritización)

Consulta:

SELECT 
    CASE WHEN fe.start_date < '2025-12-01' THEN 'historico_2015+' ELSE 'reciente' END AS regimen,
    CASE WHEN fpa.protected_area_id IS NOT NULL THEN 'protegida' ELSE 'no_protegida' END AS area_tipo,
    COUNT(DISTINCT fe.id) AS episodios,
    COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) AS necesitan_backfill
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
LEFT JOIN fire_protected_area_intersections fpa ON fpa.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
GROUP BY regimen, area_tipo
ORDER BY regimen, area_tipo;

Resultado:

[
  {
    "regimen": "historico_2015+",
    "area_tipo": "no_protegida",
    "episodios": 30981,
    "necesitan_backfill": 30981
  },
  {
    "regimen": "historico_2015+",
    "area_tipo": "protegida",
    "episodios": 4202,
    "necesitan_backfill": 4202
  },
  {
    "regimen": "reciente",
    "area_tipo": "no_protegida",
    "episodios": 475,
    "necesitan_backfill": 465
  },
  {
    "regimen": "reciente",
    "area_tipo": "protegida",
    "episodios": 156,
    "necesitan_backfill": 156
  }
]



VAE Backfill Implementation - Status: Ready for Execution

## Estado Actual: INTEGRACIÓN COMPLETADA

- **VAE module improvements**: Applied to VM
- **Backfill task**: Enhanced with year-by-year execution capability
- **Celery integration**: `workers.tasks.backfill` added to celery_app.py
- **Optimization parameters**: target_year, magnitude_threshold, optimize_frequency
- **Commands ready**: Year-by-year execution scripts documented

## Próximos Pasos: EJECUCIÓN POR AÑO (2025 → 2015)

See `backfill_commands_by_year.md` for detailed execution commands.

Current State Analysis
VAE module improvements: Already applied to VM per documentation
Backfill task: Exists in workers/tasks/backfill.py with complete implementation
Scheduler: Has VAE recovery tasks configured in workers/celery_app.py
Missing integration: backfill.py not included in celery_app.py include list
Queue routing: Backfill task correctly configured for vae queue
Implementation Tasks
Phase 1: F11 Backfill Integration (Priority P2)
F11-01: Optimize throughput and queue configuration

Increase GEE request limit from 5,000 to 50,000-100,000 req/day (project-level quota)
Scale VAE workers: 10 parallel workers for ~430,000 analysis points/day
Target processing time: 2-3 weeks instead of 160 days
Monitor EECU consumption: ~111 EECU-hours within 150 free monthly quota
F11-02: Implement prioritization strategy

Priority 1: Protected areas + Régimen B (recent, 621 episodes)
Priority 2: Large magnitude events (>500 ha) from last 5 years
Priority 3: Historical (Régimen A) in reverse chronological order (2024→2015)
Reduce analysis frequency for 2015-2018: annual instead of semestral (50% reduction)
F11-03: Adjust backfill scope for historical data (2015-today)

Remove 36-month limitation in _fetch_events query
Implement smart point generation: annual for 2015-2018, semestral for 2019-2025
Add magnitude-based prioritization in query logic
Ensure idempotency at individual request level (not just batch start)
F11-04: Integrate backfill task with Celery

Add 'workers.tasks.backfill' to celery_app.py include list
Configure queue scaling: increase worker count for vae queue
Test backfill task execution with small batch
Implement exponential backoff for GEE rate limits (429, 500 errors)
F11-05: Execute optimized backfill

Phase 1: Protected areas + recent episodes (1-2 days)
Phase 2: Large events 2019-2025 (3-5 days)
Phase 3: Remaining historical with reduced frequency (10-15 days)
Monitor EECU quota and GEE limits daily
F11-06: Documentation and verification

Document commands in docs/tasks/VAE update/vae_backfill.md
Create monitoring queries for progress tracking
Verify idempotency and error handling
Document bypass for rate limiting in backfill context
Phase 2: F12-F14 Additional Features (Priority P2/P3)
F12: Trigger endpoint with rate limiting

Verify existing rate limiter supports 5 req/6h per user
Implement bypass for backfill system using service account credentials
Test admin authentication requirements
Document trigger usage and bypass mechanism
F13: Confidence score in UI

Verify confidence_score is populated from destruction detection
Ensure cloud_pixel_percentage penalization in confidence calculation
Ensure display in LandUseChangeCard components
Document confidence model for historical images (Landsat 7/8 considerations)
F14: Test suite implementation

Unit tests for recovery thresholds
Integration tests for monitoring API
Worker idempotency tests (individual request level)
Queue routing verification tests
EECU quota monitoring tests
Technical Considerations
Queue Management (Optimized)
Backfill uses vae queue with priority 9 (lower than regular scheduling)
Optimized GEE cap: 50,000-100,000 requests/day (project-level quota)
Worker scaling: 10 parallel workers for ~430,000 analysis points/day
Request cost: 2 per analysis point (baseline + current)
EECU monitoring: Target ~111 EECU-hours within 150 free monthly quota
Database Impact
Target: Closed events (extinct, closed) without existing VAE data
Time window: 2015-today (extended from 36-month limit)
Smart prioritization: Protected areas → Large events → Historical reverse chronological
Frequency optimization: Annual for 2015-2018, semestral for 2019-2025
Idempotency: UNIQUE constraints prevent duplicates + individual request-level checks
Throughput Optimization
Phase 1: Protected areas + recent (621 episodes) → 1-2 days
Phase 2: Large events >500ha (2019-2025) → 3-5 days
Phase 3: Historical with reduced frequency → 10-15 days
Total target: 2-3 weeks vs original 160 days
Error Handling & Monitoring
Exponential backoff: For GEE 429/500 errors
DLQ management: Automatic retry with backoff for failed requests
EECU quota alerts: Daily monitoring and automatic pause if approaching limits
Progress tracking: Real-time dashboards for each phase
Execution Commands
Test Integration
bash
# Verify backfill task is available
docker compose exec worker-gee celery -A workers.celery_app inspect registered | grep backfill
 
# Test small batch
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 5, "regime": "A"}' -Q vae
Production Execution (Optimized Phases)
bash
# Phase 1: Protected areas + recent (Priority 1)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 200, "regime": "both", "prioritize_protected": true, "magnitude_threshold": 0}' -Q vae
 
# Phase 2: Large events >500ha (Priority 2) 
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 300, "regime": "A", "magnitude_threshold": 500, "prioritize_protected": false}' -Q vae
 
# Phase 3: Historical with optimized frequency (Priority 3)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 500, "regime": "A", "magnitude_threshold": 0, "optimize_frequency": true}' -Q vae
 
# Monitor EECU consumption during execution
docker compose exec worker-gee python -c "
from app.services.gee_service import GEEService
gee = GEEService()
print(f'EECU usage: {gee.get_current_month_usage()}/150 hours')
"
Progress Monitoring
sql
-- Track backfill progress by regime (updated for 2015-today scope)
SELECT
  CASE WHEN fe.start_date < '2025-12-01' THEN 'historico_2015+' ELSE 'reciente' END AS regimen,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) AS con_monitoreo,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) AS sin_monitoreo,
  MIN(fe.start_date) AS evento_mas_antiguo,
  MAX(fe.start_date) AS evento_mas_reciente
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'  -- Updated from 36-month limit
GROUP BY 1;
 
-- Estimate GEE quota requirements
SELECT
  CASE WHEN fe.start_date < '2025-12-01' THEN 'historico' ELSE 'reciente' END AS regimen,
  COUNT(DISTINCT fe.id) AS episodios,
  SUM(
    CASE 
      WHEN fe.start_date < '2025-12-01' THEN
        -- Semestral points from 2015 to today
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, fe.start_date)) * 2 + 2
      ELSE
        -- Monthly points from Dec 2025 to today  
        EXTRACT(MONTH FROM AGE(CURRENT_DATE, '2025-12-01')) + 1
    END
  ) * 2 AS estimated_gee_requests  -- 2 requests per point (baseline + current)
FROM fire_events fe
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date >= '2015-01-01'
  AND NOT EXISTS (
    SELECT 1 FROM vegetation_monitoring vm 
    WHERE vm.fire_event_id = fe.id
  )
GROUP BY 1;
Success Criteria
F11: Backfill task integrated and processing 35,183 episodes in 2-3 weeks
F12: Trigger endpoint functional with bypass for backfill operations
F13: Confidence scores displayed with cloud penalization for historical images
F14: Comprehensive test suite passing including EECU monitoring
Documentation: All commands and procedures documented
Monitoring: Real-time progress tracking and EECU quota alerts operational
Throughput: Sustained 50,000+ GEE requests/day without quota exhaustion
Risk Mitigation (Updated)
EECU quota exhaustion: Monitor daily usage, auto-pause at 140 hours (10 hour buffer)
GEE rate limiting: Exponential backoff for 429/500 errors, service account bypass for user limits
Database performance: Batch processing with connection pooling for large dataset
Task failures: DLQ with automatic retry and manual intervention procedures
Processing time: Phased approach ensures early value delivery while maintaining system stability
Historical accuracy: Cloud percentage penalization ensures confidence scores reflect data quality