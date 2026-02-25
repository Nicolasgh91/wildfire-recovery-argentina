# Corrección del ciclo de vida de estados de `fire_events`

**Proyecto:** ForestGuard  
**Fecha:** 2026-02-25  
**Severidad:** Alta — los episodios leen estados desactualizados de eventos  
**Fuentes de verdad:** `flujo_ingesta_procesamiento.md`, `episode_flow_parameters.py`, schema de BD

---

## 1. Diagnóstico

### 1.1 Causa raíz

Los `fire_events` se crean con `status = 'active'` en `app/services/detection_clustering_service.py` (línea 320) y **nunca transicionan** a `monitoring` ni `extinct` en la base de datos. No existe ningún worker, trigger ni proceso batch que persista las transiciones de estado.

La función `resolve_fire_status` en `app/services/fire_service.py` (línea 139) calcula el estado dinámicamente para la API/UI, pero es de solo lectura — no escribe el resultado en `fire_events.status`.

### 1.2 Impacto directo

Cuando `update_episode_metrics` (en `app/services/episode_service.py`, línea 381) recalcula el estado de un episodio, ejecuta:

```sql
array_remove(array_agg(DISTINCT fe.status), NULL) AS statuses
```

Lee el `status` persistido de cada `fire_event`. Como todos dicen `'active'` (nunca transicionaron), `_resolve_episode_status` (línea 162) siempre encuentra `"active" in event_statuses` y devuelve `'active'` para el episodio, incluso cuando los eventos llevan semanas sin actividad térmica.

Consecuencia: episodios que deberían estar en `monitoring` o `extinct` permanecen como `active`, distorsionando el carrusel, el mapa y las métricas del dashboard.

### 1.3 Flujo actual vs. flujo esperado

```
ACTUAL (roto):
  detection_clustering_service.py crea fire_event con status='active'
  └── Nunca cambia
  └── episode_service lee status='active' de la DB → episodio siempre 'active'
  └── resolve_fire_status calcula al vuelo para la API (no persiste)

ESPERADO (corregido):
  detection_clustering_service.py crea fire_event con status='active'
  └── update_event_statuses task persiste active → monitoring → extinct
  └── episode_service lee status actualizado → episodio refleja realidad
  └── resolve_fire_status lee status persistido (ya no necesita recalcular)
```

### 1.4 Datos afectados (snapshot 2026-02-25)

| Métrica | Valor |
|---------|-------|
| Eventos con `status='active'` en DB | 619 |
| De esos, con `last_seen_at > 168h` (deberían ser monitoring/extinct) | 619 |
| Episodios inflados como `active` por este bug | 535 |
| Eventos con `status='monitoring'` | 41 |
| Eventos con `status='extinct'` | 35,441 |

---

## 2. Pipeline diario propuesto

```
00:00 UTC  │  download_firms_daily          → fire_detections
           │
01:00 UTC  │  cluster_detections            → fire_events (status='active')
           │
01:30 UTC  │  update_event_statuses  [NUEVO] → fire_events.status actualizado
           │
02:00 UTC  │  cluster_fire_episodes_pipeline → fire_episodes (lee statuses frescos)
           │
03:00 UTC  │  generate_carousel             → slides_data
```

El task nuevo corre a las 01:30 UTC, **después** de que `cluster_detections` (01:00) crea los eventos nuevos con `active`, y **antes** de que `cluster_fire_episodes_pipeline` (02:00) agrupe eventos en episodios. Así `_resolve_episode_status` lee estados actualizados.

---

## 3. Tareas técnicas

### EVT-001 — Task batch `update_event_statuses`

**Archivo nuevo:** `workers/tasks/event_status_task.py`

**Lógica SQL:** tres UPDATEs en una sola transacción. El orden es estricto para reflejar el ciclo de vida canónico:

1. `active → monitoring`: temporal puro (7 días sin redetección)
2. `monitoring → extinct`: temporal (14 días) **más** check espacial (sin detecciones en ≤2km)
3. `monitoring → active` implícito: si hay detecciones en ≤2km, el paso 2 no aplica y el evento se reactiva en la próxima ejecución de `cluster_detections`

