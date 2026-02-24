# UC-F12 VAE: tareas técnicas para Claude Code

> **Fecha:** 2026-02-24
> **Objetivo:** implementar todas las correcciones y mejoras del UC-F12 (recuperación vegetativa y cambio de uso de suelo) identificadas en la revisión crítica.
> **Modo de ejecución:** Claude Code debe ejecutar estas tareas en orden secuencial dentro de cada fase. Las fases 1 y 2 pueden ejecutarse en paralelo entre sí.
> **Convención:** cada tarea incluye archivo, líneas de referencia, qué hacer, y comando de verificación.

---

## Instrucciones generales para Claude Code

1. Antes de modificar cualquier archivo, ejecutar `git status` y confirmar que el working directory está limpio.
2. Crear una rama: `git checkout -b feature/uc-f12-vae-implementation`.
3. Ejecutar cada tarea en orden. Después de cada tarea, ejecutar el comando de verificación.
4. Hacer un commit por fase completada con mensaje descriptivo.
5. No modificar archivos fuera del alcance de cada tarea.
6. Respetar las convenciones existentes del proyecto: Python con type hints, TypeScript strict, Tailwind CSS para estilos.
7. Todas las rutas son relativas a la raíz del repositorio `wildfire-recovery-argentina/`.

---

## FASE 0 — Prerrequisitos de schema (bloqueante)

### TAREA 0.1: verificar estado de la migración de hardening

**Contexto:** existe `database/migrations/2026_02_23_uc_f12_vae_monitoring.sql` con UNIQUE constraints, NOT NULL, FK y RLS. Necesitamos confirmar si ya fue aplicada o no.

**Acción:**
```bash
# Verificar si la migración existe en el repo
cat database/migrations/2026_02_23_uc_f12_vae_monitoring.sql
```

**Si la migración existe pero NO fue aplicada en producción**, este archivo debe incluirse en el pipeline de deploy. Documentar en este log qué contiene y confirmar que es segura de aplicar.

**Verificación:**
```bash
grep -n "UNIQUE\|NOT NULL\|FOREIGN KEY\|ENABLE ROW LEVEL SECURITY" database/migrations/2026_02_23_uc_f12_vae_monitoring.sql
```

---

### TAREA 0.2: crear migración complementaria si faltan elementos

**Archivo:** `database/migrations/2026_02_24_uc_f12_vae_complementary.sql` (nuevo)

**Acción:** revisar la migración existente (`2026_02_23`) y compararla contra los requisitos. Si falta alguno de estos elementos, crear una migración complementaria:

```sql
-- Solo incluir las sentencias que NO estén en la migración existente.
-- Verificar cada una antes de incluirla.

-- 1. UNIQUE constraint en vegetation_monitoring
-- Verificar: SELECT conname FROM pg_constraint WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u';
-- Si no existe:
ALTER TABLE vegetation_monitoring
  ADD CONSTRAINT uq_vm_event_date UNIQUE (fire_event_id, monitoring_date);

-- 2. UNIQUE constraint en land_use_changes
-- Verificar: SELECT conname FROM pg_constraint WHERE conrelid = 'land_use_changes'::regclass AND contype = 'u';
-- Si no existe:
ALTER TABLE land_use_changes
  ADD CONSTRAINT uq_luc_event_detected UNIQUE (fire_event_id, change_detected_at);

-- 3. NOT NULL en is_potential_violation
-- Verificar: SELECT is_nullable FROM information_schema.columns WHERE table_name = 'land_use_changes' AND column_name = 'is_potential_violation';
-- Si es 'YES':
UPDATE land_use_changes SET is_potential_violation = false WHERE is_potential_violation IS NULL;
ALTER TABLE land_use_changes ALTER COLUMN is_potential_violation SET NOT NULL;

-- 4. FK monitoring_record_id → vegetation_monitoring(id)
-- Verificar: SELECT conname FROM pg_constraint WHERE conrelid = 'land_use_changes'::regclass AND conname LIKE '%monitoring_record%';
-- Si no existe:
ALTER TABLE land_use_changes
  ADD CONSTRAINT land_use_changes_monitoring_record_id_fkey
  FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id);

-- 5. Índice compuesto para performance de queries de timeline
CREATE INDEX IF NOT EXISTS idx_vm_event_date
  ON vegetation_monitoring(fire_event_id, monitoring_date);

CREATE INDEX IF NOT EXISTS idx_luc_event_detected
  ON land_use_changes(fire_event_id, change_detected_at);

-- 6. RLS — solo si no está habilitada ya
-- Verificar: SELECT relrowsecurity FROM pg_class WHERE relname = 'vegetation_monitoring';
-- Si es false:
ALTER TABLE vegetation_monitoring ENABLE ROW LEVEL SECURITY;
ALTER TABLE land_use_changes ENABLE ROW LEVEL SECURITY;

-- Política: usuarios autenticados pueden leer
CREATE POLICY IF NOT EXISTS vm_authenticated_read ON vegetation_monitoring
  FOR SELECT TO authenticated USING (true);

CREATE POLICY IF NOT EXISTS vm_service_write ON vegetation_monitoring
  FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY IF NOT EXISTS luc_authenticated_read ON land_use_changes
  FOR SELECT TO authenticated USING (true);

CREATE POLICY IF NOT EXISTS luc_service_write ON land_use_changes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

**Importante:** Claude Code debe verificar cada condición antes de incluir la sentencia. No incluir sentencias que ya estén aplicadas. Si todo ya está en la migración `2026_02_23`, no crear este archivo.

**Verificación:**
```bash
# Si se creó el archivo, validar que el SQL es sintácticamente correcto
python3 -c "
sql = open('database/migrations/2026_02_24_uc_f12_vae_complementary.sql').read()
print(f'Migration has {len(sql)} chars, {sql.count(\";\") } statements')
print('OK' if 'vegetation_monitoring' in sql else 'WARNING: missing vegetation_monitoring references')
"
```

---

## FASE 1 — Backend: corregir flujo de datos

### TAREA 1.1: reescribir worker de recovery

**Archivo:** `workers/tasks/recovery.py`
**Líneas de referencia:** 37-57 (stub actual con valores hardcodeados)

**Estado actual:** el worker retorna un dict con `recovery_percentage: 45.7` hardcodeado. No instancia VAEService, no consulta GEE, no escribe en BD.

**Acción:** reescribir la función `analyze_recovery` para:

1. Obtener la geometría del fire_event desde la BD (centroid, perimeter de `fire_events`)
2. Instanciar `VAEService` (importar desde `app.services.vae_service`)
3. Ejecutar el análisis NDVI usando `VAEService.analyze_recovery()`
4. Persistir resultados en `vegetation_monitoring` con `INSERT ... ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE`
5. Retornar el resultado persistido

**Esqueleto de implementación:**

```python
from celery import shared_task
from datetime import datetime, date
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    name='workers.tasks.recovery.analyze_recovery',
    queue='vae',
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def analyze_recovery(self, fire_event_id: str, months_after_fire: int = None):
    """
    Analiza recuperación vegetativa para un evento de incendio.
    
    Obtiene datos NDVI de GEE vía VAEService y persiste en vegetation_monitoring.
    Idempotente gracias a UNIQUE(fire_event_id, monitoring_date) + ON CONFLICT.
    
    Args:
        fire_event_id: UUID del evento de incendio
        months_after_fire: meses después del incendio (opcional, se calcula si no se provee)
    """
    from app.db.session import SessionLocal
    from app.services.vae_service import VAEService
    
    db = SessionLocal()
    try:
        # 1. Obtener geometría y fecha del evento
        event_query = text("""
            SELECT id, ST_AsGeoJSON(centroid)::json as centroid_geojson,
                   ST_AsGeoJSON(perimeter)::json as perimeter_geojson,
                   start_date, province
            FROM fire_events WHERE id = :event_id
        """)
        event = db.execute(event_query, {"event_id": fire_event_id}).fetchone()
        
        if not event:
            logger.error(f"Fire event {fire_event_id} not found")
            return {"status": "error", "message": "Event not found"}
        
        # 2. Ejecutar análisis VAE
        vae_service = VAEService()
        monitoring_date = date.today()
        
        try:
            result = vae_service.analyze_recovery(
                fire_event_id=fire_event_id,
                geometry=event.perimeter_geojson or event.centroid_geojson,
                fire_start_date=event.start_date,
            )
        except Exception as gee_exc:
            logger.warning(f"GEE analysis failed for {fire_event_id}: {gee_exc}")
            raise self.retry(exc=gee_exc)
        
        # 3. Persistir con upsert idempotente
        upsert_query = text("""
            INSERT INTO vegetation_monitoring (
                fire_event_id, monitoring_date, months_after_fire,
                ndvi_mean, ndvi_min, ndvi_max, ndvi_std_dev,
                baseline_ndvi, recovery_percentage,
                land_use_classification, human_activity_detected,
                activity_type, activity_confidence
            ) VALUES (
                :fire_event_id, :monitoring_date, :months_after_fire,
                :ndvi_mean, :ndvi_min, :ndvi_max, :ndvi_std_dev,
                :baseline_ndvi, :recovery_percentage,
                :land_use_classification, :human_activity_detected,
                :activity_type, :activity_confidence
            )
            ON CONFLICT (fire_event_id, monitoring_date) DO UPDATE SET
                ndvi_mean = EXCLUDED.ndvi_mean,
                ndvi_min = EXCLUDED.ndvi_min,
                ndvi_max = EXCLUDED.ndvi_max,
                ndvi_std_dev = EXCLUDED.ndvi_std_dev,
                baseline_ndvi = EXCLUDED.baseline_ndvi,
                recovery_percentage = EXCLUDED.recovery_percentage,
                land_use_classification = EXCLUDED.land_use_classification,
                human_activity_detected = EXCLUDED.human_activity_detected,
                activity_type = EXCLUDED.activity_type,
                activity_confidence = EXCLUDED.activity_confidence,
                updated_at = NOW()
            RETURNING id
        """)
        
        # Calcular months_after_fire si no fue provisto
        if months_after_fire is None and event.start_date:
            delta = monitoring_date - event.start_date.date() if hasattr(event.start_date, 'date') else monitoring_date - event.start_date
            months_after_fire = max(0, delta.days // 30)
        
        db.execute(upsert_query, {
            "fire_event_id": fire_event_id,
            "monitoring_date": monitoring_date,
            "months_after_fire": months_after_fire,
            "ndvi_mean": result.get("ndvi_mean"),
            "ndvi_min": result.get("ndvi_min"),
            "ndvi_max": result.get("ndvi_max"),
            "ndvi_std_dev": result.get("ndvi_std_dev"),
            "baseline_ndvi": result.get("baseline_ndvi"),
            "recovery_percentage": result.get("recovery_percentage"),
            "land_use_classification": result.get("land_use_classification"),
            "human_activity_detected": result.get("human_activity_detected", False),
            "activity_type": result.get("activity_type"),
            "activity_confidence": result.get("activity_confidence"),
        })
        db.commit()
        
        logger.info(f"Recovery analysis persisted for event {fire_event_id}")
        return {
            "status": "success",
            "fire_event_id": fire_event_id,
            "recovery_percentage": result.get("recovery_percentage"),
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Recovery analysis failed for {fire_event_id}: {e}")
        raise
    finally:
        db.close()
```

**Nota para Claude Code:** adaptar las llamadas a `VAEService` según la firma real de los métodos existentes en `app/services/vae_service.py`. Inspeccionar primero:
```bash
grep -n "def analyze_recovery\|def get_recovery\|def _get_current_ndvi\|def _get_baseline_ndvi" app/services/vae_service.py
```

**Verificación:**
```bash
python3 -c "
import ast
with open('workers/tasks/recovery.py') as f:
    tree = ast.parse(f.read())
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
assert 'analyze_recovery' in funcs, 'analyze_recovery function missing'
# Verificar que NO tiene valores hardcodeados
content = open('workers/tasks/recovery.py').read()
assert '45.7' not in content, 'Still has hardcoded 45.7'
assert '0.23' not in content, 'Still has hardcoded 0.23'
assert 'ON CONFLICT' in content, 'Missing upsert ON CONFLICT'
assert 'VAEService' in content, 'Not using VAEService'
print('PASS: recovery worker rewritten correctly')
"
```

---

### TAREA 1.2: reescribir worker de destruction

**Archivo:** `workers/tasks/destruction.py`
**Líneas de referencia:** 41-62 (stub actual)

**Estado actual:** stub con valores hardcodeados, no persiste datos.

**Acción:** reescribir `detect_destruction` con el mismo patrón que la tarea 1.1:

1. Obtener geometría del fire_event
2. Instanciar VAEService
3. Ejecutar `detect_land_use_change()` o equivalente
4. Persistir en `land_use_changes` con upsert `ON CONFLICT (fire_event_id, change_detected_at)`
5. Retornar resultado

**Esqueleto de implementación:**

```python
@shared_task(
    bind=True,
    name='workers.tasks.destruction.detect_destruction',
    queue='vae',
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def detect_destruction(self, fire_event_id: str, check_date: str = None):
    """
    Detecta cambios de uso de suelo en áreas afectadas por incendios.
    
    Compara imágenes pre/post incendio vía VAEService y persiste en land_use_changes.
    Idempotente gracias a UNIQUE(fire_event_id, change_detected_at) + ON CONFLICT.
    """
    from app.db.session import SessionLocal
    from app.services.vae_service import VAEService
    from datetime import date
    
    db = SessionLocal()
    try:
        # 1. Obtener geometría
        event_query = text("""
            SELECT id, ST_AsGeoJSON(centroid)::json as centroid_geojson,
                   ST_AsGeoJSON(perimeter)::json as perimeter_geojson,
                   start_date
            FROM fire_events WHERE id = :event_id
        """)
        event = db.execute(event_query, {"event_id": fire_event_id}).fetchone()
        
        if not event:
            logger.error(f"Fire event {fire_event_id} not found")
            return {"status": "error", "message": "Event not found"}
        
        # 2. Ejecutar detección
        vae_service = VAEService()
        detection_date = date.fromisoformat(check_date) if check_date else date.today()
        
        try:
            result = vae_service.detect_land_use_change(
                fire_event_id=fire_event_id,
                geometry=event.perimeter_geojson or event.centroid_geojson,
                check_date=detection_date,
            )
        except Exception as gee_exc:
            logger.warning(f"GEE destruction detection failed for {fire_event_id}: {gee_exc}")
            raise self.retry(exc=gee_exc)
        
        # 3. Persistir con upsert
        if result.get("change_detected", False):
            # Calcular months_after_fire
            months_after = None
            if event.start_date:
                start = event.start_date.date() if hasattr(event.start_date, 'date') else event.start_date
                months_after = max(0, (detection_date - start).days // 30)
            
            upsert_query = text("""
                INSERT INTO land_use_changes (
                    fire_event_id, change_detected_at, months_after_fire,
                    change_type, change_severity, affected_area_hectares,
                    is_potential_violation, violation_confidence,
                    status, notes
                ) VALUES (
                    :fire_event_id, :change_detected_at, :months_after_fire,
                    :change_type, :change_severity, :affected_area_hectares,
                    :is_potential_violation, :violation_confidence,
                    'pending_review', :notes
                )
                ON CONFLICT (fire_event_id, change_detected_at) DO UPDATE SET
                    change_type = EXCLUDED.change_type,
                    change_severity = EXCLUDED.change_severity,
                    affected_area_hectares = EXCLUDED.affected_area_hectares,
                    is_potential_violation = EXCLUDED.is_potential_violation,
                    violation_confidence = EXCLUDED.violation_confidence,
                    notes = EXCLUDED.notes,
                    updated_at = NOW()
                RETURNING id
            """)
            
            db.execute(upsert_query, {
                "fire_event_id": fire_event_id,
                "change_detected_at": detection_date,
                "months_after_fire": months_after,
                "change_type": result.get("change_type", "unknown"),
                "change_severity": result.get("change_severity"),
                "affected_area_hectares": result.get("affected_area_hectares"),
                "is_potential_violation": result.get("is_potential_violation", False),
                "violation_confidence": result.get("violation_confidence"),
                "notes": result.get("notes"),
            })
            db.commit()
        
        logger.info(f"Destruction detection completed for event {fire_event_id}: change={result.get('change_detected')}")
        return {"status": "success", "fire_event_id": fire_event_id, "change_detected": result.get("change_detected", False)}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Destruction detection failed for {fire_event_id}: {e}")
        raise
    finally:
        db.close()
```

**Nota para Claude Code:** inspeccionar la firma real de `detect_land_use_change` en `vae_service.py`:
```bash
grep -n "def detect_land_use\|def detect_destruction\|def check_land_use" app/services/vae_service.py
```

**Verificación:**
```bash
python3 -c "
content = open('workers/tasks/destruction.py').read()
assert 'ON CONFLICT' in content, 'Missing upsert'
assert 'VAEService' in content, 'Not using VAEService'
assert 'hardcoded' not in content.lower(), 'Still has hardcoded comment'
print('PASS: destruction worker rewritten correctly')
"
```

---

### TAREA 1.3: consolidar configuración de Celery y cola vae

**Archivos:**
- `workers/celery_app.py` (principal — este es el que usa docker-compose)
- `celery_app.py` (raíz — alternativo, puede tener configuración divergente)

**Estado actual:** 
- `workers/celery_app.py` rutas: recovery y destruction → cola `analysis`
- `celery_app.py` (raíz) rutas: recovery y destruction → cola `vae`
- docker-compose no inicia worker para cola `vae`
- El trigger enqueue a `queue="vae"` explícitamente

**Acción:**

1. Inspeccionar ambos archivos:
```bash
grep -n "task_routes\|queue.*vae\|queue.*analysis" workers/celery_app.py celery_app.py
```

2. En `workers/celery_app.py`, actualizar las rutas para que recovery y destruction usen cola `vae`:
```python
# Buscar el dict task_routes y cambiar:
# ANTES:
'workers.tasks.recovery.*': {'queue': 'analysis'},
'workers.tasks.destruction.*': {'queue': 'analysis'},
# DESPUÉS:
'workers.tasks.recovery.*': {'queue': 'vae'},
'workers.tasks.destruction.*': {'queue': 'vae'},
```

3. En `celery_app.py` (raíz), alinear con la misma configuración o agregar un comentario que indique que el archivo runtime es `workers/celery_app.py`.

**Verificación:**
```bash
grep -n "vae\|analysis" workers/celery_app.py | grep -i "recovery\|destruction"
# Debe mostrar que ambas tareas apuntan a 'vae'
```

---

### TAREA 1.4: agregar worker vae en docker-compose

**Archivo:** `docker-compose.yml`
**Referencia:** buscar el servicio `worker-analysis` (aprox. línea 258) y usarlo como template.

**Acción:** agregar un nuevo servicio `worker-vae` basado en `worker-analysis`:

```yaml
  worker-vae:
    image: ${DOCKER_IMAGE:-ghcr.io/your-org/forestguard-api:latest}
    container_name: forestguard-worker-vae
    restart: unless-stopped
    command: celery -A workers.celery_app worker --loglevel=info -Q vae -c 1 --max-tasks-per-child=100
    depends_on:
      - redis
    environment:
      # Copiar las mismas variables de entorno que worker-analysis
      # IMPORTANTE: incluir GEE_PROJECT_ID, GEE_SERVICE_ACCOUNT_EMAIL, GEE_PRIVATE_KEY_PATH
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
      ENVIRONMENT: ${ENVIRONMENT:-production}
      GEE_PROJECT_ID: ${GEE_PROJECT_ID:-}
      GEE_SERVICE_ACCOUNT_EMAIL: ${GEE_SERVICE_ACCOUNT_EMAIL:-}
      GEE_PRIVATE_KEY_PATH: ${GEE_PRIVATE_KEY_PATH:-/run/secrets/gcp-sa.json}
    volumes:
      # Mismos volumes que worker-analysis
      - ./workers:/app/workers
      - ./app:/app/app
    networks:
      - forestguard-net
```

**Nota para Claude Code:** copiar exactamente las mismas environment variables y volumes que tiene `worker-analysis`. Inspeccionar primero:
```bash
grep -A 30 "worker-analysis:" docker-compose.yml | head -40
```

**Verificación:**
```bash
grep -c "worker-vae" docker-compose.yml
# Debe ser >= 1
grep "Q vae" docker-compose.yml
# Debe existir la línea con -Q vae
```

---

### TAREA 1.5: corregir query `anomaly_type` en endpoint summary

**Archivo:** `app/api/routes/monitoring.py`
**Línea de referencia:** ~196 (query SQL del endpoint GET /monitoring/recovery/summary)

**Estado actual:** la query usa `vm.anomaly_type` que no existe en schema v5.

**Acción:**

1. Buscar la referencia a `anomaly_type`:
```bash
grep -n "anomaly_type" app/api/routes/monitoring.py
```

2. Reemplazar `anomaly_type` por `activity_type` en la query SQL.

3. Buscar la lógica que usa `anomaly_type` para determinar `is_suspicious` (aprox. líneas 258-266) y adaptarla para usar `activity_type` y `human_activity_detected`:

```python
# ANTES (aproximado):
is_suspicious = row.anomaly_type is not None

# DESPUÉS:
is_suspicious = row.human_activity_detected is True or row.activity_type is not None
```

**Verificación:**
```bash
grep -n "anomaly_type" app/api/routes/monitoring.py
# Debe retornar 0 líneas
grep -n "activity_type" app/api/routes/monitoring.py
# Debe retornar al menos 1 línea
```

---

### TAREA 1.6: corregir parametrización de INTERVAL en summary

**Archivo:** `app/api/routes/monitoring.py`
**Línea de referencia:** ~208

**Estado actual:**
```sql
AND fe.start_date < NOW() - INTERVAL ':min_months months'
```

**Acción:** reemplazar por:
```sql
AND fe.start_date < NOW() - (INTERVAL '1 month' * :min_months)
```

**Verificación:**
```bash
grep -n "INTERVAL" app/api/routes/monitoring.py
# No debe contener ':min_months months' entre comillas simples
# Debe contener "INTERVAL '1 month' * :min_months"
```

---

### TAREA 1.7: implementar reintento con ventana extendida por nubosidad

**Archivo:** `app/services/vae_service.py`
**Línea de referencia:** ~709-722 (método `_get_current_ndvi`)

**Estado actual:** usa `max_cloud_cover=30` fijo. Si no hay imagen, lanza excepción sin reintento.

**Acción:** implementar fallback escalonado:

```python
def _get_current_ndvi(self, bbox, target_date, ...):
    """Obtiene NDVI actual con fallback escalonado por nubosidad."""
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
                # ... procesar y retornar
                return ndvi_result
            except GEEImageNotFoundError:
                continue
    
    raise GEEImageNotFoundError(
        f"No suitable image found for date {target_date} "
        f"after trying cloud thresholds {cloud_thresholds} "
        f"and window options {window_days_options}"
    )
```

**Nota para Claude Code:** inspeccionar la firma exacta de `_get_current_ndvi` y `get_sentinel_collection` antes de modificar:
```bash
grep -n "def _get_current_ndvi\|def get_sentinel_collection" app/services/vae_service.py app/services/gee_service.py
```

**Verificación:**
```bash
grep -n "cloud_thresholds\|window_days_options\|fallback" app/services/vae_service.py
# Debe tener al menos una referencia al patrón de fallback
```

---

### TAREA 1.8: migrar endpoint GET recovery de GEE-tiempo-real a lectura de BD

**Archivo:** `app/api/routes/monitoring.py`
**Línea de referencia:** ~328-425 (endpoint GET /monitoring/recovery/{fire_event_id})

**Estado actual:** el endpoint instancia `VAEService()` y llama a GEE en tiempo real (37 requests por petición). Si no hay datos en BD, ejecuta el análisis on-the-fly.

**Acción:** modificar para que SOLO lea de `vegetation_monitoring`:

```python
@router.get("/recovery/{fire_event_id}")
async def get_recovery(fire_event_id: str, db: Session = Depends(get_db)):
    """
    Retorna datos de recuperación vegetativa desde vegetation_monitoring.
    Si no hay datos, retorna status 'pending' sin ejecutar GEE.
    """
    # 1. Verificar que el evento existe
    event = db.execute(
        text("SELECT id, start_date FROM fire_events WHERE id = :id"),
        {"id": fire_event_id}
    ).fetchone()
    
    if not event:
        raise HTTPException(status_code=404, detail="Fire event not found")
    
    # 2. Leer datos de vegetation_monitoring
    monitoring_data = db.execute(
        text("""
            SELECT monitoring_date, months_after_fire, ndvi_mean, ndvi_min, ndvi_max,
                   ndvi_std_dev, baseline_ndvi, recovery_percentage,
                   land_use_classification, human_activity_detected, activity_type
            FROM vegetation_monitoring
            WHERE fire_event_id = :event_id
            ORDER BY monitoring_date ASC
        """),
        {"event_id": fire_event_id}
    ).fetchall()
    
    if not monitoring_data:
        return {
            "fire_event_id": fire_event_id,
            "recovery_status": "pending",
            "monitoring_data": [],
            "message": "No monitoring data available yet. Analysis is scheduled."
        }
    
    # 3. Clasificar estado desde el último registro
    latest = monitoring_data[-1]
    recovery_status = _classify_status(latest)
    
    return {
        "fire_event_id": fire_event_id,
        "recovery_status": recovery_status,
        "baseline_ndvi": latest.baseline_ndvi,
        "current_ndvi": latest.ndvi_mean,
        "recovery_percentage": latest.recovery_percentage,
        "monitoring_data": [
            {
                "date": str(row.monitoring_date),
                "month": row.months_after_fire,
                "ndvi_mean": row.ndvi_mean,
                "baseline_ndvi": row.baseline_ndvi,
                "recovery_percentage": row.recovery_percentage,
                "cloud_cover_pct": None,  # No almacenado actualmente
            }
            for row in monitoring_data
        ],
    }
```

**Verificación:**
```bash
grep -n "VAEService\|vae_service\|get_recovery_timeline" app/api/routes/monitoring.py
# El endpoint GET recovery NO debe instanciar VAEService
# Solo el POST trigger y los workers deben usar VAEService
```

---

## FASE 2 — Seguridad (ejecutar en paralelo con fase 1)

### TAREA 2.1: agregar autenticación JWT al router de monitoring

**Archivo:** `app/main.py`
**Línea de referencia:** ~236-240 (include_router de monitoring)

**Estado actual:**
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    # SIN dependencies
)
```

**Acción:**
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_user)],
)
```

**Nota:** verificar que `get_current_user` ya está importado en `main.py`:
```bash
grep -n "get_current_user" app/main.py
```
Si no está importado, agregar:
```python
from app.api.auth_deps import get_current_user
```

**Verificación:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/monitoring/recovery/summary
# Esperado: 401 (antes era 200)
```

---

### TAREA 2.2: sanitizar error messages de GEE

**Archivo:** `app/api/routes/monitoring.py`
**Línea de referencia:** ~423 y cualquier otro `raise HTTPException` que use `str(e)`

**Acción:** buscar todos los `HTTPException` que expongan `str(e)`:

```bash
grep -n "str(e)\|str(exc)" app/api/routes/monitoring.py
```

Reemplazar cada uno por un mensaje genérico:

```python
# ANTES:
raise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")

# DESPUÉS:
logger.error(f"NDVI analysis error for {fire_event_id}: {e}", exc_info=True)
raise HTTPException(status_code=503, detail="Vegetation analysis service temporarily unavailable")
```

**Verificación:**
```bash
grep -n "str(e)\|str(exc)" app/api/routes/monitoring.py | grep -i "HTTPException\|detail"
# Debe retornar 0 líneas
```

---

### TAREA 2.3: implementar endpoint POST /trigger con auth admin + rate limit

**Archivo:** `app/api/routes/monitoring.py`

**Estado actual según AS-IS:** el endpoint YA existe (línea ~588) pero necesita verificación.

**Acción:**

1. Verificar que el trigger existe y tiene auth + rate limit:
```bash
grep -n "def trigger\|POST.*trigger\|@router.post" app/api/routes/monitoring.py
```

2. Si existe, verificar que:
   - Usa `Depends(get_current_user)` con verificación de rol admin
   - Tiene rate limiting (protección de cuota GEE)
   - Encola a `queue='vae'` (no `analysis`)
   - Retorna 202 (Accepted), no 200

3. Si el trigger encola a `queue='analysis'`, cambiar a `queue='vae'`:
```bash
grep -n "queue=" app/api/routes/monitoring.py
```

**Verificación:**
```bash
grep -A 5 "trigger" app/api/routes/monitoring.py | grep -i "queue\|admin\|rate\|current_user"
# Debe mostrar: queue='vae', admin check, rate limit o current_user dependency
```

---

### TAREA 2.4: agregar tarea Celery Beat para procesamiento periódico VAE

**Archivo:** `workers/celery_app.py` (sección `beat_schedule`)

**Acción:** agregar una tarea periódica para ejecutar análisis VAE automáticamente:

```python
# Agregar al beat_schedule existente:
'vae-recovery-monthly': {
    'task': 'workers.tasks.recovery.batch_recovery_analysis',
    'schedule': crontab(hour=5, minute=0, day_of_month=1),  # 05:00 UTC del día 1 de cada mes
    'options': {'queue': 'vae'},
},
'vae-destruction-monthly': {
    'task': 'workers.tasks.destruction.batch_destruction_detection',
    'schedule': crontab(hour=6, minute=0, day_of_month=1),  # 06:00 UTC del día 1 de cada mes
    'options': {'queue': 'vae'},
},
```

**Nota:** si las funciones `batch_recovery_analysis` y `batch_destruction_detection` no existen aún, crearlas como tareas que:
1. Consultan todos los `fire_events` activos con `start_date > NOW() - INTERVAL '36 months'`
2. Para cada uno, encolan `analyze_recovery.delay(event_id)` y `detect_destruction.delay(event_id)`
3. Con batching de max 50 eventos por ejecución para proteger la cuota GEE

**Verificación:**
```bash
grep -n "vae-recovery\|vae-destruction\|batch_recovery\|batch_destruction" workers/celery_app.py
# Debe existir al menos una referencia
```

---

## FASE 3 — Frontend: alinear contratos y UX

### TAREA 3.1: unificar taxonomía de estados de recovery

**Archivos:**
- `app/api/routes/monitoring.py` → función `_classify_status` (~línea 185)
- `frontend/src/components/monitoring/RecoveryStatusBadge.tsx` (~línea 4-33)

**Estado actual:**
- Backend emite: `excellent, good, moderate, poor, critical, suspicious, unknown, pending`
- Frontend espera: `not_started, early_recovery, moderate_recovery, advanced_recovery, full_recovery, stalled, anomaly_detected, pending`

**Acción — OPCIÓN A (preferida): adaptar el backend para emitir los enums que el frontend espera.**

Modificar `_classify_status` en `monitoring.py`:

```python
def _classify_status(row) -> str:
    """
    Clasifica el estado de recuperación según datos del último registro.
    Retorna valores alineados con RecoveryStatusBadge del frontend.
    """
    if row is None:
        return "pending"
    
    recovery_pct = getattr(row, 'recovery_percentage', None)
    human_activity = getattr(row, 'human_activity_detected', False)
    
    if human_activity:
        return "anomaly_detected"
    
    if recovery_pct is None:
        return "pending"
    
    if recovery_pct >= 90:
        return "full_recovery"
    elif recovery_pct >= 70:
        return "advanced_recovery"
    elif recovery_pct >= 40:
        return "moderate_recovery"
    elif recovery_pct >= 10:
        return "early_recovery"
    elif recovery_pct >= 0:
        return "stalled"
    else:
        return "not_started"
```

**Verificación:**
```bash
# Backend
grep -n "excellent\|good.*recovery\|poor\|critical" app/api/routes/monitoring.py
# No debe haber referencias a la taxonomía anterior

# Frontend
grep -n "early_recovery\|full_recovery\|anomaly_detected" frontend/src/components/monitoring/RecoveryStatusBadge.tsx
# Debe tener estos valores configurados
```

---

### TAREA 3.2: adaptar NdviChart al formato real de la API

**Archivo:** `frontend/src/components/ndvi-chart.tsx` (o `frontend/src/components/monitoring/NdviChart.tsx`)

**Estado actual:** espera `{ month: string; value: number }[]`
**API retorna:** `{ date: string; month: int; ndvi_mean: float; baseline_ndvi: float; recovery_percentage: float }`

**Acción:**

1. Localizar el componente:
```bash
find frontend/src -name "*ndvi*" -o -name "*Ndvi*" | head -5
```

2. Actualizar la interfaz de props:

```typescript
interface NdviDataPoint {
  date: string;
  month: number;
  ndvi_mean: number;
  baseline_ndvi: number | null;
  recovery_percentage: number | null;
  cloud_cover_pct: number | null;
}

interface NdviChartProps {
  data: NdviDataPoint[];
  baselineNdvi?: number;
}
```

3. Modificar el componente para:
   - Usar `ndvi_mean` como valor principal del eje Y
   - Agregar `ReferenceLine` dinámica con `baselineNdvi` (línea punteada)
   - Agregar gradiente de color por zona: verde (>70%), amarillo (40-70%), rojo (<40%)
   - Agregar tooltip con `recovery_percentage` y `date`
   - Usar Framer Motion para animación de entrada si está disponible

```tsx
// Ejemplo de áreas de referencia con gradiente
<ReferenceArea y1={0} y2={0.3} fill="#fee2e2" fillOpacity={0.3} /> {/* Zona roja */}
<ReferenceArea y1={0.3} y2={0.5} fill="#fef3c7" fillOpacity={0.3} /> {/* Zona amarilla */}
<ReferenceArea y1={0.5} y2={1.0} fill="#dcfce7" fillOpacity={0.3} /> {/* Zona verde */}

{baselineNdvi && (
  <ReferenceLine
    y={baselineNdvi}
    stroke="#6b7280"
    strokeDasharray="5 5"
    label={{ value: 'Baseline', position: 'right', fill: '#6b7280', fontSize: 12 }}
  />
)}
```

**Verificación:**
```bash
grep -n "ndvi_mean\|baseline_ndvi\|recovery_percentage" frontend/src/components/*ndvi* frontend/src/components/monitoring/*ndvi* 2>/dev/null
# Debe tener referencias a los campos reales de la API
```

---

### TAREA 3.3: integrar RecoveryStatusBadge en el fire-card activo del feed

**Archivos:**
- `frontend/src/pages/Home.tsx` (~línea 13, importa fire-card)
- `frontend/src/components/fires/fire-card.tsx` (o equivalente usado por Home)

**Estado actual:** Home usa `components/fires/fire-card` que NO tiene badge de recovery. El `components/fire-card.tsx` con badge no se usa en ninguna ruta.

**Acción:**

1. Identificar qué componente usa Home:
```bash
grep -n "import.*fire-card\|import.*FireCard\|import.*EpisodeCard" frontend/src/pages/Home.tsx
```

2. En el componente identificado, agregar `RecoveryStatusBadge` condicional:

```tsx
import { RecoveryStatusBadge } from '../monitoring/RecoveryStatusBadge';
import { useAuth } from '../../hooks/useAuth';

// Dentro del componente, agregar:
const { isAuthenticated } = useAuth();

// En el JSX, después del badge de severity:
{isAuthenticated && recoveryStatus && (
  <RecoveryStatusBadge status={recoveryStatus} />
)}
```

**Nota:** el `recoveryStatus` debe venir de los datos del endpoint. Si el endpoint de listado no incluye recovery_status, hay que agregarlo como campo calculado o hacer un fetch adicional. Evaluar si vale la pena el fetch extra por card vs. un campo agregado en el endpoint de episodios.

**Verificación:**
```bash
grep -n "RecoveryStatusBadge" frontend/src/components/fires/fire-card.tsx frontend/src/components/fires/*.tsx 2>/dev/null
# Debe existir la importación
```

---

### TAREA 3.4: agregar marcador diferenciado en mapa para violaciones

**Archivos:**
- `frontend/src/components/map/layers/FireMarkers.tsx` (~línea 27, 93)
- `frontend/src/pages/MapPage.tsx` (~línea 77, construcción de map items)
- `frontend/src/types/map.ts` (~línea 18, tipo MapItem)

**Acción:**

1. En `types/map.ts`, agregar campo `is_potential_violation`:
```typescript
// Agregar al tipo MapItem (o equivalente):
is_potential_violation?: boolean;
```

2. En `MapPage.tsx`, alimentar el campo desde los datos (si el endpoint lo provee):
```typescript
// En la construcción del map item (~línea 77):
is_potential_violation: episode.is_potential_violation ?? false,
```

3. En `FireMarkers.tsx`, usar el campo para ícono diferenciado:
```typescript
// En la función que determina el ícono (~línea 27):
if (item.is_potential_violation) {
  return violationIcon; // Ícono rojo con signo de alerta
}
```

**Crear el ícono de violación:**
```typescript
const violationIcon = L.divIcon({
  className: 'violation-marker',
  html: `<div class="w-6 h-6 bg-red-600 rounded-full border-2 border-white flex items-center justify-center shadow-lg animate-pulse">
    <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92z" />
    </svg>
  </div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});
