# Tareas técnicas: fases F5 y F6 (prioridad P1)

Fecha: 2026-03-12
Prerrequisitos: F1 (schema), F2 (umbrales), F3 (colas), F4 (taxonomía) completados
Referencia: `vae_module_specification.md` secciones 5, 6, 7

---

## F5: workers reales con persistencia

**Estado:** Completada 2026-03-12.  
F5-01 ya cumplía (no hay return 0.45; BaselineNotAvailableError existía). F5-02: fallback escalonado en _get_current_ndvi_with_cloud (30/50/70% nubes, ventanas 30/60/90 días). F5-03: analyze_recovery con bbox desde perimeter, persist de pending_reason (no_baseline_image, no_current_image), cache latest_recovery_status/latest_recovery_pct en fire_events. F5-04: detect_destruction con bbox desde perimeter, confidence_score en INSERT y notes unificadas. F5-05: colas vae ya aplicadas en F3.

---

### F5-01: corregir fallback silencioso de baseline en VAEService

**Archivo:** `app/services/vae_service.py` (~línea 704-707)

**Estado actual:**
```python
except GEEImageNotFoundError:
    logger.warning("No pre-fire image found, using default baseline")
    return 0.45
```

**Problema:** el fallback 0.45 produce datos ficticios. Un incendio en bosque denso (baseline real ~0.75) calcula recovery_pct = 0.35/0.45 = 77% cuando el real sería 0.35/0.75 = 46%.

**Cambio requerido:**
```python
except GEEImageNotFoundError:
    logger.warning(f"No pre-fire image found for bbox={bbox}, fire_date={fire_date}")
    raise BaselineNotAvailableError(
        f"No hay imágenes Sentinel-2 pre-incendio disponibles "
        f"para la fecha {fire_date}"
    )
```

Si `BaselineNotAvailableError` no existe como clase, crearla:

**Archivo:** `app/services/vae_service.py` (sección de excepciones, inicio del archivo)

```python
class BaselineNotAvailableError(Exception):
    """No hay imagen pre-incendio disponible en GEE para calcular baseline NDVI."""
    pass
```

**Verificación:**
```bash
grep -n "return 0.45" app/services/vae_service.py
# Esperado: 0 resultados

grep -n "BaselineNotAvailableError" app/services/vae_service.py
# Esperado: al menos 2 (definición + raise)
```

---

### F5-02: implementar fallback escalonado por nubosidad

**Archivo:** `app/services/vae_service.py` — método `_get_current_ndvi` o `_get_current_ndvi_with_cloud`

**Estado actual:** usa `max_cloud_cover=30` fijo. Si no hay imagen con < 30% nubes, falla.

**Cambio requerido:** implementar búsqueda escalonada antes de declarar falta de imagen.

```python
def _get_current_ndvi_with_cloud(
    self, bbox: dict, target_date: date
) -> tuple[float, float]:
    """
    Obtiene NDVI actual con fallback escalonado por nubosidad.
    
    Estrategia: ampliar ventana temporal y tolerancia de nubes
    progresivamente antes de declarar falta de imagen.
    
    Returns:
        tuple (ndvi_mean, cloud_cover_pct)
    
    Raises:
        GEEImageNotFoundError si no se encuentra imagen en ninguna combinación.
    """
    cloud_thresholds = [30, 50, 70]
    window_days_options = [30, 60, 90]
    
    for max_cloud in cloud_thresholds:
        for window_days in window_days_options:
            try:
                start = target_date - timedelta(days=window_days)
                end = target_date + timedelta(days=window_days)
                
                collection = self._gee.get_sentinel_collection(
                    bbox=bbox,
                    start_date=start,
                    end_date=end,
                    max_cloud_cover=max_cloud,
                )
                
                best_image = self._gee.get_best_image(collection, bbox)
                ndvi_result = self._gee.calculate_ndvi(best_image, bbox)
                cloud_cover = self._gee.get_image_cloud_cover(best_image)
                
                logger.info(
                    f"NDVI obtenido con cloud_max={max_cloud}, "
                    f"window={window_days}d: ndvi={ndvi_result.mean:.3f}, "
                    f"cloud={cloud_cover:.1f}%"
                )
                return ndvi_result.mean, cloud_cover
                
            except GEEImageNotFoundError:
                continue
    
    raise GEEImageNotFoundError(
        f"No se encontró imagen utilizable para bbox={bbox}, "
        f"target={target_date} después de búsqueda extendida"
    )
```