```python
"""
Batch event status lifecycle task.
Persists active → monitoring → extinct transitions in fire_events.

Ciclo de vida canónico (fuente: flujo_ingesta_procesamiento.md §4.4):
  active    (días 0-7 desde last_seen_at)
  monitoring (días 7-14, evaluación espacial activa)
  extinct   (sin detección en ≤2km durante la ventana 7-14d)

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md
"""

import logging
import time

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.episode_flow_parameters import load_canonical_episode_flow_parameters
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.tasks.event_status_task.update_event_statuses",
    queue="clustering",
    max_retries=3,
)
def update_event_statuses(self):
    """
    Persiste las transiciones de estado de fire_events.

    Reglas (en orden de ejecución):
      1. active → monitoring  si last_seen_at + 7d < NOW  (temporal)
      2. monitoring → extinct si last_seen_at + 14d < NOW  (temporal)
                              Y no hay detecciones en ≤2km tras last_seen_at (espacial)

    reference_time = COALESCE(last_seen_at, end_date, start_date)
    Parámetros:
      event_monitoring_window_hours  = 168  (7d: umbral active→monitoring)
      event_extinction_window_hours  = 336  (14d: umbral monitoring→extinct)
    """
    t0 = time.monotonic()
    db = SessionLocal()
    try:
        params = load_canonical_episode_flow_parameters(db)
        active_window = int(params.get("event_monitoring_window_hours", 168))
        extinct_window = int(params.get("event_extinction_window_hours", 336))

        # Paso 1: active → monitoring (criterio temporal puro, 7 días)
        r_monitoring = db.execute(
            text("""
                UPDATE fire_events
                   SET status = 'monitoring',
                       updated_at = NOW()
                 WHERE status = 'active'
                   AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
                   AND COALESCE(last_seen_at, end_date, start_date)
                       < NOW() - MAKE_INTERVAL(hours => :active_window)
            """),
            {"active_window": active_window},
        )

        # Paso 2: monitoring → extinct (criterio temporal + espacial, 14 días)
        # El NOT EXISTS verifica ausencia de cualquier fire_detection en ≤2km
        # aparecida DESPUÉS de last_seen_at. Si existe alguna, significa que el
        # evento fue reactivado por cluster_detections y no debe marcarse extinct.
        r_extinct = db.execute(
            text("""
                UPDATE fire_events
                   SET status = 'extinct',
                       updated_at = NOW()
                 WHERE id IN (
                     SELECT fe.id
                       FROM fire_events fe
                      WHERE fe.status = 'monitoring'
                        AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
                        AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                            < NOW() - MAKE_INTERVAL(hours => :extinct_window)
                        AND NOT EXISTS (
                            SELECT 1
                              FROM fire_detections fd
                             WHERE ST_DWithin(
                                       fd.location::geography,
                                       fe.centroid,
                                       2000
                                   )
                               AND fd.detected_at
                                   > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                        )
                 )
            """),
            {"extinct_window": extinct_window},
        )

        db.commit()

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        result = {
            "success": True,
            "to_monitoring": r_monitoring.rowcount,
            "to_extinct": r_extinct.rowcount,
            "active_window_hours": active_window,
            "extinct_window_hours": extinct_window,
            "elapsed_ms": elapsed_ms,
        }
        logger.info("Event status update complete: %s", result)
        return result

    except Exception as exc:
        db.rollback()
        logger.exception("Event status update failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
```

**Decisiones de diseño:**

| Decisión | Justificación |
|----------|---------------|
| SQL directo (no ORM) | Rendimiento: un UPDATE batch es O(1) roundtrips vs. N queries con ORM |
| Orden monitoring-primero | Un evento que pasa de active a monitoring en esta ejecución no puede pasar a extinct en la misma (necesita estar 7d más en monitoring) |
| `NOT EXISTS` con `ST_DWithin` | Verifica ausencia de cualquier detección en ≤2km post-`last_seen_at`; si hay una, el evento fue reactivado y no debe extinguirse |
| `fd.location::geography` | Convierte geometry a geography para que ST_DWithin use metros reales |
| `MAKE_INTERVAL(hours => :window)` | Parametrizado desde `system_parameters`, no hardcodeado |
| Cola `clustering` | Reutiliza `worker-clustering` existente; no requiere nuevo container |
| `max_retries=3` | Consistente con el patrón de los otros tasks de clustering |
| No toca eventos con `reference_time IS NULL` | Defensivo: eventos sin timestamp temporal se excluyen del UPDATE |

**Definición de `reference_time` (consistencia con `fire_service.py` línea 121):**

```
COALESCE(last_seen_at, end_date, start_date)
```

Replica exactamente `FireService._event_reference_time()`:
```python
# app/services/fire_service.py:121-122
@staticmethod
def _event_reference_time(fire: FireEvent) -> Optional[datetime]:
    return fire.last_seen_at or fire.end_date or fire.start_date
```

---

### EVT-002 — Registro en beat schedule y routing

**Archivo:** `workers/celery_app.py`

**Cambio 1 — task_routes (línea ~112):** agregar después de la entry de `cluster_fire_episodes_pipeline`:

```python
'workers.tasks.event_status_task.update_event_statuses': {'queue': 'clustering'},
```

**Cambio 2 — beat_schedule (entre `cluster-daily` y `cluster-episodes-daily`):**

```python
'update-event-statuses-daily': {
    'task': 'workers.tasks.event_status_task.update_event_statuses',
    'schedule': crontab(hour=1, minute=30),  # 01:30 UTC
    'options': {'queue': 'clustering'},
},
```

**No requiere cambios en `docker-compose.yml`:** el servicio `worker-clustering` ya consume la cola `clustering` (línea 210 de `docker-compose.yml`: `--queues=clustering`).

**Posición en el beat schedule completo post-cambio:**

| Hora UTC | Task | Cola |
|----------|------|------|
| 00:00 | `download_firms_daily` | ingestion |
| 01:00 | `cluster_detections` | clustering |
| **01:30** | **`update_event_statuses`** | **clustering** |
| 02:00 | `cluster_fire_episodes_pipeline` | clustering |
| 03:00 | `generate_carousel` | analysis |
| 04:00 | `cleanup_expired_assets` | analysis |
| 08:00 | `generate_closure_reports` | analysis |

