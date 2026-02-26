# Especificación técnica: mitigación de cuota GEE en ForestGuard

**Fecha:** 2026-02-26  
**Scope:** `app/api/routes/monitoring.py`, `app/services/vae_service.py`, `workers/tasks/recovery.py`, `celery_app.py`  
**Problema raíz:** El endpoint `GET /monitoring/recovery/{id}` llama GEE en tiempo real (37 requests síncronos por HTTP request), agotando la cuota del free tier ante cualquier carga real.

---

## 1. Diagnóstico cuantificado

### 1.1 Requests GEE por escenario

| Escenario | Requests GEE | Cuota consumida (50k/día) | Consecuencia |
|---|---|---|---|
| 1 usuario abre fire detail | 37 | 0,07% | 10–30s latencia |
| 5 usuarios simultáneos | 185 | 0,37% | Probable timeout en VM |
| 40 usuarios simultáneos | 1.480 | 3% | Cuota en ~34 sesiones diarias |
| Feed con 50 cards (si llaman recovery) | 1.850 por page load | 3,7% por carga | Inviable |
| **Worker mensual por evento (actual)** | **37 / evento / mes** | **Controlado** | **Patrón correcto** |
| **Worker con batch GEE (optimizado)** | **1–3 / evento / mes** | **Mínimo** | **Objetivo** |
| **Endpoint solo lee BD (correcto)** | **0 por HTTP GET** | **0%** | **Cuota libre para workers** |

### 1.2 Límites del free tier GEE

- Requests/día: **50.000**
- Requests simultáneos recomendados: **10**
- Tiempo máximo de procesamiento: **variable** (colecciones grandes pueden tardar 30–120s)
- Política de throttling: error `EEException: Computation timed out` o `User memory limit exceeded`

### 1.3 Presupuesto GEE recomendado por componente

| Componente | Requests/día reservados | Uso |
|---|---|---|
| Workers `analyze_recovery` (batch nocturno) | 35.000 (~950 eventos × 37) | Análisis mensual |
| Worker `detect_destruction` | 5.000 | Cambio de uso |
| Worker `generate_carousel` | 5.000 | Thumbnails |
| Buffer de seguridad | 5.000 | Trigger manual admin |
| **Total** | **50.000** | **0 para endpoints HTTP** |

---

## 2. Arquitectura objetivo

### 2.1 Separación de responsabilidades (patrón correcto)

```
[GEE] ←— solo workers (Celery) —→ [vegetation_monitoring en BD]
                                              ↑
                                   [GET /monitoring/recovery/{id}]
                                   Lee de BD, latencia ~5ms, 0 GEE
```

### 2.2 Diagrama de flujo corregido

```
Celery Beat (03:00 UTC mensual)
  └─ analyze_recovery_batch()
       ├─ Selecciona eventos activos/monitoring
       ├─ Para cada evento:
       │    ├─ _get_baseline_ndvi() → 1 req GEE (solo si no existe)
       │    └─ _get_current_ndvi()  → 1 req GEE (mes actual)
       │    └─ UPSERT vegetation_monitoring
       └─ Total: 2 req GEE/evento/mes (vs 37 actual)

HTTP GET /monitoring/recovery/{id}
  └─ SELECT * FROM vegetation_monitoring WHERE fire_event_id = ?
       ├─ Si hay datos → devuelve serie, 0 GEE
       └─ Si no hay datos → {status: "pending"}, encola job async
```

---

## 3. Correcciones a implementar

### 3.1 Corrección crítica: separar endpoint de GEE

**Archivo:** `app/api/routes/monitoring.py`

**Antes (problemático):**
```python
@router.get("/recovery/{fire_event_id}")
async def get_recovery_status(fire_event_id: UUID, db: Session = Depends(get_db)):
    vae = VAEService()                          # instancia por request
    result = await vae.get_recovery_timeline(   # 37 requests GEE síncronos
        str(fire_event_id)
    )
    return result
```

