## Core Pipeline End‑to‑End — Runbook de troubleshooting

Runbook orientado a incidentes que afectan múltiples tramos del pipeline.

### Escenario 1: No aparecen incendios/episodios en la UI

**Pasos rápidos**:

1. Verificar ingesta:

```sql
SELECT COUNT(*) FROM fire_detections WHERE acquisition_date >= CURRENT_DATE - INTERVAL '1 day';
```

2. Verificar eventos:

```sql
SELECT COUNT(*) FROM fire_events WHERE start_date >= CURRENT_DATE - INTERVAL '7 days';
```

3. Verificar episodios:

```sql
SELECT COUNT(*) FROM fire_episodes WHERE start_date >= CURRENT_DATE - INTERVAL '30 days';
```

4. Si alguno de los conteos es 0 cuando debería haber datos, revisar:
   - workers `ingestion`/`clustering`,
   - logs de Celery (`workers/celery_app.py` + contenedores).

### Escenario 2: Episodios sin thumbnails o assets faltantes

**Pasos**:

1. Verificar que `slides_data` está vacío:

```sql
SELECT id, status, gee_candidate, jsonb_array_length(slides_data) AS slides
FROM fire_episodes
WHERE status IN ('active','monitoring')
ORDER BY gee_priority DESC NULLS LAST
LIMIT 20;
```

2. Si `slides = 0`:
   - Revisar logs del worker de carrusel (`carousel_task`) en la cola `gee`.
   - Consultar `PNG_CORRUPTION_FIX_SUMMARY.md` y el runbook de preproceso si hay errores de PNG.

### Escenario 3: Análisis VAE desfasado respecto a eventos recientes

**Pasos**:

1. Revisar si `vegetation_monitoring` tiene filas recientes para eventos activos:

```sql
SELECT fire_event_id, MAX(monitoring_date) AS last_date
FROM vegetation_monitoring
GROUP BY fire_event_id
ORDER BY last_date DESC
LIMIT 20;
```

2. Si los workers están configurados pero no hay datos nuevos:
   - Verificar schedules GEE en `workers/celery_app.py` (tareas `recovery-*` y `vae-*`).
   - Ejecutar manualmente una tarea de `recovery` para un evento y revisar logs.

### Escenario 4: Validación E2E y reintento controlado

Para validar o reintentar de punta a punta sin reprocesar todo:

1. Usar `scripts/run_pipeline_manual.py` con un `days_back` moderado (por ejemplo, 7–30) en un entorno de prueba.
2. Verificar estado antes/después con el propio script (usa `show_state`).

Referencias útiles:

- `docs/INDEX.md`
- `docs/Carrusel fix/flujo_ingesta_procesamiento.md`
- `docs/assets-generation/tareas-tecnicas-assets-pipeline.md`