**Riesgo de contención:** los 3 tasks de clustering (01:00, 01:30, 02:00) corren en la misma cola con `concurrency=2`. El task de 01:00 (`cluster_detections`) puede tardar hasta 2h si hay muchas detecciones. Si aún no terminó a las 01:30, `update_event_statuses` espera en la cola y se ejecuta cuando el worker quede libre. Esto es seguro: el task de episodios (02:00) también espera en la misma cola, manteniendo el orden.

---

### EVT-003 — Parámetros de ventana temporal en `system_parameters`

#### `event_monitoring_window_hours` (existente)

**Estado:** ya existe en la tabla.

```
param_key: event_monitoring_window_hours
param_value: {"unit": "hours", "value": 168}
```

Controla la transición `active → monitoring` (umbral: 7 días desde `last_seen_at`).

**Lectura en código:**

1. `app/services/episode_flow_parameters.py` — `CANONICAL_EPISODE_FLOW_DEFAULTS` incluye `"event_monitoring_window_hours": 168` como fallback
2. `app/services/fire_service.py:131` — `_event_monitoring_window_hours()` lo lee vía `load_canonical_episode_flow_parameters()`
3. `app/services/export_service.py:46` — copia duplicada del mismo método (ver deuda DT-001)
4. EVT-001 (nuevo task) — parámetro `active_window` del UPDATE paso 1

**No requiere INSERT.** Solo se documenta como referencia.

#### `event_extinction_window_hours` (NUEVO)

**Estado:** debe insertarse.

```sql
INSERT INTO system_parameters (param_key, param_value)
VALUES ('event_extinction_window_hours', '{"unit": "hours", "value": 336}');
```

Controla la transición `monitoring → extinct` (umbral temporal: 14 días desde `last_seen_at`). Se combina con el check espacial de ≤2km. Valor = `event_monitoring_window_hours × 2`.

**Agregar a `CANONICAL_EPISODE_FLOW_DEFAULTS` en `app/services/episode_flow_parameters.py`:**

```python
"event_extinction_window_hours": 336,   # 14 días: umbral monitoring → extinct
```

**Lectura en código:**

1. `app/services/episode_flow_parameters.py` — agregar a `CANONICAL_EPISODE_FLOW_DEFAULTS`
2. EVT-001 (nuevo task) — parámetro `extinct_window` del UPDATE paso 2 (spatial check)

---

### EVT-007 — Migrations de schema

Prerequisito de EVT-006. Debe ejecutarse antes de activar el task `episode_closer`.

#### 7a — Agregar `extinct_at` a `fire_episodes`

La columna es necesaria para que `episode_closer` pueda evaluar cuándo promover un episodio a `closed`. Sin ella, no hay forma de calcular "30 días desde que fue extinct".

```sql
-- Migration: agregar extinct_at a fire_episodes
ALTER TABLE fire_episodes ADD COLUMN IF NOT EXISTS extinct_at TIMESTAMPTZ;

-- Backfill para episodios ya extintos: usar updated_at como aproximación
-- (es la mejor estimación disponible sin historial de cambios)
UPDATE fire_episodes
   SET extinct_at = updated_at
 WHERE status = 'extinct'
   AND extinct_at IS NULL;
```

**Archivo de modelo a actualizar:** `app/models/episode.py`

```python
# Agregar a la clase FireEpisode:
extinct_at = Column(DateTime(timezone=True))
```

#### 7b — Agregar `CLOSED` a `FireStatus` enum

**Archivo:** `app/schemas/fire.py`

```python
class FireStatus(str, Enum):
    ACTIVE = "active"
    MONITORING = "monitoring"
    EXTINCT = "extinct"
    CLOSED = "closed"    # NUEVO: episodio archivado, solo visible en históricos
```

**Nota:** el CHECK constraint en `fire_episodes.status` ya incluye `'closed'` según el schema de BD (`flujo_ingesta_procesamiento.md` sección 3.4, línea: `CHECK: active, monitoring, extinct, closed`). No requiere ALTER TABLE adicional. El CHECK constraint en `fire_events.status` solo tiene `active, monitoring, extinct` — los eventos nunca llegan a `closed`.

#### 7c — Insertar `event_extinction_window_hours` en `system_parameters`

```sql
INSERT INTO system_parameters (param_key, param_value)
VALUES ('event_extinction_window_hours', '{"unit": "hours", "value": 336}')
ON CONFLICT (param_key) DO NOTHING;
```

**Orden de ejecución de las migrations:**
1. `ALTER TABLE fire_episodes ADD COLUMN extinct_at` (sin downtime)
2. `UPDATE fire_episodes SET extinct_at = updated_at WHERE status = 'extinct'` (backfill)
3. `INSERT INTO system_parameters` (event_extinction_window_hours)
4. Actualizar `app/models/episode.py` y `app/schemas/fire.py` → deploy

---

### EVT-004 — Alineación de `resolve_fire_status` (opcional)

**Archivo:** `app/services/fire_service.py`, línea 139

