# Corrección: estrategia de backfill con dos regímenes

Fecha: 2026-03-12
Tipo: delta sobre documentos existentes
Motivo: refinamiento de la decisión D-07 (backfill histórico)

---

## Decisión actualizada

**D-07 (antes):** serie completa semestral para todos los eventos.

**D-07 (ahora):** dos regímenes diferenciados por fecha de corte **1 de diciembre de 2025**:

| Régimen | Aplica a | Frecuencia de puntos | Ejecución | Episodios |
|---|---|---|---|---|
| **A — históricos** | Episodios cerrados con `start_date < 2025-12-01` | Cada 6 meses desde `start_date` hasta hoy | One-shot (backfill único) | Solo cerrados |
| **B — recientes** | Episodios cerrados con `start_date >= 2025-12-01` | Mensual desde `start_date` hasta hoy | One-shot (backfill) + scheduling regular a futuro | Solo cerrados |

Los episodios **activos** (no cerrados) se cubren con el beat schedule regular (monthly + weekly-recent + episodios, escenario C). No entran en el backfill.

Los episodios **nuevos** que surjan a partir de 2026 y pasen a cerrado entrarán automáticamente en régimen B (mensual) vía el scheduling regular que ya los procesa mientras están activos.

---

## Impacto en quota GEE (recalculado)

Asumiendo ~300 históricos cerrados y ~80 recientes cerrados:

| Régimen | Eventos | Puntos/evento (promedio) | Req GEE/evento | Total req GEE |
|---|---|---|---|---|
| A (históricos, semestral) | ~300 | ~4 (24 meses / 6) | ~8 | ~2 400 |
| B (recientes, mensual) | ~80 | ~4 (dic 2025 a mar 2026) | ~8 | ~640 |
| **Total backfill** | | | | **~3 040** |

Ejecutable en 1 día con cap de 5 000 req/día. Sin impacto en operación regular.

---

## Documento 1: `vae_module_specification.md`

### Corrección en sección 3 — tabla de decisiones

Reemplazar fila D-07:

**Antes:**
```
| D-07 | Backfill | Serie completa semestral (cada 6 meses, no mensual) | Reduce costo a ~1/6 del mensual |
```

**Después:**
```
| D-07 | Backfill | Dos regímenes: semestral para históricos cerrados (pre dic 2025), mensual para recientes cerrados (dic 2025+). One-shot. Episodios activos cubiertos por scheduling regular. | ~3 040 req GEE totales |
```

---

### Corrección en sección 5.3 — flujo de backfill histórico

Reemplazar el bloque completo de la sección 5.3 por:

```
### 5.3 Flujo de backfill histórico

Fecha de corte: 2025-12-01

Régimen A — episodios cerrados con start_date < 2025-12-01:
    │
    ├── 1. Query: episodios cerrados sin registros en vegetation_monitoring
    │      WHERE start_date < '2025-12-01'
    │      AND status IN ('extinct', 'closed')
    │      ORDER BY: áreas protegidas primero (relevancia legal)
    ├── 2. Para cada episodio:
    │      ├── Generar puntos de análisis cada 6 meses desde start_date
    │      │   Ejemplo: incendio 2023-01 → 2023-07, 2024-01, 2024-07, 2025-01, 2025-07
    │      └── Para cada punto: ejecutar analyze_recovery
    ├── 3. Cap diario: 5 000 req GEE
    └── 4. Horario: madrugada UTC-3

Régimen B — episodios cerrados con start_date >= 2025-12-01:
    │
    ├── 1. Query: episodios cerrados sin registros en vegetation_monitoring
    │      WHERE start_date >= '2025-12-01'
    │      AND status IN ('extinct', 'closed')
    ├── 2. Para cada episodio:
    │      ├── Generar puntos de análisis mensuales desde start_date
    │      │   Ejemplo: incendio 2025-12 → 2026-01, 2026-02, 2026-03
    │      └── Para cada punto: ejecutar analyze_recovery
    ├── 3. Mismo cap diario compartido con régimen A
    └── 4. Ejecutar después de completar régimen A (prioridad a históricos)

Notas:
- Episodios activos NO entran en backfill (cubiertos por beat schedule).
- Episodios nuevos (2026+) que pasen a cerrado ya tendrán datos del
  scheduling regular; si tienen gaps, el beat schedule mensual los cubre.
- El backfill es one-shot: una vez completado, no se re-ejecuta.
```

---

### Corrección en sección 6.3 — consumo estimado de quota GEE

Agregar fila de backfill a la tabla:

```
| Tarea | Frecuencia | Eventos/ciclo | Req GEE/ciclo | Req GEE/mes |
|---|---|---|---|---|
| recovery-monthly | 1×/mes | ~200 | ~400 | 400 |
| recovery-weekly-recent | 4×/mes | ~50 | ~100 | 400 |
| vae-episodes-weekly | 4×/mes | ~30 | ~60 | 240 |
| vae-destruction-monthly | 1×/mes | ~200 | ~600 | 600 |
| **Total scheduling** | | | | **~1 640/mes** |
| **Backfill (one-shot)** | **1 vez** | **~380** | **~3 040** | **n/a** |
```

---

## Documento 2: `vae_p2p3_technical_tasks_f9_f14.md`

### Corrección en F11-01: reescribir tarea de backfill

Reemplazar el código completo de `backfill_historical_recovery` en la sección F11-01 por:

```python
"""
Backfill de datos VAE para episodios cerrados sin monitoreo.
Dos regímenes:
  A) Históricos (start_date < 2025-12-01): puntos semestrales
  B) Recientes (start_date >= 2025-12-01): puntos mensuales
Prioriza episodios en áreas protegidas.
Cap diario: 5000 req GEE.
One-shot: ejecutar una vez para poblar datos históricos.
"""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from workers.celery_app import celery_app
from app.db.session import SessionLocal
from workers.tasks.recovery import analyze_recovery

logger = logging.getLogger(__name__)

DAILY_GEE_CAP = 5000
REQUESTS_PER_POINT = 2  # baseline + current
CUTOFF_DATE = date(2025, 12, 1)


def _generate_analysis_points(
    fire_date: date, today: date, interval_months: int
) -> list[date]:
    """Genera lista de fechas de análisis desde fire_date hasta today."""
    points = []
    point = fire_date + relativedelta(months=interval_months)
    while point <= today:
        points.append(point.replace(day=1))
        point += relativedelta(months=interval_months)
    # Agregar punto actual si no coincide con el último
    current_month = today.replace(day=1)
    if not points or points[-1] != current_month:
        points.append(current_month)
    return points


@celery_app.task(queue="vae", soft_time_limit=3600, time_limit=3900)
def backfill_historical_recovery(
    batch_size: int = 50,
    regime: str = "both",  # "A", "B", o "both"
    prioritize_protected: bool = True,
) -> dict:
    """
    Procesa un batch de episodios cerrados sin datos VAE.

    Args:
        batch_size: máximo de episodios a procesar por ejecución.
        regime: "A" (históricos semestral), "B" (recientes mensual),
                "both" (primero A, luego B con el cap restante).
        prioritize_protected: ordenar por áreas protegidas primero.
    """
    db = SessionLocal()
    try:
        today = date.today()
        total_enqueued = 0
        events_processed = 0
        results = {"regime_a": 0, "regime_b": 0}

        # ── Régimen A: históricos cerrados pre-dic 2025, semestral ──
        if regime in ("A", "both"):
            events_a = _fetch_events(
                db, batch_size, before_date=CUTOFF_DATE,
                prioritize_protected=prioritize_protected
            )
            for event in events_a:
                points = _generate_analysis_points(
                    event.start_date, today, interval_months=6
                )
                cost = len(points) * REQUESTS_PER_POINT
                if total_enqueued + cost > DAILY_GEE_CAP:
                    logger.info(f"Cap alcanzado en régimen A: {total_enqueued} req")
                    break
                _enqueue_points(event.id, points)
                total_enqueued += cost
                events_processed += 1
                results["regime_a"] += 1

        # ── Régimen B: recientes cerrados dic 2025+, mensual ──
        if regime in ("B", "both") and total_enqueued < DAILY_GEE_CAP:
            remaining_batch = batch_size - events_processed
            if remaining_batch > 0:
                events_b = _fetch_events(
                    db, remaining_batch, from_date=CUTOFF_DATE,
                    prioritize_protected=prioritize_protected
                )
                for event in events_b:
                    points = _generate_analysis_points(
                        event.start_date, today, interval_months=1
                    )
                    cost = len(points) * REQUESTS_PER_POINT
                    if total_enqueued + cost > DAILY_GEE_CAP:
                        logger.info(f"Cap alcanzado en régimen B: {total_enqueued} req")
                        break
                    _enqueue_points(event.id, points)
                    total_enqueued += cost
                    events_processed += 1
                    results["regime_b"] += 1

        logger.info(
            f"Backfill completado: {events_processed} episodios, "
            f"{total_enqueued} req GEE encolados. "
            f"Régimen A: {results['regime_a']}, B: {results['regime_b']}"
        )
        return {
            "status": "ok",
            "events_processed": events_processed,
            "total_requests_enqueued": total_enqueued,
            **results,
        }

    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)
        return {"status": "error", "reason": str(e)}
    finally:
        db.close()


def _fetch_events(
    db, batch_size: int,
    before_date: date | None = None,
    from_date: date | None = None,
    prioritize_protected: bool = True,
):
    """Obtiene episodios cerrados sin datos de monitoreo."""
    date_filter = ""
    if before_date:
        date_filter = f"AND fe.start_date < '{before_date.isoformat()}'"
    elif from_date:
        date_filter = f"AND fe.start_date >= '{from_date.isoformat()}'"

    order = """
        ORDER BY
            CASE WHEN fpa.protected_area_id IS NOT NULL THEN 0 ELSE 1 END,
            fe.start_date ASC
    """ if prioritize_protected else "ORDER BY fe.start_date ASC"

    return db.execute(text(f"""
        SELECT DISTINCT fe.id, fe.start_date
        FROM fire_events fe
        LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
        LEFT JOIN fire_protected_area_intersections fpa
            ON fpa.fire_event_id = fe.id
        WHERE vm.id IS NULL
          AND fe.status IN ('extinct', 'closed')
          AND fe.start_date > NOW() - INTERVAL '36 months'
          {date_filter}
        {order}
        LIMIT :batch
    """), {"batch": batch_size}).fetchall()


def _enqueue_points(event_id: str, points: list[date]):
    """Encola analyze_recovery para cada punto de análisis."""
    for point in points:
        analyze_recovery.apply_async(
            args=[str(event_id), point.isoformat()],
            queue="vae",
            priority=9,  # baja prioridad vs scheduling regular
        )
    logger.info(
        f"Backfill: {event_id} → {len(points)} puntos encolados "
        f"({points[0]} a {points[-1]})"
    )
```