**Nota:** si el método actual tiene lógica adicional (circuit breaker, rate limiting), preservarla y solo agregar el loop de escalonamiento alrededor de la búsqueda.

**Verificación:**
```bash
grep -n "cloud_thresholds\|window_days_options" app/services/vae_service.py
# Esperado: ambas variables presentes

grep -n "max_cloud_cover=30" app/services/vae_service.py
# Esperado: 0 resultados como valor hardcodeado único (puede aparecer como primer elemento del array)
```

---

### F5-03: reescribir worker analyze_recovery

**Archivo:** `workers/tasks/recovery.py`

**Estado actual según auditorías:** el worker tiene estructura parcial pero fragmentos hardcodeados (líneas 37-57 retornan dict con valores fijos en algunos paths). Según la auditoría AS-IS, la estructura de VAEService call + upsert existe pero el critical review confirma paths que no persisten.

**Comportamiento objetivo completo:**

```python
import logging
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

from workers.celery_app import celery_app
from app.db.session import SessionLocal
from app.services.vae_service import VAEService, BaselineNotAvailableError
from app.services.gee_service import GEEImageNotFoundError, GEEServiceUnavailableError
from app.core.recovery_thresholds import classify_recovery_status

logger = logging.getLogger(__name__)


@celery_app.task(
    queue="vae",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=300,
    time_limit=360,
)
def analyze_recovery(self, fire_event_id: str) -> dict:
    """
    Analiza recuperación de vegetación para un evento de incendio.
    
    Flujo:
    1. Lee geometría del evento desde fire_events
    2. Busca o calcula baseline NDVI
    3. Calcula NDVI actual vía GEE
    4. Clasifica estado de recuperación
    5. Persiste en vegetation_monitoring (upsert)
    6. Actualiza cache en fire_events
    
    Idempotente: ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE.
    """
    db = SessionLocal()
    try:
        # 1. Leer evento
        row = db.execute(text("""
            SELECT
                fe.start_date,
                ST_X(fe.centroid) AS lon,
                ST_Y(fe.centroid) AS lat,
                fe.estimated_area_hectares,
                CASE 
                    WHEN fe.perimeter IS NOT NULL THEN
                        ST_XMin(fe.perimeter) 
                    ELSE ST_X(fe.centroid) - 0.01
                END AS bbox_west,
                CASE 
                    WHEN fe.perimeter IS NOT NULL THEN
                        ST_YMin(fe.perimeter)
                    ELSE ST_Y(fe.centroid) - 0.01
                END AS bbox_south,
                CASE 
                    WHEN fe.perimeter IS NOT NULL THEN
                        ST_XMax(fe.perimeter)
                    ELSE ST_X(fe.centroid) + 0.01
                END AS bbox_east,
                CASE 
                    WHEN fe.perimeter IS NOT NULL THEN
                        ST_YMax(fe.perimeter)
                    ELSE ST_Y(fe.centroid) + 0.01
                END AS bbox_north
            FROM fire_events fe
            WHERE fe.id = :fid
        """), {"fid": fire_event_id}).fetchone()

        if not row:
            logger.error(f"Fire event {fire_event_id} not found")
            return {"status": "error", "reason": "event_not_found"}

        fire_date = row.start_date
        bbox = {
            "west": float(row.bbox_west),
            "south": float(row.bbox_south),
            "east": float(row.bbox_east),
            "north": float(row.bbox_north),
        }
        
        target_date = date.today().replace(day=1)  # primer día del mes actual
        months_after = (
            (target_date.year - fire_date.year) * 12
            + (target_date.month - fire_date.month)
        )

        # 2. Buscar baseline existente en BD
        existing_baseline = db.execute(text("""
            SELECT baseline_ndvi FROM vegetation_monitoring
            WHERE fire_event_id = :fid AND baseline_ndvi IS NOT NULL
            ORDER BY monitoring_date ASC LIMIT 1
        """), {"fid": fire_event_id}).fetchone()

        vae = VAEService()

        if existing_baseline and existing_baseline.baseline_ndvi:
            baseline_ndvi = float(existing_baseline.baseline_ndvi)
        else:
            try:
                baseline_ndvi = vae._get_baseline_ndvi(bbox, fire_date)
            except BaselineNotAvailableError:
                logger.warning(
                    f"No baseline available for {fire_event_id}"
                )
                # Persistir estado pending con razón
                db.execute(text("""
                    INSERT INTO vegetation_monitoring (
                        fire_event_id, monitoring_date, months_after_fire,
                        pending_reason, recovery_status, updated_at
                    ) VALUES (
                        :fid, :date, :months, 'no_baseline_image', 'pending', NOW()
                    )
                    ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                        pending_reason = 'no_baseline_image',
                        recovery_status = 'pending',
                        updated_at = NOW()
                """), {
                    "fid": fire_event_id,
                    "date": target_date,
                    "months": months_after,
                })
                db.commit()
                return {"status": "pending", "reason": "no_baseline_image"}

        # 3. Calcular NDVI actual
        try:
            current_ndvi, cloud_cover = vae._get_current_ndvi_with_cloud(
                bbox, target_date
            )
        except GEEImageNotFoundError:
            logger.warning(
                f"No current image for {fire_event_id} at {target_date}"
            )
            db.execute(text("""
                INSERT INTO vegetation_monitoring (
                    fire_event_id, monitoring_date, months_after_fire,
                    baseline_ndvi, pending_reason, recovery_status, updated_at
                ) VALUES (
                    :fid, :date, :months, :baseline,
                    'no_current_image', 'pending', NOW()
                )
                ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                    pending_reason = 'no_current_image',
                    recovery_status = 'pending',
                    updated_at = NOW()
            """), {
                "fid": fire_event_id,
                "date": target_date,
                "months": months_after,
                "baseline": baseline_ndvi,
            })
            db.commit()
            return {"status": "pending", "reason": "no_current_image"}

        # 4. Calcular recovery
        recovery_pct = min(100.0, max(0.0, (current_ndvi / baseline_ndvi) * 100))
        recovery_status = classify_recovery_status(recovery_pct)

        # 5. Upsert en vegetation_monitoring
        db.execute(text("""
            INSERT INTO vegetation_monitoring (
                fire_event_id, monitoring_date, months_after_fire,
                ndvi_mean, baseline_ndvi, recovery_percentage,
                cloud_cover_pct, recovery_status, pending_reason,
                updated_at
            ) VALUES (
                :fid, :date, :months,
                :ndvi, :baseline, :recovery_pct,
                :cloud, :status, NULL,
                NOW()
            )
            ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                baseline_ndvi = EXCLUDED.baseline_ndvi,
                recovery_percentage = EXCLUDED.recovery_percentage,
                cloud_cover_pct = EXCLUDED.cloud_cover_pct,
                recovery_status = EXCLUDED.recovery_status,
                pending_reason = NULL,
                updated_at = NOW()
        """), {
            "fid": fire_event_id,
            "date": target_date,
            "months": months_after,
            "ndvi": current_ndvi,
            "baseline": baseline_ndvi,
            "recovery_pct": recovery_pct,
            "cloud": cloud_cover,
            "status": recovery_status,
        })

        # 6. Actualizar cache en fire_events
        db.execute(text("""
            UPDATE fire_events SET
                latest_recovery_status = :status,
                latest_recovery_pct = :pct
            WHERE id = :fid
        """), {
            "fid": fire_event_id,
            "status": recovery_status,
            "pct": recovery_pct,
        })

        db.commit()

        logger.info(
            f"Recovery analyzed: {fire_event_id} → "
            f"{recovery_status} ({recovery_pct:.1f}%)"
        )
        return {
            "status": "ok",
            "fire_event_id": fire_event_id,
            "recovery_percentage": round(recovery_pct, 1),
            "recovery_status": recovery_status,
            "baseline_ndvi": baseline_ndvi,
            "current_ndvi": current_ndvi,
        }

    except GEEServiceUnavailableError as e:
        logger.error(f"GEE circuit breaker open: {e}")
        raise self.retry(exc=e, countdown=300)
    except Exception as e:
        logger.error(f"Unexpected error analyzing {fire_event_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
```