```

**Verificación:**
```bash
grep -n "is_potential_violation\|violation" frontend/src/components/map/layers/FireMarkers.tsx
# Debe tener referencia al campo
grep -n "is_potential_violation" frontend/src/types/map.ts
# Debe estar en el tipo
```

---

### TAREA 3.5: implementar skeleton loading y empty state en RecoveryPanel

**Archivo:** `frontend/src/components/monitoring/RecoveryPanel.tsx`

**Acción:** mejorar los estados de carga y vacío para UX estilo Instagram:

1. **Skeleton loading** — reemplazar spinner genérico por placeholders animados:

```tsx
// Componente de skeleton para el panel
const RecoverySkeleton = () => (
  <div className="space-y-4 animate-pulse">
    {/* Badge skeleton */}
    <div className="h-6 w-32 bg-gray-200 rounded-full" />
    
    {/* Metric cards skeleton */}
    <div className="grid grid-cols-3 gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-20 bg-gray-200 rounded-xl" />
      ))}
    </div>
    
    {/* Chart skeleton */}
    <div className="h-48 bg-gray-200 rounded-xl" />
    
    {/* Cards skeleton */}
    <div className="space-y-2">
      {[1, 2].map((i) => (
        <div key={i} className="h-16 bg-gray-200 rounded-lg" />
      ))}
    </div>
  </div>
);
```

2. **Empty state atractivo** — cuando `recovery_status === 'pending'`:

```tsx
const RecoveryEmptyState = () => (
  <div className="flex flex-col items-center justify-center py-12 px-6 text-center">
    {/* Ícono de planta creciendo */}
    <div className="w-16 h-16 bg-emerald-50 rounded-full flex items-center justify-center mb-4">
      <svg className="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
          d="M12 21c-4-4-8-7.5-8-11a8 8 0 0116 0c0 3.5-4 7-8 11z" />
      </svg>
    </div>
    <h3 className="text-sm font-medium text-gray-900 mb-1">
      Análisis de recuperación pendiente
    </h3>
    <p className="text-xs text-gray-500 max-w-xs">
      El monitoreo de vegetación se ejecuta mensualmente. Los datos estarán disponibles
      una vez que se procese el primer análisis NDVI para este evento.
    </p>
  </div>
);
```

**Verificación:**
```bash
grep -n "Skeleton\|animate-pulse\|EmptyState\|pendiente" frontend/src/components/monitoring/RecoveryPanel.tsx
# Debe tener referencias a skeleton y empty state
```

---

### TAREA 3.6: crear componente LandUseChangeCard

**Archivo:** `frontend/src/components/monitoring/LandUseChangeCard.tsx` (nuevo)

**Acción:** crear componente tipo tarjeta para mostrar cambios de uso de suelo detectados:

```tsx
import { motion } from 'framer-motion';