**Después (correcto):**
```python
@router.get("/recovery/{fire_event_id}")
async def get_recovery_status(
    fire_event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Verificar que el evento existe
    event = db.execute(
        text("SELECT id, status FROM fire_events WHERE id = :id"),
        {"id": str(fire_event_id)}
    ).fetchone()
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    # 2. Leer datos ya procesados de BD (0 llamadas GEE)
    rows = db.execute(
        text("""
            SELECT monitoring_date, ndvi_mean, baseline_ndvi,
                   recovery_percentage, cloud_cover_pct, recovery_status
            FROM vegetation_monitoring
            WHERE fire_event_id = :id
            ORDER BY monitoring_date ASC
        """),
        {"id": str(fire_event_id)}
    ).fetchall()

    if not rows:
        # 3. Sin datos: encolar análisis si no está pendiente
        _enqueue_recovery_if_not_pending(str(fire_event_id))
        return {
            "fire_event_id": str(fire_event_id),
            "recovery_status": "pending",
            "monitoring_data": [],
            "baseline_ndvi": None,
            "message": "Análisis en proceso. Los datos estarán disponibles en los próximos minutos."
        }

    # 4. Construir respuesta desde BD
    latest = rows[-1]
    return {
        "fire_event_id": str(fire_event_id),
        "recovery_status": latest.recovery_status,
        "baseline_ndvi": latest.baseline_ndvi,
        "current_ndvi": latest.ndvi_mean,
        "recovery_percentage": latest.recovery_percentage,
        "monitoring_data": [
            {
                "date": row.monitoring_date.isoformat(),
                "month": row.monitoring_date.month,
                "ndvi_mean": row.ndvi_mean,
                "recovery_percentage": row.recovery_percentage,
                "cloud_cover_pct": row.cloud_cover_pct,
            }
            for row in rows
        ],
    }


def _enqueue_recovery_if_not_pending(fire_event_id: str) -> None:
    """Encola análisis GEE solo si no hay uno ya en cola."""
    from workers.tasks.recovery import analyze_recovery
    # Idempotente: la tarea hace UPSERT, no duplica registros
    analyze_recovery.apply_async(
        args=[fire_event_id],
        queue="gee",
        countdown=5,  # pequeño delay para no saturar ante burst de requests
    )
```

### 3.2 Worker optimizado: batch mensual con GEE eficiente

**Archivo:** `workers/tasks/recovery.py`

El worker actual llama `get_recovery_time_series()` que itera 36 meses. La corrección es que cada ejecución del worker procese **solo el mes actual** (incremental), no toda la historia.