**Puntos clave del diseño:**

- **Bbox desde perimeter, no centroid.** Usa `ST_XMin/YMin/XMax/YMax(perimeter)` con fallback a centroid ±0.01° si no hay perimeter. Esto resuelve el bug histórico de bboxes microscópicas.
- **Baseline reutilizado desde BD.** Solo llama GEE si no existe baseline previo.
- **Pending con razón.** Persiste `pending_reason` para distinguir "no baseline" de "no imagen actual".
- **Cache en fire_events.** Actualiza `latest_recovery_status` + `latest_recovery_pct` para evitar N+1 desde FireCard.
- **Retry con circuit breaker.** Si GEE está caído, reintenta en 5 minutos.

**Verificación:**
```bash
grep -n "return 0.45\|'recovery_percentage': 45.7\|hardcoded\|# hardcodeado" workers/tasks/recovery.py
# Esperado: 0 resultados

grep -n "ON CONFLICT" workers/tasks/recovery.py
# Esperado: al menos 1 resultado

grep -n "latest_recovery_status" workers/tasks/recovery.py
# Esperado: al menos 1 resultado (cache update)
```

---

### F5-04: reescribir worker detect_destruction

**Archivo:** `workers/tasks/destruction.py`

**Comportamiento objetivo:** sigue la misma estructura que F5-03 pero persiste en `land_use_changes`:

```python
@celery_app.task(
    queue="vae",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=300,
    time_limit=360,
)
def detect_destruction(self, fire_event_id: str) -> dict:
    """
    Detecta cambios de uso de suelo post-incendio.
    
    Persiste en land_use_changes con confidence_score.
    Genera notificación interna si is_potential_violation = true.
    NO notifica a autoridades (decisión D-04).
    """
    db = SessionLocal()
    try:
        # 1. Leer evento (misma query que F5-03 para bbox)
        row = db.execute(text("""..."""), {"fid": fire_event_id}).fetchone()
        if not row:
            return {"status": "error", "reason": "event_not_found"}

        fire_date = row.start_date
        bbox = { ... }  # misma lógica que F5-03
        area_ha = float(row.estimated_area_hectares or 0)
        
        analysis_date = date.today()
        months_after = (
            (analysis_date.year - fire_date.year) * 12
            + (analysis_date.month - fire_date.month)
        )

        # 2. Llamar VAEService
        vae = VAEService()
        try:
            result = vae.detect_land_use_change(
                fire_event_id=fire_event_id,
                bbox=bbox,
                fire_date=fire_date,
                analysis_date=analysis_date,
                area_hectares=area_ha,
            )
        except (BaselineNotAvailableError, GEEImageNotFoundError) as e:
            logger.warning(f"Cannot detect destruction for {fire_event_id}: {e}")
            return {"status": "pending", "reason": str(type(e).__name__)}

        # 3. Persistir en land_use_changes
        is_violation = result.is_potential_violation
        confidence = getattr(result, "confidence", None) or 0.5

        db.execute(text("""
            INSERT INTO land_use_changes (
                fire_event_id, change_detected_at, months_after_fire,
                change_type, change_severity,
                affected_area_hectares, is_potential_violation,
                confidence_score, status, notes, updated_at
            ) VALUES (
                :fid, :date, :months,
                :type, :severity,
                :area, :violation,
                :confidence, 'pending_review',
                :notes, NOW()
            )
            ON CONFLICT (fire_event_id, change_detected_at) DO UPDATE SET
                change_type = EXCLUDED.change_type,
                change_severity = EXCLUDED.change_severity,
                affected_area_hectares = EXCLUDED.affected_area_hectares,
                is_potential_violation = EXCLUDED.is_potential_violation,
                confidence_score = EXCLUDED.confidence_score,
                notes = EXCLUDED.notes,
                updated_at = NOW()
        """), {
            "fid": fire_event_id,
            "date": analysis_date,
            "months": months_after,
            "type": result.change_type.value if hasattr(result.change_type, 'value') else str(result.change_type),
            "severity": result.severity.value if hasattr(result.severity, 'value') else str(result.severity),
            "area": area_ha,
            "violation": is_violation,
            "confidence": confidence,
            "notes": "Alerta de detección remota — requiere verificación presencial",
        })
        db.commit()

        # 4. Notificación interna si hay violación (decisión D-04)
        if is_violation:
            logger.warning(
                f"VIOLATION ALERT: {fire_event_id} — "
                f"type={result.change_type}, confidence={confidence:.2f}"
            )
            # TODO: integrar con sistema de notificaciones internas
            # notification_service.notify_team(...)

        return {
            "status": "ok",
            "fire_event_id": fire_event_id,
            "change_type": str(result.change_type),
            "is_potential_violation": is_violation,
            "confidence_score": confidence,
        }

    except GEEServiceUnavailableError as e:
        raise self.retry(exc=e, countdown=300)
    except Exception as e:
        logger.error(f"Error detecting destruction {fire_event_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
```