interface LandUseChange {
  id: string;
  change_type: string;
  change_severity: string | null;
  affected_area_hectares: number | null;
  is_potential_violation: boolean;
  violation_confidence: string | null;
  change_detected_at: string;
  months_after_fire: number | null;
  status: string;
  notes: string | null;
}

interface LandUseChangeCardProps {
  change: LandUseChange;
}

const severityConfig: Record<string, { color: string; bg: string }> = {
  high: { color: 'text-red-700', bg: 'bg-red-50 border-red-200' },
  medium: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200' },
  low: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200' },
};

export const LandUseChangeCard = ({ change }: LandUseChangeCardProps) => {
  const severity = severityConfig[change.change_severity ?? 'low'] ?? severityConfig.low;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border p-4 ${severity.bg} transition-shadow hover:shadow-md`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-sm font-medium ${severity.color}`}>
              {change.change_type}
            </span>
            {change.is_potential_violation && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                ⚠ Posible violación
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500">
            Detectado: {new Date(change.change_detected_at).toLocaleDateString('es-AR')}
            {change.months_after_fire != null && ` · ${change.months_after_fire} meses post-incendio`}
          </p>
        </div>
        {change.affected_area_hectares != null && (
          <span className="text-sm font-semibold text-gray-700">
            {change.affected_area_hectares.toFixed(1)} ha
          </span>
        )}
      </div>
      {change.notes && (
        <p className="mt-2 text-xs text-gray-600">{change.notes}</p>
      )}
    </motion.div>
  );
};
```

**Verificación:**
```bash
test -f frontend/src/components/monitoring/LandUseChangeCard.tsx && echo "PASS: file exists" || echo "FAIL: file missing"
grep -n "is_potential_violation\|change_type\|affected_area" frontend/src/components/monitoring/LandUseChangeCard.tsx
# Debe tener referencias a los campos de la API
```

---

## FASE 4 — Escalabilidad y limpieza

### TAREA 4.1: definir estrategia de backfill con batching

**Archivo:** `workers/tasks/recovery.py`

**Acción:** crear función `batch_recovery_analysis` si no existe:

```python
@shared_task(
    name='workers.tasks.recovery.batch_recovery_analysis',
    queue='vae',
)
def batch_recovery_analysis(max_events: int = 50):
    """
    Ejecuta análisis de recuperación para todos los eventos activos.
    Limita a max_events por ejecución para proteger cuota GEE.
    Programada mensualmente vía Celery Beat.
    """
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        # Obtener eventos que necesitan análisis (activos, < 36 meses)
        events = db.execute(text("""
            SELECT fe.id
            FROM fire_events fe
            WHERE fe.start_date > NOW() - INTERVAL '36 months'
              AND fe.status IN ('active', 'monitoring', 'contained')
              AND fe.centroid IS NOT NULL
            ORDER BY fe.start_date DESC
            LIMIT :max_events
        """), {"max_events": max_events}).fetchall()
        
        enqueued = 0
        for event in events:
            analyze_recovery.delay(str(event.id))
            enqueued += 1
        
        logger.info(f"Batch recovery: enqueued {enqueued} events for analysis")
        return {"enqueued": enqueued}
    finally:
        db.close()