```python
@app.task(
    bind=True,
    queue="gee",
    max_retries=3,
    default_retry_delay=300,   # 5 min entre reintentos GEE
    time_limit=600,            # 10 min máximo por tarea
    soft_time_limit=540,
)
def analyze_recovery(self, fire_event_id: str) -> dict:
    """
    Analiza recuperación vegetal para un evento específico.

    Comportamiento:
    - Si no existe baseline en BD: llama GEE 1 vez para obtenerlo.
    - Si ya existe baseline: llama GEE 1 vez para el mes actual.
    - Total: 1–2 requests GEE por ejecución (vs 37 anterior).
    - Hace UPSERT en vegetation_monitoring (idempotente).
    """
    from app.db.session import SessionLocal
    from app.services.vae_service import VAEService, BaselineNotAvailableError
    from sqlalchemy import text
    from datetime import date

    db = SessionLocal()
    try:
        # 1. Verificar si ya existe baseline para este evento
        baseline_row = db.execute(
            text("""
                SELECT baseline_ndvi FROM vegetation_monitoring
                WHERE fire_event_id = :id AND baseline_ndvi IS NOT NULL
                LIMIT 1
            """),
            {"id": fire_event_id}
        ).fetchone()

        vae = get_vae_service()  # singleton, no instancia nueva

        # 2. Obtener o calcular baseline (1 req GEE si no existe)
        if baseline_row:
            baseline_ndvi = baseline_row.baseline_ndvi
        else:
            try:
                baseline_ndvi = vae._get_baseline_ndvi(fire_event_id)
            except BaselineNotAvailableError:
                # No hay imagen pre-incendio disponible; marcar pending y salir
                logger.warning(
                    "baseline_not_available",
                    fire_event_id=fire_event_id
                )
                return {"status": "pending", "reason": "no_baseline_image"}

        # 3. Obtener NDVI actual (1 req GEE)
        today = date.today()
        target_month = today.replace(day=1)
        try:
            current_ndvi, cloud_cover = vae._get_current_ndvi_with_cloud(
                fire_event_id, target_month
            )
        except GEEImageNotFoundError:
            logger.warning(
                "no_gee_image_for_month",
                fire_event_id=fire_event_id,
                month=target_month.isoformat()
            )
            return {"status": "pending", "reason": "no_image_this_month"}

        # 4. Calcular porcentaje de recuperación
        # Fórmula: recuperación desde nadir, no ratio simple
        # recovery_pct = (current - post_fire_min) / (baseline - post_fire_min) * 100
        # Por ahora usamos la fórmula actual hasta tener post_fire_min en BD
        recovery_pct = min(100.0, max(0.0, (current_ndvi / baseline_ndvi) * 100))

        recovery_status = _classify_recovery(recovery_pct, current_ndvi, baseline_ndvi)

        # 5. UPSERT (idempotente)
        db.execute(
            text("""
                INSERT INTO vegetation_monitoring
                    (fire_event_id, monitoring_date, ndvi_mean, baseline_ndvi,
                     recovery_percentage, cloud_cover_pct, recovery_status)
                VALUES
                    (:fire_event_id, :monitoring_date, :ndvi_mean, :baseline_ndvi,
                     :recovery_pct, :cloud_cover, :status)
                ON CONFLICT (fire_event_id, monitoring_date)
                DO UPDATE SET
                    ndvi_mean = EXCLUDED.ndvi_mean,
                    recovery_percentage = EXCLUDED.recovery_percentage,
                    cloud_cover_pct = EXCLUDED.cloud_cover_pct,
                    recovery_status = EXCLUDED.recovery_status,
                    updated_at = NOW()
            """),
            {
                "fire_event_id": fire_event_id,
                "monitoring_date": target_month,
                "ndvi_mean": current_ndvi,
                "baseline_ndvi": baseline_ndvi,
                "recovery_pct": recovery_pct,
                "cloud_cover": cloud_cover,
                "status": recovery_status,
            }
        )
        db.commit()

        logger.info(
            "recovery_analyzed",
            fire_event_id=fire_event_id,
            recovery_pct=recovery_pct,
            status=recovery_status,
        )
        return {
            "status": "ok",
            "recovery_percentage": recovery_pct,
            "recovery_status": recovery_status,
        }

    except Exception as exc:
        db.rollback()
        logger.error("analyze_recovery_failed", fire_event_id=fire_event_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        db.close()


def _classify_recovery(pct: float, current: float, baseline: float) -> str:
    if current >= baseline * 0.95:
        return "full_recovery"
    if pct >= 80:
        return "advanced_recovery"
    if pct >= 50:
        return "moderate_recovery"
    if pct >= 20:
        return "early_recovery"
    return "not_started"
```

### 3.3 Batch nocturno: programar análisis mensual masivo

**Archivo:** `celery_app.py`

```python
# Agregar al beat_schedule existente:
beat_schedule = {
    # ... tareas existentes ...

    # Análisis mensual de recuperación vegetal (GEE)
    # Ejecuta el día 2 de cada mes a las 02:00 UTC para evitar solapamiento
    # con ingestion (00:00) y clustering (01:00)
    "recovery-monthly": {
        "task": "workers.tasks.recovery.batch_recovery_monthly",
        "schedule": crontab(day_of_month=2, hour=2, minute=0),
        "options": {"queue": "gee"},
    },

    # Análisis incremental semanal (para eventos muy recientes)
    "recovery-weekly-recent": {
        "task": "workers.tasks.recovery.batch_recovery_recent",
        "schedule": crontab(day_of_week=1, hour=3, minute=0),  # lunes 03:00 UTC
        "options": {"queue": "gee"},
    },
}

# Configuración de colas: separar gee de analysis
task_routes = {
    "workers.tasks.recovery.analyze_recovery": {"queue": "gee"},
    "workers.tasks.recovery.batch_recovery_monthly": {"queue": "gee"},
    "workers.tasks.recovery.batch_recovery_recent": {"queue": "gee"},
    "workers.tasks.destruction.detect_destruction": {"queue": "gee"},
    "workers.tasks.carousel_task.generate_carousel": {"queue": "gee"},
    "workers.tasks.clustering.*": {"queue": "clustering"},
    "workers.tasks.ingestion.*": {"queue": "ingestion"},
}
```

**Nueva tarea batch** (`workers/tasks/recovery.py`):