**Estado actual:**

```python
def resolve_fire_status(self, fire: FireEvent) -> FireStatus:
    if fire.status:                          # ← Prioriza status de la DB
        try:
            return FireStatus(fire.status)
        except ValueError:
            pass

    now = datetime.now(timezone.utc)         # ← Fallback: recálculo dinámico
    reference_time = self._event_reference_time(fire)
    if reference_time:
        # ... lógica temporal ...
    return FireStatus.EXTINCT
```

**Problema de dualidad:** el bloque de fallback (líneas 146-159) recalcula el estado cuando `fire.status` es `None` o inválido. Esto crea dos fuentes de verdad: el status persistido y el status calculado al vuelo. Con EVT-001 activo, el status siempre estará persistido y el fallback nunca se alcanzará en condiciones normales.

**Cambio propuesto:**

```python
def resolve_fire_status(self, fire: FireEvent) -> FireStatus:
    if fire.status:
        try:
            return FireStatus(fire.status)
        except ValueError:
            pass
    return FireStatus.ACTIVE
```

Si `fire.status` es `None` o inválido, retornar `ACTIVE` (el default de creación en `detection_clustering_service.py` línea 320). El task batch EVT-001 se encargará de transicionarlo en la próxima ejecución.

**Clasificación:** opcional, riesgo bajo. Con EVT-001 operando, este cambio solo afecta el edge case de un evento recién creado que se consulta antes de la primera ejecución del task (ventana de hasta 30 min entre 01:00 y 01:30 UTC).

**Impacto en `export_service.py`:** si se aplica EVT-004, la copia duplicada en `app/services/export_service.py:54` también debe alinearse (ver deuda DT-001).

---

### EVT-005 — Script one-shot para corregir eventos existentes

**Archivo:** `scripts/maintenance/fix_event_statuses_oneshot.py`

Aplica la misma lógica que EVT-001 (incluyendo el check espacial) a los eventos que nunca transitaron de estado. El archivo ya existe en el repo; debe actualizarse para incorporar el spatial check en el paso `monitoring → extinct`.

**Lógica actualizada (reemplazar el contenido del archivo):**

```python
"""
One-shot script: corrige fire_events con status estatico.
Aplica la misma logica que el task EVT-001 (update_event_statuses),
incluyendo el check espacial de 2km para monitoring → extinct.

Uso:
    python scripts/maintenance/fix_event_statuses_oneshot.py            # ejecuta
    python scripts/maintenance/fix_event_statuses_oneshot.py --dry-run  # solo muestra

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md (EVT-005)
"""

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.episode_flow_parameters import load_canonical_episode_flow_parameters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SQL_TO_MONITORING = """
    UPDATE fire_events
       SET status = 'monitoring', updated_at = NOW()
     WHERE status = 'active'
       AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
       AND COALESCE(last_seen_at, end_date, start_date)
           < NOW() - MAKE_INTERVAL(hours => :active_window)
"""

SQL_TO_EXTINCT = """
    UPDATE fire_events
       SET status = 'extinct', updated_at = NOW()
     WHERE id IN (
         SELECT fe.id
           FROM fire_events fe
          WHERE fe.status = 'monitoring'
            AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
            AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
                < NOW() - MAKE_INTERVAL(hours => :extinct_window)
            AND NOT EXISTS (
                SELECT 1
                  FROM fire_detections fd
                 WHERE ST_DWithin(
                           fd.location::geography,
                           fe.centroid,
                           2000
                       )
                   AND fd.detected_at
                       > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
            )
     )
"""

SQL_COUNT_TO_MONITORING = """
    SELECT COUNT(*) FROM fire_events
     WHERE status = 'active'
       AND COALESCE(last_seen_at, end_date, start_date) IS NOT NULL
       AND COALESCE(last_seen_at, end_date, start_date)
           < NOW() - MAKE_INTERVAL(hours => :active_window)
"""

SQL_COUNT_TO_EXTINCT = """
    SELECT COUNT(*) FROM (
        SELECT fe.id
          FROM fire_events fe
         WHERE fe.status = 'monitoring'
           AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date) IS NOT NULL
           AND COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
               < NOW() - MAKE_INTERVAL(hours => :extinct_window)
           AND NOT EXISTS (
               SELECT 1
                 FROM fire_detections fd
                WHERE ST_DWithin(
                          fd.location::geography,
                          fe.centroid,
                          2000
                      )
                  AND fd.detected_at
                      > COALESCE(fe.last_seen_at, fe.end_date, fe.start_date)
           )
    ) sub
"""


def print_distribution(db):
    rows = db.execute(
        text("SELECT status, COUNT(*) AS cnt FROM fire_events GROUP BY status ORDER BY cnt DESC")
    ).fetchall()
    logger.info("Distribucion de fire_events.status:")
    for row in rows:
        logger.info("  %-12s: %d", row[0], row[1])


def main():
    parser = argparse.ArgumentParser(description="Corrige fire_events.status estaticos (EVT-005)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--active-window", type=int, default=None)
    parser.add_argument("--extinct-window", type=int, default=None)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        params = load_canonical_episode_flow_parameters(db)
        active_window = args.active_window or int(params.get("event_monitoring_window_hours", 168))
        extinct_window = args.extinct_window or int(params.get("event_extinction_window_hours", 336))

        logger.info("active_window  = %d h (active → monitoring)", active_window)
        logger.info("extinct_window = %d h (monitoring → extinct, + check espacial 2km)", extinct_window)

        print_distribution(db)

        if args.dry_run:
            n_monitoring = db.execute(text(SQL_COUNT_TO_MONITORING), {"active_window": active_window}).scalar()
            n_extinct = db.execute(text(SQL_COUNT_TO_EXTINCT), {"extinct_window": extinct_window}).scalar()
            logger.info("[DRY-RUN] Pasarian a monitoring: %d", n_monitoring)
            logger.info("[DRY-RUN] Pasarian a extinct:    %d", n_extinct)
            logger.info("[DRY-RUN] No se realizaron cambios.")
            return

        db.execute(text("SET statement_timeout = '300s'"))
        t0 = time.monotonic()

        r1 = db.execute(text(SQL_TO_MONITORING), {"active_window": active_window})
        logger.info("Actualizados a monitoring: %d", r1.rowcount)

        r2 = db.execute(text(SQL_TO_EXTINCT), {"extinct_window": extinct_window})
        logger.info("Actualizados a extinct:    %d", r2.rowcount)

        db.commit()
        logger.info("COMMIT exitoso en %d ms.", int((time.monotonic() - t0) * 1000))

        print_distribution(db)

    except Exception:
        db.rollback()
        logger.exception("Error. Se realizo rollback.")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

**Uso:**

```bash
# Ver qué cambiaría (sin modificar datos)
PYTHONPATH=. python scripts/maintenance/fix_event_statuses_oneshot.py --dry-run