```

Y lo mismo para destruction en `workers/tasks/destruction.py`:

```python
@shared_task(
    name='workers.tasks.destruction.batch_destruction_detection',
    queue='vae',
)
def batch_destruction_detection(max_events: int = 50):
    """Ejecuta detección de cambios de uso para eventos activos."""
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        events = db.execute(text("""
            SELECT fe.id
            FROM fire_events fe
            WHERE fe.start_date > NOW() - INTERVAL '36 months'
              AND fe.status IN ('active', 'monitoring', 'contained')
              AND fe.centroid IS NOT NULL
            ORDER BY fe.start_date DESC
            LIMIT :max_events
        """), {"max_events": max_events}).fetchall()
        
        enqueued = 0
        for event in events:
            detect_destruction.delay(str(event.id))
            enqueued += 1
        
        logger.info(f"Batch destruction: enqueued {enqueued} events")
        return {"enqueued": enqueued}
    finally:
        db.close()
```

**Verificación:**
```bash
grep -n "batch_recovery_analysis\|batch_destruction_detection" workers/tasks/recovery.py workers/tasks/destruction.py
# Debe existir en ambos archivos
```

---

### TAREA 4.2: resolver conflicto de nomenclatura UC-12 vs UC-F12

**Archivo:** `app/main.py`
**Línea de referencia:** ~123-126 (tag OpenAPI de visitor-logs)

**Acción:** crear un tag OpenAPI separado para monitoring/VAE:

```python
# Buscar la sección de tags en main.py y agregar:
{
    "name": "monitoring",
    "description": "**Vegetation Recovery & Land Use (UC-F12/VAE)** — NDVI monitoring and land-use change detection."
},
```

Y en el include_router de monitoring, asegurar que usa tag `"monitoring"`:
```python
app.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],  # ← NO "visitor-logs"
    dependencies=[Depends(get_current_user)],
)
```

**Verificación:**
```bash
grep -n "monitoring\|UC-F12\|VAE" app/main.py | grep -i "tag\|description"
# Debe existir un tag separado para monitoring
```

---

### TAREA 4.3: documentar fórmula de recovery_percentage

**Archivo:** `app/services/vae_service.py` (docstring del método)

**Acción:** en el método que calcula `recovery_percentage` (~línea 302), agregar documentación explícita:

```python
def _calculate_recovery_percentage(self, current_ndvi: float, baseline_ndvi: float) -> float:
    """
    Calcula el porcentaje de recuperación vegetativa.
    
    Fórmula: (current_ndvi / baseline_ndvi) * 100
    
    NOTA: esta fórmula mide el "porcentaje del NDVI baseline alcanzado",
    NO el "porcentaje recuperado desde el nadir post-incendio".
    Ejemplo: baseline=0.6, nadir=0.1, actual=0.35 → resultado=58%
    (la recuperación real desde el nadir sería 50%)
    
    Se mantiene esta fórmula por consistencia con datos existentes.
    Si se desea cambiar a la fórmula de recuperación real, usar:
    recovery_pct = (current - nadir) / (baseline - nadir) * 100
    """
    if baseline_ndvi is None or baseline_ndvi == 0:
        return 0.0
    return min(100.0, max(0.0, (current_ndvi / baseline_ndvi) * 100))