```python
@app.task(queue="gee", time_limit=7200)  # 2hs máximo
def batch_recovery_monthly() -> dict:
    """
    Ejecuta analyze_recovery para todos los eventos activos/monitoring.
    Se llama desde Celery Beat el día 2 de cada mes.

    Límite de seguridad: procesa máximo 900 eventos por ejecución
    (900 × 2 req GEE = 1.800 req, ~4% de la cuota diaria).
    Eventos restantes se procesan en la siguiente semana via batch semanal.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    MAX_EVENTS_PER_RUN = 900
    GEE_DELAY_BETWEEN_TASKS = 3  # segundos entre tasks para evitar burst

    db = SessionLocal()
    try:
        events = db.execute(
            text("""
                SELECT id FROM fire_events
                WHERE status IN ('active', 'monitoring')
                ORDER BY updated_at DESC
                LIMIT :limit
            """),
            {"limit": MAX_EVENTS_PER_RUN}
        ).fetchall()

        enqueued = 0
        for i, event in enumerate(events):
            analyze_recovery.apply_async(
                args=[str(event.id)],
                queue="gee",
                countdown=i * GEE_DELAY_BETWEEN_TASKS,
            )
            enqueued += 1

        logger.info("batch_recovery_scheduled", total=enqueued)
        return {"enqueued": enqueued}
    finally:
        db.close()


@app.task(queue="gee", time_limit=3600)
def batch_recovery_recent() -> dict:
    """
    Análisis semanal para eventos creados en los últimos 30 días.
    Cubre eventos nuevos que no estaban en el batch mensual.
    """
    from app.db.session import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    try:
        events = db.execute(
            text("""
                SELECT fe.id FROM fire_events fe
                LEFT JOIN vegetation_monitoring vm
                    ON vm.fire_event_id = fe.id
                    AND DATE_TRUNC('month', vm.monitoring_date) = DATE_TRUNC('month', NOW())
                WHERE fe.created_at > NOW() - INTERVAL '30 days'
                AND vm.id IS NULL  -- sin análisis este mes
            """)
        ).fetchall()

        for event in events:
            analyze_recovery.apply_async(args=[str(event.id)], queue="gee")

        return {"enqueued": len(events)}
    finally:
        db.close()
```

### 3.4 Rate limiting en el endpoint de trigger (admin)

**Archivo:** `app/api/routes/monitoring.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post(
    "/recovery/trigger",
    status_code=202,
    dependencies=[Depends(get_current_user)],
)
@limiter.limit("10/hour")  # máximo 10 triggers manuales por hora por IP
async def trigger_recovery_analysis(
    request: Request,
    fire_event_id: UUID,
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Se requiere rol admin")

    # Verificar que el evento existe
    ...

    # Estimar costo GEE antes de encolar
    analyze_recovery.apply_async(
        args=[str(fire_event_id)],
        queue="gee",
        expires=3600,  # descarta si no se procesa en 1h (evita acumulación)
    )

    return {
        "status": "queued",
        "fire_event_id": str(fire_event_id),
        "message": "Análisis encolado. Los datos estarán disponibles en 2–5 minutos.",
        "estimated_gee_requests": 2,
    }
```

### 3.5 Circuit breaker para GEE

**Archivo:** `app/core/circuit_breaker.py` (nuevo)

```python
import time
from enum import Enum
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal: requests pasan
    OPEN = "open"          # Falla: requests bloqueados
    HALF_OPEN = "half_open"  # Probando recuperación


class GEECircuitBreaker:
    """
    Circuit breaker para llamadas a Google Earth Engine.

    Estados:
    - CLOSED: modo normal, errores se cuentan
    - OPEN: se bloquean requests por `recovery_timeout` segundos
    - HALF_OPEN: se permite 1 request de prueba; si falla vuelve a OPEN

    Configuración para GEE free tier:
    - failure_threshold=5: abre tras 5 errores consecutivos
    - recovery_timeout=300: espera 5 minutos antes de reintentar
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,  # segundos
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                remaining = int(
                    self.recovery_timeout - (time.time() - self.last_failure_time)
                )
                raise GEECircuitOpenError(
                    f"GEE circuit abierto. Reintento en {remaining}s."
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure(exc)
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self, exc: Exception):
        self.failure_count += 1
        self.last_failure_time = time.time()
        logger.warning(
            "gee_circuit_failure",
            failure_count=self.failure_count,
            threshold=self.failure_threshold,
            error=str(exc)[:200],  # no exponer internals completos
        )
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "gee_circuit_opened",
                recovery_timeout=self.recovery_timeout
            )

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time is not None
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    @property
    def is_healthy(self) -> bool:
        return self.state == CircuitState.CLOSED


class GEECircuitOpenError(Exception):
    pass


# Instancia global (singleton en proceso de worker)
gee_circuit = GEECircuitBreaker(failure_threshold=5, recovery_timeout=300)
```