**Verificación:**
```bash
grep -n "ON CONFLICT" workers/tasks/destruction.py
# Esperado: al menos 1

grep -n "confidence_score" workers/tasks/destruction.py
# Esperado: al menos 1

grep -n "hardcodeado\|hardcoded\|'recovery_percentage': 45" workers/tasks/destruction.py
# Esperado: 0
```

---

### F5-05: batch tasks — actualizar para usar cola vae

**Archivo:** `workers/tasks/recovery.py` — funciones batch

Verificar y actualizar todas las funciones batch (`batch_recovery_monthly`, `batch_recovery_recent`, `batch_episode_recovery_analysis`) para que:

1. Consulten `fire_events` con `status IN ('active', 'monitoring', 'contained')` y `start_date > NOW() - INTERVAL '36 months'`.
2. Encolen `analyze_recovery` con `.set(queue='vae')` (no `analysis` ni `gee`).
3. Encolen `detect_destruction` desde el batch mensual de destruction.

**Verificación:**
```bash
grep -rn "set(queue=" workers/tasks/recovery.py workers/tasks/destruction.py
# Todos los resultados deben ser queue='vae'
```

---

## F6: API con autenticación diferenciada

**Estado:** Completada 2026-03-12.  
Router monitoring sin auth global (main.py). Summary y GET recovery/{id} públicos; summary con legal_disclaimer y average_recovery_percentage. GET recovery/{id} con get_optional_user; anotaciones human_activity_detected/activity_type solo cuando current_user no es None. GET land-use-changes con Depends(get_current_user) y legal_disclaimer + confidence_score en respuesta. Trigger con get_current_user + is_admin y rate limit existente. _enqueue_recovery_if_not_pending(fire_event_id, db) con chequeo pending_reason en ventana 1 h. get_optional_user alias de get_current_user_optional en auth_deps.

---

### F6-01: reestructurar autenticación del router monitoring

**Archivo:** `app/main.py` (~línea 236)

**Estado actual:** el router monitoring no tiene `dependencies=[Depends(get_current_user)]`.

**Cambio:** NO agregar auth a nivel de router (porque el summary debe ser público). En su lugar, aplicar auth por endpoint individual.

```python
# main.py — SIN dependencies globales para monitoring:
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    # NO dependencies aquí — auth se maneja por endpoint
)
```

---

### F6-02: endpoint GET /monitoring/recovery/summary — público

**Archivo:** `app/api/routes/monitoring.py`

Este endpoint ya existe. Cambios requeridos:

1. **Sin auth** (público para transparencia).
2. **Corregir query** (anomaly_type → activity_type, INTERVAL fix — ya hechos en F4).
3. **Agregar disclaimer legal.**
4. **Excluir datos de violaciones** del response público.

