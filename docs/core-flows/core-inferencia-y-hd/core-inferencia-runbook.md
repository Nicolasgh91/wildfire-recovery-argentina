## Core Inferencia, Recurrencia y Exploración HD — Runbook de troubleshooting

### Escenario 1: Heatmap de recurrencia vacío o inconsistente

**Síntomas**:

- Capa de heatmap no muestra datos pese a tener historial de incendios.

**Pasos**:

1. Verificar que el pipeline base (ingesta + clustering + episodios) corrió en los últimos días.
2. Consultar `fires-stats`:

```bash
curl -s "$API_URL/api/v1/fires/stats" | jq
```

3. Si responde vacío, revisar servicios de recurrencia (`recurrence_service`) y sus queries H3.

### Escenario 2: Scores de calidad fuera de rango o incoherentes

**Síntomas**:

- `ReliabilityScore` muestra 0 o valores extremos para la mayoría de incendios.

**Pasos**:

1. Revisar en BD los campos de calidad:

```sql
SELECT id, reliability_score
FROM fire_events
ORDER BY start_date DESC
LIMIT 20;
```

2. Si todos son 0 o `NULL`, revisar el servicio `quality_service` y cualquier worker asociado (si existe) que deba poblar esos valores.

### Escenario 3: Exploraciones HD colgadas o sin assets

**Síntomas**:

- Exploraciones en estado “generando” por mucho tiempo.
- `GET /explorations/{id}/assets` devuelve lista vacía.

**Pasos**:

1. Revisar logs de `exploration_hd_worker`:

```bash
docker logs --tail 100 forestguard-worker-gee | grep -i exploration
```

2. Confirmar que las tareas Celery de exploración usan la cola correcta y que GEE/Storage están configurados.
3. Si el problema es intermitente (cuotas o timeouts GEE), reintentar generación para una exploración de prueba y monitorizar.

### Escenario 4: Desajuste entre UI y BD

**Síntomas**:

- Tablas de BD tienen datos de inferencia/HD pero la UI no muestra nada.

**Pasos**:

1. Verificar respuestas de:

```bash
curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/explorations" | jq
```

2. Comprobar que los componentes de UI (`Exploration.tsx`, `FireMap`, `ReliabilityScore`) están consumiendo los campos correctos y no hay cambios recientes en el contrato que falten cablear.