# Ejecutar la corrección
PYTHONPATH=. python scripts/maintenance/fix_event_statuses_oneshot.py
```

**Nota:** el `--dry-run` con spatial check es más lento que la versión anterior porque ejecuta la subquery con `ST_DWithin`. En entornos con muchos eventos en monitoring, puede tardar 10–30 s.

---

### EVT-006 — Task `episode_closer` y simplificación de `_resolve_episode_status`

#### 6a — Simplificación de `_resolve_episode_status`

**Archivo:** `app/services/episode_service.py`, línea 162

**Problema actual:** la función usa una ventana temporal propia del episodio (`episode_temporal_window_hours = 720h`) para decidir entre `monitoring` y `extinct`. Esta ventana es incorrecta según la lógica canónica: el estado del episodio debe heredarse directamente del estado persistido de sus eventos, sin ventana temporal adicional.

**Cambio requerido en `_resolve_episode_status`:**

```python
# ANTES (lógica incorrecta: usa ventana temporal propia del episodio)
def _resolve_episode_status(self, event_statuses, last_seen_at, start_date, window_hours=None):
    if "active" in event_statuses:
        return "active"
    # ... cálculo de elapsed vs window_hours ...
    if elapsed >= window:
        return "extinct"
    return "monitoring"

# DESPUÉS (lógica correcta: hereda estado de eventos)
def _resolve_episode_status(self, event_statuses, last_seen_at=None, start_date=None, window_hours=None):
    if "active" in event_statuses:
        return "active"
    if "monitoring" in event_statuses:
        return "monitoring"
    return "extinct"
```

Los parámetros `last_seen_at`, `start_date` y `window_hours` quedan como argumentos opcionales para compatibilidad de firma, pero ya no se usan en la lógica principal.

**Adicionalmente**, cuando el episodio transiciona a `extinct` en `update_episode_metrics`, debe persistirse `extinct_at`:

```python
# En la query UPDATE de update_episode_metrics (episode_service.py):
# Agregar extinct_at = CASE WHEN nuevo_status = 'extinct' AND extinct_at IS NULL THEN NOW() END
```

#### 6b — Nuevo task `episode_closer`

**Archivo nuevo:** `workers/tasks/episode_closer_task.py`

Promueve episodios de `extinct` a `closed` cuando han permanecido 30 días en estado extinct (basado en `extinct_at`).

```python
"""
Episode closer task (EVT-006).

Promueve fire_episodes de 'extinct' a 'closed' cuando extinct_at + 30d < NOW().
Los episodios 'closed' dejan de mostrarse en el carrusel/mapa y solo
aparecen en la grilla de historicos.

Prerequisitos:
  - fire_episodes.extinct_at (EVT-007 migration)
  - FireStatus.CLOSED en app/schemas/fire.py (EVT-007)

Fuente de verdad: docs/Carrusel fix/fix_event_status_lifecycle.md (EVT-006)
"""

import logging
import time

from sqlalchemy import text

from app.db.session import SessionLocal
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

CLOSE_AFTER_DAYS = 30