```python
from app.core.legal import get_legal_disclaimer

@router.get("/recovery/summary")
async def get_recovery_summary(
    # Sin dependencia de auth — endpoint público
    min_months: int = Query(default=3, ge=1, le=36),
    db: Session = Depends(get_db),
):
    """
    Resumen público de estado de recuperación.
    No incluye datos de violaciones ni cambios de uso.
    """
    # ... query existente con fixes de F4 ...
    
    return {
        "total_monitored_events": total,
        "status_breakdown": breakdown,
        "average_recovery_percentage": avg_pct,
        "legal_disclaimer": get_legal_disclaimer(),
        # NO incluir: violation_count, changes, is_potential_violation
    }
```

---

### F6-03: endpoint GET /monitoring/recovery/{fire_event_id} — auth diferenciada

**Archivo:** `app/api/routes/monitoring.py`

**Cambio clave:** este endpoint debe funcionar tanto para anónimos (datos básicos) como para autenticados (datos completos). Usar optional auth.

```python
from app.api.auth_deps import get_optional_user  # ver F6-07

@router.get("/recovery/{fire_event_id}")
async def get_recovery_status(
    fire_event_id: str,
    current_user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    Datos de recuperación para un evento.
    
    Anónimo: badge de estado + gráfico NDVI + métricas básicas.
    Autenticado: todo lo anterior + anotaciones de anomalías.
    """
    # 1. Leer de BD (NUNCA llamar GEE en tiempo real)
    rows = db.execute(text("""
        SELECT monitoring_date, months_after_fire, ndvi_mean,
               baseline_ndvi, recovery_percentage, cloud_cover_pct,
               recovery_status, pending_reason,
               human_activity_detected, activity_type
        FROM vegetation_monitoring
        WHERE fire_event_id = :fid
        ORDER BY monitoring_date ASC
    """), {"fid": fire_event_id}).fetchall()

    if not rows:
        # Encolar análisis si no hay datos
        _enqueue_recovery_if_not_pending(fire_event_id, db)
        return {
            "fire_event_id": fire_event_id,
            "recovery_status": "pending",
            "recovery_metric": "baseline_ratio",
            "recovery_metric_description": "Porcentaje del NDVI pre-incendio alcanzado",
            "baseline_ndvi": None,
            "current_ndvi": None,
            "recovery_percentage": None,
            "months_monitored": 0,
            "monitoring_data": [],
            "message": "Análisis en proceso. Los datos estarán disponibles próximamente.",
            "legal_disclaimer": get_legal_disclaimer(),
        }

    # 2. Construir respuesta
    latest = rows[-1]
    baseline = next((r.baseline_ndvi for r in rows if r.baseline_ndvi), None)
    
    monitoring_data = []
    for r in rows:
        entry = {
            "monitoring_date": str(r.monitoring_date),
            "months_after_fire": r.months_after_fire,
            "ndvi_mean": r.ndvi_mean,
            "recovery_percentage": r.recovery_percentage,
            "cloud_cover_pct": r.cloud_cover_pct,
            "recovery_status": r.recovery_status,
        }
        # Solo autenticados ven anotaciones de anomalías
        if current_user:
            entry["human_activity_detected"] = r.human_activity_detected
            entry["activity_type"] = r.activity_type
        monitoring_data.append(entry)

    return {
        "fire_event_id": fire_event_id,
        "recovery_status": latest.recovery_status or "pending",
        "recovery_metric": "baseline_ratio",
        "recovery_metric_description": "Porcentaje del NDVI pre-incendio alcanzado",
        "baseline_ndvi": baseline,
        "current_ndvi": latest.ndvi_mean,
        "recovery_percentage": latest.recovery_percentage,
        "months_monitored": len(rows),
        "monitoring_data": monitoring_data,
        "legal_disclaimer": get_legal_disclaimer(),
    }
```

**Punto crítico:** este endpoint lee de BD exclusivamente. El patrón anterior de llamar `VAEService().get_recovery_timeline()` (37 req GEE por request) se elimina completamente.

---

### F6-04: endpoint GET /monitoring/land-use-changes/{fire_event_id} — solo JWT