---

### Corrección en F11-02: comandos de ejecución

Reemplazar los comandos de ejecución por:

```bash
# Ejecutar solo régimen A (históricos semestrales):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "A", "prioritize_protected": true}' -Q vae

# Ejecutar solo régimen B (recientes mensuales):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 50, "regime": "B", "prioritize_protected": true}' -Q vae

# Ejecutar ambos (A primero, B con el cap restante):
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.backfill.backfill_historical_recovery \
  --kwargs='{"batch_size": 100, "regime": "both"}' -Q vae

# Monitorear progreso:
psql "$DATABASE_URL" -c "
SELECT
  CASE WHEN fe.start_date < '2025-12-01' THEN 'historico' ELSE 'reciente' END AS regimen,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NOT NULL) AS con_monitoreo,
  COUNT(DISTINCT fe.id) FILTER (WHERE vm.id IS NULL) AS sin_monitoreo
FROM fire_events fe
LEFT JOIN vegetation_monitoring vm ON vm.fire_event_id = fe.id
WHERE fe.status IN ('extinct', 'closed')
  AND fe.start_date > NOW() - INTERVAL '36 months'
GROUP BY 1;
"
```

---

## Documento 3: `vae_p1_technical_tasks_f5_f6.md`

### Corrección menor en F5-03: firma de analyze_recovery

La firma ya contempla `target_date_str: str | None = None` (agregado en la spec original de F11). Verificar que la nota en la sección F11 de `vae_p2p3_technical_tasks_f9_f14.md` que dice "agregar parámetro target_date_str" se mantiene consistente.

Sin cambio de código adicional. Solo confirmar que la firma en F5-03 es:

```python
def analyze_recovery(self, fire_event_id: str, target_date_str: str | None = None):
```

---

## Documento 4: `vae_quota_impact_analysis.md`

### Corrección en sección "Pregunta 8: backfill"

Agregar nota aclaratoria al final de la sección:

```
### Actualización (2026-03-12): estrategia de backfill refinada

La decisión final usa dos regímenes con fecha de corte 2025-12-01:
- Régimen A (históricos cerrados pre-dic 2025): puntos semestrales → ~2 400 req GEE
- Régimen B (recientes cerrados dic 2025+): puntos mensuales → ~640 req GEE
- Total backfill one-shot: ~3 040 req GEE
- Solo episodios cerrados. Activos cubiertos por scheduling regular.

Esto reemplaza la estimación anterior de "serie completa semestral" uniforme.
```

---

## Documentos NO afectados

| Documento | Razón |
|---|---|
| `vae_p0_technical_tasks.md` (F1-F4) | Schema, umbrales, colas y taxonomía no dependen de la estrategia de backfill |
| `vae_p1p2_technical_tasks_f7_f8.md` (F7-F8) | El frontend no distingue origen de datos (backfill vs scheduling) |

---

## Resumen de cambios

| Documento | Sección | Tipo de cambio |
|---|---|---|
| `vae_module_specification.md` | 3 (decisiones), 5.3 (flujo backfill), 6.3 (quota) | Reescritura parcial |
| `vae_p2p3_technical_tasks_f9_f14.md` | F11-01 (tarea backfill), F11-02 (comandos) | Reescritura completa de F11 |
| `vae_p1_technical_tasks_f5_f6.md` | F5-03 (firma worker) | Verificación de consistencia, sin cambio de código |
| `vae_quota_impact_analysis.md` | Sección 8 | Nota aclaratoria al final |