```

**Verificación:**
```bash
grep -A 5 "recovery_percentage\|recovery_pct" app/services/vae_service.py | grep -i "baseline\|nadir\|fórmula\|nota"
# Debe tener documentación explícita
```

---

## Verificación final post-implementación

### Checklist de regresión

```bash
# 1. Auth obligatoria en monitoring
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/monitoring/recovery/summary
# Esperado: 401

# 2. Cola vae configurada
grep "Q vae" docker-compose.yml
# Debe existir

# 3. Workers sin hardcoded values
grep -rn "45.7\|0.23\|hardcoded" workers/tasks/recovery.py workers/tasks/destruction.py
# Debe retornar 0 líneas

# 4. anomaly_type eliminado
grep -rn "anomaly_type" app/api/routes/monitoring.py
# Debe retornar 0 líneas

# 5. Error messages sanitizados
grep -n "str(e)" app/api/routes/monitoring.py | grep -i "detail"
# Debe retornar 0 líneas

# 6. Frontend contract alineado
grep -rn "early_recovery\|full_recovery\|anomaly_detected" frontend/src/components/monitoring/
# Debe tener múltiples referencias

# 7. New components exist
test -f frontend/src/components/monitoring/LandUseChangeCard.tsx && echo "OK" || echo "MISSING"