**Archivo:** `app/api/routes/monitoring.py`

**Endpoint nuevo** (no existe actualmente):

```python
from app.api.auth_deps import get_current_user

@router.get("/land-use-changes/{fire_event_id}")
async def get_land_use_changes(
    fire_event_id: str,
    current_user=Depends(get_current_user),  # JWT obligatorio
    db: Session = Depends(get_db),
):
    """
    Cambios de uso de suelo detectados para un evento.
    Requiere autenticación. Contiene datos de posibles violaciones.
    """
    # Verificar que el evento existe
    event = db.execute(text(
        "SELECT id FROM fire_events WHERE id = :fid"
    ), {"fid": fire_event_id}).fetchone()
    
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    rows = db.execute(text("""
        SELECT change_detected_at, months_after_fire,
               change_type, change_severity,
               affected_area_hectares, is_potential_violation,
               confidence_score, status, notes
        FROM land_use_changes
        WHERE fire_event_id = :fid
        ORDER BY change_detected_at DESC
    """), {"fid": fire_event_id}).fetchall()

    changes = [
        {
            "change_detected_at": str(r.change_detected_at),
            "months_after_fire": r.months_after_fire,
            "change_type": r.change_type,
            "change_severity": r.change_severity,
            "affected_area_hectares": r.affected_area_hectares,
            "is_potential_violation": r.is_potential_violation,
            "confidence_score": r.confidence_score,
            "status": r.status,
            "notes": r.notes,
        }
        for r in rows
    ]

    violation_count = sum(1 for r in rows if r.is_potential_violation)

    return {
        "fire_event_id": fire_event_id,
        "total_changes": len(changes),
        "violation_count": violation_count,
        "changes": changes,
        "legal_disclaimer": get_legal_disclaimer(),
    }
```

---

### F6-05: endpoint POST /monitoring/recovery/trigger — admin + rate limit

**Archivo:** `app/api/routes/monitoring.py`

```python
from app.api.auth_deps import get_current_user, require_admin
from app.core.rate_limiter import rate_limit  # ya existe en el proyecto

@router.post("/recovery/trigger", status_code=202)
async def trigger_recovery_analysis(
    fire_event_id: str = Query(...),
    current_user=Depends(require_admin),  # admin obligatorio
    db: Session = Depends(get_db),
):
    """
    Disparo manual de análisis VAE.
    Solo admin. Rate limit: 5 requests por 6 horas.
    """
    # Verificar evento existe
    event = db.execute(text(
        "SELECT id, start_date FROM fire_events WHERE id = :fid"
    ), {"fid": fire_event_id}).fetchone()
    
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    # Encolar ambas tareas
    from workers.tasks.recovery import analyze_recovery
    from workers.tasks.destruction import detect_destruction
    
    analyze_recovery.apply_async(args=[fire_event_id], queue="vae")
    detect_destruction.apply_async(args=[fire_event_id], queue="vae")

    return {
        "message": "Análisis encolado exitosamente",
        "fire_event_id": fire_event_id,
        "jobs_enqueued": ["analyze_recovery", "detect_destruction"],
    }
```

**Rate limit:** aplicar el decorador/middleware existente (`app/core/rate_limiter.py`) con límite de 5 requests por 6 horas por usuario. Si `rate_limiter.py` no tiene esta granularidad, agregar:

```python
# En el endpoint, antes de encolar:
_check_trigger_rate_limit(current_user.id, db)  # lanza 429 si excede
```

---

### F6-06: helper _enqueue_recovery_if_not_pending

**Archivo:** `app/api/routes/monitoring.py`

Función auxiliar para evitar encolar duplicados:

```python
def _enqueue_recovery_if_not_pending(fire_event_id: str, db: Session):
    """
    Encola analyze_recovery solo si no hay un job pendiente reciente.
    Usa pending_reason como semáforo simple.
    """
    recent_pending = db.execute(text("""
        SELECT 1 FROM vegetation_monitoring
        WHERE fire_event_id = :fid
          AND pending_reason IS NOT NULL
          AND updated_at > NOW() - INTERVAL '1 hour'
        LIMIT 1
    """), {"fid": fire_event_id}).fetchone()

    if not recent_pending:
        from workers.tasks.recovery import analyze_recovery
        analyze_recovery.apply_async(args=[fire_event_id], queue="vae")
        logger.info(f"Enqueued recovery analysis for {fire_event_id}")
```