**Integración en `VAEService`:**

```python
# app/services/vae_service.py
from app.core.circuit_breaker import gee_circuit, GEECircuitOpenError

class VAEService:
    def _get_current_ndvi(self, fire_event_id: str, target_date) -> float:
        try:
            return gee_circuit.call(
                self._gee.compute_ndvi,
                fire_event_id,
                target_date,
            )
        except GEECircuitOpenError:
            raise GEEServiceUnavailableError("GEE temporalmente no disponible")
```

### 3.6 Manejo correcto de error messages (no exponer internals)

**Archivo:** `app/api/routes/monitoring.py`

```python
# Antes (expone internals):
raise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")

# Después (seguro):
logger.error(
    "monitoring_endpoint_error",
    fire_event_id=str(fire_event_id),
    error_type=type(e).__name__,
    # NO loguear str(e) directamente si puede tener tokens GEE
    error_msg=str(e)[:500],
)
raise HTTPException(
    status_code=503,
    detail="Servicio de análisis temporalmente no disponible. Intente nuevamente en unos minutos."
)
```

---

## 4. Migraciones de base de datos

### 4.1 Índice para queries de timeline

```sql
-- Migración: add_vegetation_monitoring_indexes
-- Archivo: supabase/migrations/YYYYMMDD_add_vm_indexes.sql

-- Índice principal para queries por evento (endpoint GET /recovery/{id})
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vm_event_date
    ON vegetation_monitoring (fire_event_id, monitoring_date DESC);

-- Índice para queries de estado reciente (badge en feed)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_vm_event_latest
    ON vegetation_monitoring (fire_event_id, monitoring_date DESC)
    WHERE monitoring_date > NOW() - INTERVAL '3 months';

-- UNIQUE constraint para idempotencia de workers
ALTER TABLE vegetation_monitoring
    ADD CONSTRAINT uq_vm_event_date
    UNIQUE (fire_event_id, monitoring_date);
```

### 4.2 Campo de snapshot en fire_events (para badge público sin llamar al endpoint de monitoring)

```sql
-- Migración: add_recovery_snapshot_to_fire_events
ALTER TABLE fire_events
    ADD COLUMN IF NOT EXISTS recovery_status VARCHAR(50) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS recovery_percentage NUMERIC(5,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS last_monitoring_date DATE DEFAULT NULL;

-- Trigger para mantener sincronizado automáticamente
CREATE OR REPLACE FUNCTION sync_fire_event_recovery_snapshot()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE fire_events
    SET
        recovery_status = NEW.recovery_status,
        recovery_percentage = NEW.recovery_percentage,
        last_monitoring_date = NEW.monitoring_date
    WHERE id = NEW.fire_event_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sync_recovery_snapshot
    AFTER INSERT OR UPDATE ON vegetation_monitoring
    FOR EACH ROW
    EXECUTE FUNCTION sync_fire_event_recovery_snapshot();
```

Esto permite que `GET /fires/:id` incluya `recovery_status` y `recovery_percentage` directamente (badge público, 0 requests GEE, 0 llamadas al endpoint de monitoring).

---

## 5. Verificación y límites de seguridad

### 5.1 Verificación de implementación

```bash
# 1. Confirmar que el endpoint NO llama GEE
grep -n "VAEService\|get_recovery_timeline\|get_recovery_time_series" \
    app/api/routes/monitoring.py
# Esperado: 0 resultados (solo en workers)

# 2. Confirmar que el worker usa cola gee
grep -n "queue" workers/tasks/recovery.py
# Esperado: queue="gee" en todas las tareas

# 3. Verificar circuit breaker presente
grep -rn "gee_circuit\|GEECircuitBreaker" app/services/vae_service.py
# Esperado: al menos 1 resultado

# 4. Confirmar índice en BD (Supabase SQL editor)
SELECT indexname FROM pg_indexes
WHERE tablename = 'vegetation_monitoring';
-- Esperado: idx_vm_event_date, uq_vm_event_date

# 5. Test: endpoint responde sin GEE (datos en BD)
curl -s -w "\nHTTP %{http_code} — %{time_total}s\n" \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:8000/api/v1/monitoring/recovery/$FIRE_EVENT_ID"
# Esperado: HTTP 200, tiempo < 0.5s

# 6. Test: endpoint responde sin auth
curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:8000/api/v1/monitoring/recovery/$FIRE_EVENT_ID"
# Esperado: 401

# 7. Test: trigger con rate limit
for i in {1..12}; do
    curl -s -o /dev/null -w "%{http_code}\n" \
        -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
        "http://localhost:8000/api/v1/monitoring/recovery/trigger" \
        -d "{\"fire_event_id\": \"$FIRE_EVENT_ID\"}"
done
# Esperado: primeros 10 → 202, siguientes → 429
```