# 8. Celery Beat schedule
grep -n "vae-recovery\|vae-destruction" workers/celery_app.py
# Debe existir

# 9. Violation markers
grep -n "is_potential_violation" frontend/src/components/map/layers/FireMarkers.tsx frontend/src/types/map.ts
# Debe existir en ambos archivos
```

### Integridad de schema (ejecutar contra BD)

```sql
-- UNIQUE constraints
SELECT conname FROM pg_constraint 
WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u';
-- Esperado: uq_vm_event_date

SELECT conname FROM pg_constraint 
WHERE conrelid = 'land_use_changes'::regclass AND contype = 'u';
-- Esperado: uq_luc_event_detected

-- RLS activa
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('vegetation_monitoring', 'land_use_changes');
-- Esperado: 4 políticas (2 por tabla)

-- Índices
SELECT indexname FROM pg_indexes 
WHERE tablename IN ('vegetation_monitoring', 'land_use_changes')
ORDER BY tablename, indexname;
```

---

## Resumen de archivos modificados

| Archivo | Tipo de cambio | Fase |
|---------|---------------|------|
| `database/migrations/2026_02_24_uc_f12_vae_complementary.sql` | Nuevo (si necesario) | 0 |
| `workers/tasks/recovery.py` | Reescritura mayor | 1 |
| `workers/tasks/destruction.py` | Reescritura mayor | 1 |
| `workers/celery_app.py` | Modificar rutas + beat schedule | 1, 2 |
| `celery_app.py` (raíz) | Alinear o documentar | 1 |
| `docker-compose.yml` | Agregar servicio worker-vae | 1 |
| `app/api/routes/monitoring.py` | Múltiples correcciones | 1, 2 |
| `app/services/vae_service.py` | Nubosidad fallback + docs | 1 |
| `app/main.py` | Auth + tag OpenAPI | 2, 4 |
| `frontend/src/components/monitoring/RecoveryStatusBadge.tsx` | Sin cambio (verificar) | 3 |
| `frontend/src/components/ndvi-chart.tsx` | Adaptar interfaz | 3 |
| `frontend/src/components/fires/fire-card.tsx` | Agregar badge | 3 |
| `frontend/src/components/map/layers/FireMarkers.tsx` | Violation icon | 3 |
| `frontend/src/pages/MapPage.tsx` | Alimentar violation flag | 3 |
| `frontend/src/types/map.ts` | Agregar campo | 3 |
| `frontend/src/components/monitoring/RecoveryPanel.tsx` | Skeleton + empty state | 3 |
| `frontend/src/components/monitoring/LandUseChangeCard.tsx` | Nuevo | 3 |