---

### F6-07: crear get_optional_user en auth_deps

**Archivo:** `app/api/auth_deps.py`

Si no existe una función que retorne `None` cuando no hay JWT (en vez de lanzar 401), crearla:

```python
async def get_optional_user(
    authorization: str | None = Header(default=None),
) -> User | None:
    """
    Retorna el usuario autenticado o None si no hay JWT.
    Para endpoints con acceso diferenciado anónimo/autenticado.
    """
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
```

**Verificación:**
```bash
grep -n "get_optional_user" app/api/auth_deps.py
# Esperado: al menos 1 (definición)

grep -n "get_optional_user" app/api/routes/monitoring.py
# Esperado: al menos 1 (uso en recovery endpoint)
```

---

## Verificación integral F5 + F6

### Test de humo post-deploy
```bash
# 1. Summary público (sin JWT)
curl -s http://localhost:8000/api/v1/monitoring/recovery/summary | python -m json.tool
# Esperado: 200 con status_breakdown, sin violation_count

# 2. Recovery sin JWT (datos básicos)
curl -s http://localhost:8000/api/v1/monitoring/recovery/TEST_EVENT_ID | python -m json.tool
# Esperado: 200 con monitoring_data SIN human_activity_detected

# 3. Recovery con JWT (datos completos)
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/monitoring/recovery/TEST_EVENT_ID | python -m json.tool
# Esperado: 200 con monitoring_data CON human_activity_detected

# 4. Land use changes sin JWT
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8000/api/v1/monitoring/land-use-changes/TEST_EVENT_ID
# Esperado: 401

# 5. Land use changes con JWT
curl -s -H "Authorization: Bearer $JWT" \
  http://localhost:8000/api/v1/monitoring/land-use-changes/TEST_EVENT_ID | python -m json.tool
# Esperado: 200 con changes + legal_disclaimer

# 6. Trigger sin JWT
curl -s -o /dev/null -w "%{http_code}" -X POST \
  "http://localhost:8000/api/v1/monitoring/recovery/trigger?fire_event_id=TEST"
# Esperado: 401

# 7. Trigger con JWT no-admin
curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $USER_JWT" \
  "http://localhost:8000/api/v1/monitoring/recovery/trigger?fire_event_id=TEST"
# Esperado: 403

# 8. Worker ejecuta y persiste (single event test)
docker compose exec worker-gee celery -A workers.celery_app call \
  workers.tasks.recovery.analyze_recovery --args='["TEST_EVENT_ID"]' -Q vae
# Verificar en BD:
psql "$DATABASE_URL" -c "SELECT * FROM vegetation_monitoring WHERE fire_event_id = 'TEST_EVENT_ID';"
# Esperado: al menos 1 fila con ndvi_mean NOT NULL
```

---

## Orden de ejecución F5 + F6

```
F5-01 (fix baseline fallback) ─┐
F5-02 (nubosidad escalonada)   ├── Cambios en vae_service.py (1 deploy)
                                │
F5-03 (worker recovery)  ──────┤
F5-04 (worker destruction) ────┤── Cambios en workers/ (mismo deploy)
F5-05 (batch tasks)      ──────┘
                                │
F6-01 (router sin auth global) ┐
F6-02 (summary público)       ├── Cambios en API (mismo deploy)
F6-03 (recovery diferenciada)  │
F6-04 (land-use con JWT)      │
F6-05 (trigger admin)         │
F6-06 (enqueue helper)        │
F6-07 (optional auth)   ──────┘

Deploy secuencia:
1. Deploy código (F5 + F6 juntos)
2. Restart workers: docker compose restart worker-gee
3. Test single-event recovery (F5-03 verificación)
4. Test endpoints (F6 smoke tests)
5. Monitorear logs 24h para errores GEE
```