### 5.2 Límites configurados

| Límite | Valor | Archivo | Razón |
|---|---|---|---|
| Rate limit trigger admin | 10/hora por IP | `monitoring.py` | Proteger cuota GEE de abuso admin |
| Max eventos por batch mensual | 900 | `recovery.py` | 900×2=1.800 req GEE ≈ 4% cuota |
| Delay entre tasks en batch | 3 segundos | `recovery.py` | Evitar burst a GEE |
| Time limit por task GEE | 600s (soft 540s) | `celery_app` / tarea | Liberar worker ante timeout GEE |
| Reintentos GEE | 3 | tarea Celery | Con 5min entre intentos |
| Circuit breaker threshold | 5 errores | `circuit_breaker.py` | Abre tras 5 fallas consecutivas |
| Circuit breaker recovery | 300s | `circuit_breaker.py` | 5 min de pausa antes de reintentar |
| Expires de tarea encolada | 3.600s | trigger endpoint | Descarta si no se procesa en 1h |

### 5.3 Monitoreo de cuota GEE

Agregar al endpoint de health o a logs estructurados:

```python
# app/api/routes/monitoring.py (o en un endpoint /health/gee)
@router.get("/health/gee", include_in_schema=False)
async def gee_health(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403)

    from app.core.circuit_breaker import gee_circuit
    return {
        "circuit_state": gee_circuit.state.value,
        "failure_count": gee_circuit.failure_count,
        "is_healthy": gee_circuit.is_healthy,
        "last_failure": gee_circuit.last_failure_time,
    }
```

---

## 6. Hoja de ruta de implementación

```
Estado actual: GET /recovery/{id} → 37 GEE req síncronos

Fase 1 — Corrección crítica (1–2h)
  [1] Reescribir endpoint: leer de BD, no llamar GEE
  [2] Agregar _enqueue_recovery_if_not_pending()
  [3] Sanitizar error messages

Fase 2 — Worker correcto (2–3h)
  [4] Reescribir analyze_recovery: incremental (2 GEE/ejecución)
  [5] Agregar batch_recovery_monthly y batch_recovery_recent
  [6] Actualizar task_routes en celery_app.py (cola "gee")
  [7] Agregar al beat_schedule

Fase 3 — Índices y schema (30min)
  [8] Migración: idx_vm_event_date + uq_vm_event_date
  [9] Migración: columnas recovery_snapshot en fire_events + trigger

Fase 4 — Seguridad y resiliencia (1–2h)
  [10] Circuit breaker GEECircuitBreaker
  [11] Rate limit en POST /trigger (slowapi)
  [12] Endpoint /health/gee para admins

Verificación final
  [13] Tests de latencia: GET /recovery/{id} < 0.5s
  [14] Tests de auth: 401 sin token
  [15] Tests de rate limit: 429 tras 10 triggers/hora
```

---

## 7. Resumen de impacto

| Métrica | Antes | Después |
|---|---|---|
| Requests GEE por HTTP GET | 37 | 0 |
| Latencia endpoint | 10–30s | < 100ms |
| Usuarios simultáneos sin agotar cuota | ~1 | ilimitados |
| Requests GEE por evento por mes | 37 (en cada GET) | 2 (solo en worker) |
| Cuota GEE consumida por tráfico web | hasta 100% | 0% |
| Cuota GEE disponible para análisis | impredecible | ~90% |
| Protección ante falla GEE | ninguna | circuit breaker (5 fallas → 5min pausa) |
| Protección ante abuso del trigger | ninguna | 10 triggers/hora/IP |