@celery_app.task(
    bind=True,
    name="workers.tasks.episode_closer_task.close_extinct_episodes",
    queue="analysis",
    max_retries=3,
)
def close_extinct_episodes(self):
    """
    Promueve episodios extinct → closed cuando extinct_at + 30d < NOW().

    Solo actua sobre episodios con extinct_at NOT NULL (seteado por
    update_episode_metrics cuando el episodio transiciona a 'extinct').
    """
    t0 = time.monotonic()
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                UPDATE fire_episodes
                   SET status = 'closed',
                       updated_at = NOW()
                 WHERE status = 'extinct'
                   AND extinct_at IS NOT NULL
                   AND extinct_at < NOW() - INTERVAL ':days days'
            """.replace(":days days", f"{CLOSE_AFTER_DAYS} days")),
        )

        db.commit()

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        outcome = {
            "success": True,
            "episodes_closed": result.rowcount,
            "close_after_days": CLOSE_AFTER_DAYS,
            "elapsed_ms": elapsed_ms,
        }
        logger.info("Episode closer complete: %s", outcome)
        return outcome

    except Exception as exc:
        db.rollback()
        logger.exception("Episode closer failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
    finally:
        db.close()
```

**Registro en `workers/celery_app.py`:**

```python
# En task_routes:
'workers.tasks.episode_closer_task.close_extinct_episodes': {'queue': 'analysis'},

# En beat_schedule (después de carousel-daily a las 03:00):
'close-extinct-episodes-daily': {
    'task': 'workers.tasks.episode_closer_task.close_extinct_episodes',
    'schedule': crontab(hour=5, minute=0),  # 05:00 UTC (después de cleanup)
    'options': {'queue': 'analysis'},
},
```

**Posición en el beat schedule completo post-cambio:**

| Hora UTC | Task | Cola |
|----------|------|------|
| 00:00 | `download_firms_daily` | ingestion |
| 01:00 | `cluster_detections` | clustering |
| 01:30 | `update_event_statuses` | clustering |
| 02:00 | `cluster_fire_episodes_pipeline` | clustering |
| 03:00 | `generate_carousel` | analysis |
| 04:00 | `cleanup_expired_assets` | analysis |
| **05:00** | **`close_extinct_episodes`** | **analysis** |
| 08:00 | `generate_closure_reports` | analysis |

---

## 4. Validación post-implementación

### 4.1 Queries de verificación

```sql
-- V1: Distribución de estados de eventos (debe mostrar active, monitoring y extinct)
SELECT status, COUNT(*) AS cnt
FROM fire_events
GROUP BY status
ORDER BY status;

-- V2: Eventos active que realmente tienen actividad reciente (< 168h)
-- Debe ser > 0 solo si hay detecciones recientes
SELECT COUNT(*)
FROM fire_events
WHERE status = 'active'
  AND COALESCE(last_seen_at, end_date, start_date) >= NOW() - INTERVAL '168 hours';

-- V3: Coherencia episodio-evento
-- Episodios active sin eventos active (debe ser 0)
SELECT e.id, e.status AS ep_status,
       ARRAY_AGG(DISTINCT fe.status) AS event_statuses
FROM fire_episodes e
JOIN fire_episode_events fee ON fee.episode_id = e.id
JOIN fire_events fe ON fe.id = fee.event_id
WHERE e.status = 'active'
GROUP BY e.id, e.status
HAVING NOT ('active' = ANY(ARRAY_AGG(fe.status)));

-- V4: Episodios monitoring sin eventos monitoring ni active (debe ser 0)
SELECT e.id, e.status AS ep_status,
       ARRAY_AGG(DISTINCT fe.status) AS event_statuses
FROM fire_episodes e
JOIN fire_episode_events fee ON fee.episode_id = e.id
JOIN fire_events fe ON fe.id = fee.event_id
WHERE e.status = 'monitoring'
GROUP BY e.id, e.status
HAVING NOT ('active' = ANY(ARRAY_AGG(fe.status)))
   AND NOT ('monitoring' = ANY(ARRAY_AGG(fe.status)));
```

### 4.2 Test funcional (secuencia)

1. Ejecutar `fix_event_statuses_oneshot.py --dry-run` — verificar conteos
2. Ejecutar `fix_event_statuses_oneshot.py` — verificar conteos reales
3. Ejecutar `recalculate_episodes.py --skip-carousel` — recalcular episodios con estados frescos
4. Ejecutar queries V1-V4
5. Verificar beat schedule con `celery -A workers.celery_app inspect conf | grep beat`

---

## 5. Deudas técnicas identificadas

### DT-001 — `export_service.py` duplica `resolve_fire_status`

**Archivos afectados:**
- `app/services/fire_service.py:139` — `resolve_fire_status()` (original)
- `app/services/export_service.py:54` — `_resolve_fire_status()` (copia)

**Descripción:** `ExportService` tiene su propia copia de `_resolve_fire_status`, `_event_reference_time`, `_event_monitoring_window_hours` y `_episode_flow_params` (líneas 35-74). Es código idéntico al de `FireService`.

**Riesgo:** si se modifica la lógica de estados en `fire_service.py` (como EVT-004), `export_service.py` queda desalineado.

**Solución propuesta:** reemplazar los 4 métodos duplicados por:
```python
from app.services.fire_service import FireService

# En ExportService.__init__:
self._fire_svc = FireService(db)

# En lugar de self._resolve_fire_status(fire):
self._fire_svc.resolve_fire_status(fire)
```

**Prioridad:** media. No bloquea EVT-001.

---

### DT-002 — `episode_inactive_grace_hours` obsoleto en `system_parameters`

**Valor en BD:** `episode_inactive_grace_hours = {"value": 72}`

**Problema:** no existe ningún archivo Python que lea este parámetro. El método `_resolve_inactive_grace_hours` en `episode_service.py` (línea 121) lee `episode_temporal_window_hours` (720h), no `episode_inactive_grace_hours`. Los 72h son un vestigio de la versión pre-fix del código (ver causa raíz documentada en la auditoría previa: el default era 72 y causaba que episodios con `last_seen_at > 3 días` fueran marcados como `extinct` prematuramente).

**Solución propuesta:** eliminar la fila de `system_parameters`:
```sql
DELETE FROM system_parameters WHERE param_key = 'episode_inactive_grace_hours';
```

**Prioridad:** baja. No afecta funcionalidad actual.

---

### DT-003 — Eventos históricos 2015-2024 sin episodio

**Datos:** 33,329 eventos creados entre 2015 y 2024 no tienen entrada en `fire_episode_events`. El sistema de episodios se implementó en 2025 y solo procesa eventos de los últimos 90 días (`days_back=90` en `cluster_fire_episodes_pipeline`).

**Impacto:** datos huérfanos en `fire_events`. No bloquea el pipeline actual. Los eventos están todos en `extinct` y no aparecen en la UI.

**Solución propuesta (si se necesita):** ejecutar `ClusteringService.run_clustering(days_back=3650)` una vez para agrupar retroactivamente. Requiere evaluación de rendimiento (36K eventos con búsqueda espacial).

**Prioridad:** baja. Cosmético.

---

### DT-004 — Columna `detection_hash` documentada pero inexistente

**Referencia en documentación:** `flujo_ingesta_procesamiento.md` menciona `detection_hash` para deduplicación.

**Realidad en BD:** la columna no existe en `fire_detections`. La deduplicación se hace por pre-filtrado Python en `load_firms_incremental.py` usando una llave natural compuesta (`latitude + longitude + detected_at + satellite + confidence`).

**Solución propuesta:** actualizar la documentación para reflejar el mecanismo real de deduplicación, o crear la columna como índice materializado si se necesita deduplicación a nivel DB.

**Prioridad:** baja. Documental.

---

## 6. Orden de ejecución recomendado

```
── FASE 1: Schema y parámetros (prerequisitos) ──────────────────────────────
1. EVT-007a  ALTER TABLE fire_episodes ADD COLUMN extinct_at
             + UPDATE backfill extinct_at = updated_at
2. EVT-007b  INSERT system_parameters: event_extinction_window_hours = 336
3. EVT-007c  Actualizar app/models/episode.py + app/schemas/fire.py + deploy

── FASE 2: Corrección de datos históricos ───────────────────────────────────
4. EVT-005   --dry-run                  → verificar conteos con spatial check
5. EVT-005   (ejecución real)           → corregir eventos existentes

── FASE 3: Activar automatización ───────────────────────────────────────────
6. EVT-001   Actualizar workers/tasks/event_status_task.py (SQL con spatial check)
7. EVT-003   Ya implementado en beat schedule (EVT-002 ya ejecutado)
8. EVT-006a  Simplificar _resolve_episode_status en episode_service.py
9. EVT-006b  Crear workers/tasks/episode_closer_task.py
10. EVT-006c Agregar route + beat entry en workers/celery_app.py (05:00 UTC)
11. EVT-004  (opcional) Simplificar resolve_fire_status en fire_service.py

── FASE 4: Validación ───────────────────────────────────────────────────────
12. Recalcular episodios → recalculate_episodes.py --skip-carousel
13. Validación V1-V5     → confirmar coherencia de estados
```

---

## 7. Archivos modificados (resumen)

| Archivo | Tipo | Tarea |
|---------|------|-------|
| `workers/tasks/event_status_task.py` | Nuevo | EVT-001 |
| `workers/celery_app.py` | Modificado | EVT-002, EVT-006c |
| `app/services/episode_flow_parameters.py` | Modificado | EVT-003 |
| `app/services/fire_service.py` | Modificado (opcional) | EVT-004 |
| `scripts/maintenance/fix_event_statuses_oneshot.py` | Modificado | EVT-005 |
| `app/services/episode_service.py` | Modificado | EVT-006a |
| `workers/tasks/episode_closer_task.py` | Nuevo | EVT-006b |
| `app/models/episode.py` | Modificado | EVT-007a |
| `app/schemas/fire.py` | Modificado | EVT-007b |

**SQL de migración requerido (ejecutar manualmente o via script de migration):**

```sql
-- EVT-007a: columna extinct_at en episodios
ALTER TABLE fire_episodes ADD COLUMN IF NOT EXISTS extinct_at TIMESTAMPTZ;
UPDATE fire_episodes SET extinct_at = updated_at WHERE status = 'extinct' AND extinct_at IS NULL;

-- EVT-007b: parámetro de ventana de extinción
INSERT INTO system_parameters (param_key, param_value)
VALUES ('event_extinction_window_hours', '{"unit": "hours", "value": 336}')
ON CONFLICT (param_key) DO NOTHING;
```

---

---

## 8. Geo-enrichment: provincia y áreas protegidas (ENR-001 a ENR-003)

### Contexto

Los scripts `scripts/enrich_location.py` y `scripts/cross_fire_protected_areas.py` existían como herramientas manuales independientes. Su funcionalidad ya estaba completamente replicada en `workers/tasks/geo_enrichment.py` como el task `enrich_recent_fire_events`. Sin embargo, el task estaba ubicado como **paso 2 del chain de episode aggregation** (02:00 UTC), lo que significaba que los eventos se enriquecían **después** de que `cluster_fire_episodes` ya los había usado para crear episodios.

### Problema de timing

```
ANTES (incorrecto):
  01:00  cluster_detections        → fire_events creados (sin province, sin legal)
  02:00  cluster_fire_episodes     → episodios creados con eventos sin enriquecer
            └── enrich_recent_fire_events → province + legal asignados (tarde)

DESPUÉS (corregido):
  01:00  cluster_detections        → fire_events creados
  01:30  update_event_statuses     → statuses actualizados
  01:45  enrich_recent_fire_events → province + has_legal_analysis asignados  ← MOVIDO
  02:00  cluster_fire_episodes     → episodios con eventos ya enriquecidos ✓
```

### ENR-001 — Beat entry independiente a las 01:45 UTC

**Archivo modificado:** `workers/celery_app.py`

```python
'enrich-events-daily': {
    'task': 'workers.tasks.geo_enrichment.enrich_recent_fire_events',
    'schedule': crontab(hour=1, minute=45),  # 01:45 UTC
    'kwargs': {'lookback_hours': 72, 'max_events': 5000},
    'options': {'queue': 'analysis'},
},
```

**Parámetros:**
- `lookback_hours=72`: ventana de 3 días para cubrir eventos de los últimos días más el nuevo batch de 01:00, con margen ante retries
- `max_events=5000`: consistente con el resto del pipeline

**Cola:** `analysis` (consume `worker-analysis`, que ya existe y tiene las variables de entorno GEE)

### ENR-002 — Remover enrichment del chain de episodios

**Archivo modificado:** `workers/tasks/clustering_task.py`

El chain en `cluster_fire_episodes_pipeline` queda simplificado a un único step:

```python
workflow = chain(
    cluster_fire_episodes.s(days_back=days_back, max_events=max_events),
)
```

El parámetro `geo_lookback_hours` fue eliminado de la firma y del beat entry correspondiente. Ya no tiene uso.

### ENR-003 — Scripts legacy movidos

Los siguientes archivos fueron movidos a `scripts/legacy/` ya que su funcionalidad está completamente cubierta por `workers/tasks/geo_enrichment.py`:

| Script original | Nuevo path | Motivo |
|---|---|---|
| `scripts/enrich_location.py` | `scripts/legacy/legacy_enrich_location.py` | Reemplazado por `_update_missing_provinces()` en `geo_enrichment.py` |
| `scripts/cross_fire_protected_areas.py` | `scripts/legacy/legacy_cross_fire_protected_areas.py` | Reemplazado por `_upsert_protected_area_intersections()` en `geo_enrichment.py` |

**Para ejecución manual puntual** (batch completo o reprocessamiento), usar directamente el task:

```bash
# Usando Celery (en entorno con workers activos)
celery -A workers.celery_app call workers.tasks.geo_enrichment.enrich_recent_fire_events \
  --kwargs='{"lookback_hours": 8760, "max_events": 50000}'

# O via Django shell / script Python directamente
PYTHONPATH=. python -c "
from app.db.session import SessionLocal
from workers.tasks.geo_enrichment import (
    _select_candidate_event_ids,
    _update_missing_provinces,
    _upsert_protected_area_intersections,
    _mark_events_as_legally_analyzed,
)
# ... ejecutar funciones privadas directamente
"
```

### Pipeline completo post-cambios ENR

| Hora UTC | Task | Cola | Descripción |
|----------|------|------|-------------|
| 00:00 | `download_firms_daily` | ingestion | Descarga FIRMS → `fire_detections` |
| 01:00 | `cluster_detections` | clustering | ST-DBSCAN → `fire_events` |
| 01:30 | `update_event_statuses` | clustering | Persiste statuses (EVT-001) |
| **01:45** | **`enrich_recent_fire_events`** | **analysis** | **Province + áreas protegidas** |
| 02:00 | `cluster_fire_episodes_pipeline` | clustering | Episodios con eventos enriquecidos |
| 03:00 | `generate_carousel` | analysis | Thumbnails GEE |
| 04:00 | `cleanup_expired_assets` | analysis | Limpieza de assets |
| **05:00** | **`close_extinct_episodes`** | **analysis** | **Extinct → Closed (EVT-006)** |
| 08:00 | `generate_closure_reports` | analysis | PDFs de cierre |

---

*Documento generado como fuente de verdad para la corrección del ciclo de vida de fire_events. Última actualización: 2026-02-25.*
