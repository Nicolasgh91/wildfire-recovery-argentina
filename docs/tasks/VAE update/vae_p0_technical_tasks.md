# Tareas técnicas: fases F1 a F4 (prioridad P0)

Fecha: 2026-03-12
Referencia: `vae_module_specification.md` secciones 4, 5.1, 7.3
Formato: tareas ejecutables por Claude Code con archivos, líneas y verificación

---

## F1: migración de schema

**Estado:** Completada 2026-03-12.  
F1-01, F1-02, F1-03 y RLS (auth/service_role) ya estaban aplicados vía `2026_02_23_uc_f12_vae_monitoring.sql`. Se aplicó `2026_03_13_vae_schema_hardening.sql` para F1-04 (columnas nuevas) y F1-05 (política `anon_read_vegetation`). Ver `VAE_tech_debt.md` TD-001, TD-002.

---

### F1-01: UNIQUE constraints para idempotencia

**Archivo:** nueva migración SQL
**Ruta sugerida:** `database/migrations/2026_03_13_vae_schema_hardening.sql`

```sql
-- F1-01a: UNIQUE constraint en vegetation_monitoring
ALTER TABLE vegetation_monitoring
  ADD CONSTRAINT uq_vm_event_date UNIQUE (fire_event_id, monitoring_date);

-- F1-01b: UNIQUE constraint en land_use_changes
ALTER TABLE land_use_changes
  ADD CONSTRAINT uq_luc_event_date UNIQUE (fire_event_id, change_detected_at);
```

**Verificación:**
```sql
SELECT conname FROM pg_constraint
WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u';
-- Esperado: uq_vm_event_date

SELECT conname FROM pg_constraint
WHERE conrelid = 'land_use_changes'::regclass AND contype = 'u';
-- Esperado: uq_luc_event_date
```

**Riesgo:** si existen registros duplicados en producción, el ALTER falla. Pre-check obligatorio:
```sql
-- Ejecutar ANTES de la migración
SELECT fire_event_id, monitoring_date, COUNT(*)
FROM vegetation_monitoring
GROUP BY fire_event_id, monitoring_date
HAVING COUNT(*) > 1;

SELECT fire_event_id, change_detected_at, COUNT(*)
FROM land_use_changes
GROUP BY fire_event_id, change_detected_at
HAVING COUNT(*) > 1;
```
Si hay duplicados: conservar el registro más reciente (`MAX(updated_at)`) y eliminar el resto antes de aplicar el constraint.

---

### F1-02: índices de performance

**Archivo:** misma migración `2026_03_13_vae_schema_hardening.sql`

```sql
-- F1-02a: índice compuesto para queries de timeline
CREATE INDEX IF NOT EXISTS idx_vm_event_date
  ON vegetation_monitoring(fire_event_id, monitoring_date);

-- F1-02b: índice para queries por meses post-incendio
CREATE INDEX IF NOT EXISTS idx_vm_event_months
  ON vegetation_monitoring(fire_event_id, months_after_fire);

-- F1-02c: índice para queries de land_use_changes
CREATE INDEX IF NOT EXISTS idx_luc_event
  ON land_use_changes(fire_event_id, change_detected_at);
```

**Verificación:**
```sql
SELECT indexname FROM pg_indexes
WHERE tablename = 'vegetation_monitoring'
  AND indexname IN ('idx_vm_event_date', 'idx_vm_event_months');
-- Esperado: 2 filas
```

---

### F1-03: FK faltante + NOT NULL

**Archivo:** misma migración

```sql
-- F1-03a: FK en monitoring_record_id
ALTER TABLE land_use_changes
  ADD CONSTRAINT land_use_changes_monitoring_record_id_fkey
  FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id);

-- F1-03b: NOT NULL en is_potential_violation
-- Pre-check: asegurar que no hay nulls
UPDATE land_use_changes SET is_potential_violation = false
WHERE is_potential_violation IS NULL;

ALTER TABLE land_use_changes
  ALTER COLUMN is_potential_violation SET NOT NULL;
```

**Riesgo F1-03a:** si existen `monitoring_record_id` que apuntan a IDs inexistentes, el ALTER falla. Pre-check:
```sql
SELECT id, monitoring_record_id FROM land_use_changes
WHERE monitoring_record_id IS NOT NULL
  AND monitoring_record_id NOT IN (SELECT id FROM vegetation_monitoring);
```
Si hay huérfanos: setear a NULL antes de aplicar FK.

---

### F1-04: nuevas columnas

**Archivo:** misma migración

```sql
-- F1-04a: confidence_score numérico para land_use_changes
ALTER TABLE land_use_changes
  ADD COLUMN IF NOT EXISTS confidence_score real;

-- F1-04b: pending_reason para vegetation_monitoring
ALTER TABLE vegetation_monitoring
  ADD COLUMN IF NOT EXISTS pending_reason varchar(50);

-- F1-04c: campos cacheados en fire_events para badge en listado
ALTER TABLE fire_events
  ADD COLUMN IF NOT EXISTS latest_recovery_status varchar,
  ADD COLUMN IF NOT EXISTS latest_recovery_pct real;
```

**Verificación:**
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'land_use_changes' AND column_name = 'confidence_score';
-- Esperado: 1 fila

SELECT column_name FROM information_schema.columns
WHERE table_name = 'fire_events' AND column_name = 'latest_recovery_status';
-- Esperado: 1 fila
```

---

### F1-05: RLS diferenciada

**Archivo:** misma migración

```sql
-- F1-05a: RLS en vegetation_monitoring (lectura pública para badge + NDVI)
ALTER TABLE vegetation_monitoring ENABLE ROW LEVEL SECURITY;

CREATE POLICY "anon_read_vegetation" ON vegetation_monitoring
  FOR SELECT TO anon USING (true);

CREATE POLICY "auth_read_vegetation" ON vegetation_monitoring
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "system_write_vegetation" ON vegetation_monitoring
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- F1-05b: RLS en land_use_changes (solo autenticados leen, anon NO)
ALTER TABLE land_use_changes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auth_read_land_use" ON land_use_changes
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "system_write_land_use" ON land_use_changes
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- NOTA: NO se crea política para anon en land_use_changes.
-- Resultado: anon no puede leer datos de violaciones.
```

**Verificación:**
```sql
SELECT tablename, policyname, roles FROM pg_policies
WHERE tablename IN ('vegetation_monitoring', 'land_use_changes')
ORDER BY tablename, policyname;
-- Esperado: 5 políticas (3 para vegetation_monitoring, 2 para land_use_changes)
```

---

### F1-06: migración completa consolidada

**Archivo final:** `database/migrations/2026_03_13_vae_schema_hardening.sql`

Orden de ejecución dentro del archivo:
1. Pre-checks de duplicados (como comentarios SQL con instrucciones)
2. F1-04 (nuevas columnas) — primero porque no rompen nada
3. F1-01 (UNIQUE constraints) — después de limpiar duplicados
4. F1-02 (índices)
5. F1-03 (FK + NOT NULL)
6. F1-05 (RLS)

**Comando de aplicación:**
```bash
# En la VM de producción, conectado a Supabase:
psql "$DATABASE_URL" -f database/migrations/2026_03_13_vae_schema_hardening.sql
```

**Rollback:**
```sql
-- Solo si es necesario revertir:
ALTER TABLE vegetation_monitoring DROP CONSTRAINT IF EXISTS uq_vm_event_date;
ALTER TABLE land_use_changes DROP CONSTRAINT IF EXISTS uq_luc_event_date;
ALTER TABLE land_use_changes DROP CONSTRAINT IF EXISTS land_use_changes_monitoring_record_id_fkey;
DROP INDEX IF EXISTS idx_vm_event_date;
DROP INDEX IF EXISTS idx_vm_event_months;
DROP INDEX IF EXISTS idx_luc_event;
-- RLS: DROP POLICY + DISABLE ROW LEVEL SECURITY
-- Columnas: DROP COLUMN
```

---

## F2: umbrales unificados

**Estado:** Completada 2026-03-12.  
Creado `app/core/recovery_thresholds.py`; VAEService, worker recovery y API monitoring usan `classify_recovery_status`. Enum `RecoveryStatus` ampliado con `STALLED` y `PENDING`; `_map_recovery_status_to_string` devuelve taxonomía unificada.

---

### F2-01: crear archivo de constantes

**Archivo nuevo:** `app/core/recovery_thresholds.py`

```python
"""
Umbrales unificados de clasificación de recuperación de vegetación.

Fuente única de verdad para VAEService, workers y API.
Basados en decisión de negocio D-02 (2026-03-12).

Métrica: baseline ratio = (current_ndvi / baseline_ndvi) * 100
Interpretación: porcentaje del NDVI pre-incendio alcanzado.
NO es "recuperación desde el nadir post-incendio".
"""

RECOVERY_THRESHOLDS = {
    "full_recovery": 90,
    "advanced_recovery": 70,
    "moderate_recovery": 40,
    "early_recovery": 10,
    "stalled": 0,
}

# Estados que no dependen de umbrales numéricos
SPECIAL_STATES = {
    "not_started",    # sin datos / sin baseline
    "pending",        # análisis en curso
    "anomaly_detected",  # anomalía activa (overrides clasificación numérica)
}

# Todos los estados válidos (para validación en API y frontend)
ALL_RECOVERY_STATES = (
    list(RECOVERY_THRESHOLDS.keys())
    + ["not_started", "pending", "anomaly_detected"]
)


def classify_recovery_status(
    recovery_pct: float | None,
    has_anomaly: bool = False,
) -> str:
    """
    Clasificación unificada de estado de recuperación.

    Args:
        recovery_pct: porcentaje del baseline alcanzado (0-100+), o None si no hay datos.
        has_anomaly: True si se detectó anomalía activa.

    Returns:
        String con el estado de recuperación.

    Examples:
        >>> classify_recovery_status(95.0)
        'full_recovery'
        >>> classify_recovery_status(42.0)
        'moderate_recovery'
        >>> classify_recovery_status(None)
        'not_started'
        >>> classify_recovery_status(50.0, has_anomaly=True)
        'anomaly_detected'
    """
    if has_anomaly:
        return "anomaly_detected"
    if recovery_pct is None:
        return "not_started"
    if recovery_pct >= RECOVERY_THRESHOLDS["full_recovery"]:
        return "full_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["advanced_recovery"]:
        return "advanced_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["moderate_recovery"]:
        return "moderate_recovery"
    if recovery_pct >= RECOVERY_THRESHOLDS["early_recovery"]:
        return "early_recovery"
    return "stalled"
```

**Verificación:**
```bash
python -c "
from app.core.recovery_thresholds import classify_recovery_status
assert classify_recovery_status(95) == 'full_recovery'
assert classify_recovery_status(75) == 'advanced_recovery'
assert classify_recovery_status(42) == 'moderate_recovery'
assert classify_recovery_status(15) == 'early_recovery'
assert classify_recovery_status(5) == 'stalled'
assert classify_recovery_status(None) == 'not_started'
assert classify_recovery_status(50, has_anomaly=True) == 'anomaly_detected'
print('OK: todos los umbrales verificados')
"
```

---

### F2-02: actualizar VAEService

**Archivo:** `app/services/vae_service.py`

**Cambio 1 — importar umbrales (inicio del archivo):**
```python
from app.core.recovery_thresholds import classify_recovery_status, RECOVERY_THRESHOLDS
```

**Cambio 2 — reemplazar clasificación inline (~línea 896-907):**

Buscar el bloque que clasifica con umbrales hardcodeados (variantes de `if recovery_pct < 10: NOT_STARTED`, `elif recovery_pct < 30: EARLY_RECOVERY`, etc.) y reemplazar por:

```python
recovery_status = classify_recovery_status(recovery_pct, has_anomaly=anomaly_detected)
```

**Cambio 3 — documentar fórmula (~línea 302-303):**

Reemplazar comentario existente por:
```python
# Métrica: porcentaje del NDVI pre-incendio alcanzado (baseline ratio).
# NO es "recuperación desde el nadir post-incendio".
# Fórmula: (current_ndvi / baseline_ndvi) * 100
# Ejemplo: baseline=0.6, actual=0.35 → 58% del baseline alcanzado.
# Decisión D-01: se mantiene esta fórmula. nadir_ndvi no se persiste.
recovery_pct = min(100, max(0, (current_ndvi / baseline_ndvi) * 100))
```

**Verificación:**
```bash
grep -n "from app.core.recovery_thresholds" app/services/vae_service.py
# Esperado: 1 línea con el import

grep -n "classify_recovery_status" app/services/vae_service.py
# Esperado: al menos 1 uso

grep -rn "if recovery_pct < 10\|if recovery_pct < 30\|if pct >= 80\|if pct >= 50" app/services/vae_service.py
# Esperado: 0 resultados (umbrales hardcodeados eliminados)
```

---

### F2-03: actualizar worker recovery

**Archivo:** `workers/tasks/recovery.py`

**Cambio — reemplazar clasificación inline (~línea 20-32):**

Buscar el bloque con umbrales como `if pct >= 80: "advanced_recovery"`, `if pct >= 50: "moderate_recovery"`, etc.

Reemplazar por:
```python
from app.core.recovery_thresholds import classify_recovery_status

# Dentro de la función que clasifica:
recovery_status = classify_recovery_status(recovery_pct)
```

**Verificación:**
```bash
grep -n "classify_recovery_status" workers/tasks/recovery.py
# Esperado: al menos 1 uso

grep -rn "if pct >= 80\|if pct >= 50\|if pct >= 20" workers/tasks/recovery.py
# Esperado: 0 resultados
```

---

### F2-04: actualizar API monitoring

**Archivo:** `app/api/routes/monitoring.py`

**Cambio 1 — reemplazar clasificación inline (~línea 219-238):**

Buscar `_classify_status` o el bloque con umbrales como `if recovery_pct >= 90: "full_recovery"`, `if recovery_pct >= 70: "advanced_recovery"`, etc.

Reemplazar toda la función `_classify_status` por:
```python
from app.core.recovery_thresholds import classify_recovery_status

# Eliminar función _classify_status() completa.
# En todos los puntos donde se llamaba _classify_status(), usar:
recovery_status = classify_recovery_status(recovery_pct, has_anomaly=is_suspicious)
```

**Cambio 2 — corregir referencia a anomaly_type (~línea 196):**

Buscar `vm.anomaly_type` en la query SQL del summary y reemplazar por `vm.activity_type`.

Ajustar la lógica de `is_suspicious` (~línea 258-266) para usar `human_activity_detected` y `activity_type` en vez de `anomaly_type`.

**Cambio 3 — corregir INTERVAL parametrization (~línea 208):**

Buscar:
```sql
AND fe.start_date < NOW() - INTERVAL ':min_months months'
```
Reemplazar por:
```sql
AND fe.start_date < NOW() - (INTERVAL '1 month' * :min_months)
```

**Verificación:**
```bash
# Umbrales unificados
grep -rn "if recovery_pct >= 90\|if recovery_pct >= 70\|if recovery_pct >= 40" app/api/routes/monitoring.py
# Esperado: 0 resultados

# anomaly_type eliminado
grep -rn "anomaly_type" app/api/routes/monitoring.py
# Esperado: 0 resultados

# INTERVAL corregido
grep -rn "INTERVAL ':min_months" app/api/routes/monitoring.py
# Esperado: 0 resultados

# classify_recovery_status usado
grep -n "classify_recovery_status" app/api/routes/monitoring.py
# Esperado: al menos 1 resultado
```

---

## F3: unificación de colas Celery

**Estado:** Completada 2026-03-12.  
task_routes y beat_schedule usan cola `vae` para recovery y destruction; carousel en `analysis`. Worker recovery y API monitoring encolan en `vae`. `celery_app.py` en raíz es proxy a `workers.celery_app` (sin rutas). Docker-compose worker-gee ya consume `analysis,vae`.

---

### F3-01: actualizar task_routes en celery_app

**Archivo:** `workers/celery_app.py`

Buscar en `task_routes` (aproximadamente línea 96-106) todas las entradas que apuntan a cola `'gee'`:

```python
# ANTES (estado actual):
'workers.tasks.recovery.*': {'queue': 'gee'},
'workers.tasks.destruction.*': {'queue': 'gee'},
```

Reemplazar por:
```python
# DESPUÉS:
'workers.tasks.recovery.*': {'queue': 'vae'},
'workers.tasks.destruction.*': {'queue': 'vae'},
```

**Verificación:**
```bash
grep -rn "'gee'" workers/celery_app.py
# Esperado: 0 resultados (cola gee eliminada completamente)

grep -rn "'queue': 'vae'" workers/celery_app.py
# Esperado: al menos 2 resultados (recovery + destruction)
```

---

### F3-02: actualizar decoradores de tasks

**Archivo:** `workers/tasks/recovery.py`

Buscar decorador `@celery_app.task(queue="gee", ...)` (~línea 38) y cambiar a:
```python
@celery_app.task(queue="vae", ...)
```

Buscar en `batch_recovery_analysis` (~línea 88):
```python
analyze_recovery.s(fire_id, months).set(queue='analysis')
```
Cambiar a:
```python
analyze_recovery.s(fire_id, months).set(queue='vae')
```

**Archivo:** `workers/tasks/destruction.py`

Verificar que ya usa `queue='vae'`. Si hay alguna referencia a `queue='gee'`, cambiar a `vae`.

**Verificación:**
```bash
grep -rn "queue.*gee\|queue=\"gee\"\|queue='gee'" workers/tasks/
# Esperado: 0 resultados

grep -rn "queue.*vae\|queue=\"vae\"\|queue='vae'" workers/tasks/recovery.py
# Esperado: al menos 1 resultado
```

---

### F3-03: actualizar beat_schedule

**Archivo:** `workers/celery_app.py`

Buscar en `beat_schedule` todas las entradas con `'options': {'queue': 'gee'}`:

```python
# Entradas afectadas:
'recovery-monthly':        options → {'queue': 'vae'}
'recovery-weekly-recent':  options → {'queue': 'vae'}
'vae-recovery-monthly':    options → {'queue': 'vae'}
'vae-destruction-monthly': options → {'queue': 'vae'}
'vae-episodes-weekly':     options → {'queue': 'vae'}
```

Para `carousel-daily`, mantener en `analysis` (no es VAE):
```python
'carousel-daily': options → {'queue': 'analysis'}  # sin cambio
```

**Verificación:**
```bash
grep -A2 "queue.*gee" workers/celery_app.py
# Esperado: 0 resultados

# Verificar que beat entries usan vae:
python -c "
from workers.celery_app import celery_app
for name, entry in celery_app.conf.beat_schedule.items():
    q = entry.get('options', {}).get('queue', 'default')
    if 'recovery' in name or 'vae' in name or 'destruction' in name:
        assert q == 'vae', f'{name} usa cola {q}, esperada vae'
        print(f'OK: {name} → {q}')
"
```

---

### F3-04: actualizar endpoints que encolan

**Archivo:** `app/api/routes/monitoring.py`

Buscar en `trigger_recovery_analysis` (~línea 850, 854) las llamadas `.apply_async()` con `queue="gee"`:

```python
# ANTES:
analyze_recovery.apply_async(args=[fire_event_id], queue="gee")
detect_destruction.apply_async(args=[fire_event_id], queue="gee")
```

Reemplazar por:
```python
# DESPUÉS:
analyze_recovery.apply_async(args=[fire_event_id], queue="vae")
detect_destruction.apply_async(args=[fire_event_id], queue="vae")
```

También buscar en `_enqueue_recovery_if_not_pending` (~línea 641):
```python
# Si usa queue="gee", cambiar a queue="vae"
```

**Verificación:**
```bash
grep -rn "queue.*gee\|queue=\"gee\"\|queue='gee'" app/api/routes/monitoring.py
# Esperado: 0 resultados
```

---

### F3-05: verificar celery_app duplicado en raíz

**Archivo:** `celery_app.py` (en la raíz del proyecto, NO en `workers/`)

Según la auditoría AS-IS existe un `celery_app.py` en la raíz que diverge de `workers/celery_app.py`. Buscar si tiene rutas a cola `gee` y actualizar de la misma manera. Si es un archivo legacy no usado por docker-compose, documentarlo o eliminarlo.

**Verificación:**
```bash
# Confirmar cuál celery_app usa docker-compose:
grep "celery_app" docker-compose.yml
# Esperado: todas las referencias usan "workers.celery_app"

# Si celery_app.py raíz existe y no se usa:
grep -rn "queue.*gee" celery_app.py
# Si tiene referencias a gee: actualizar o eliminar archivo
```

---

## F4: unificación de taxonomía de estados

**Estado:** Completada 2026-03-12.  
F4-02 ya aplicado en F2 (classify_recovery_status). Creado `app/core/legal.py` (F4-05); RecoveryResponse con recovery_metric, recovery_metric_description, legal_disclaimer; todos los retornos de RecoveryResponse incluyen los tres campos (F4-04). Mensajes 503 ya sanitizados (F4-06 sin cambio).

---

### F4-01: mapeo actual → objetivo

**Estado actual (backend `_classify_status`):**
```
suspicious, unknown, excellent, good, moderate, poor, critical, pending
```

**Estado actual (frontend `RecoveryStatusBadge`):**
```
not_started, early_recovery, moderate_recovery, advanced_recovery,
full_recovery, stalled, anomaly_detected, pending
```

**Estado objetivo (unificado, fuente: `recovery_thresholds.py`):**
```
not_started, pending, early_recovery, moderate_recovery,
advanced_recovery, full_recovery, stalled, anomaly_detected
```

### F4-02: eliminar _classify_status del backend

**Archivo:** `app/api/routes/monitoring.py`

Buscar la función `_classify_status` (~línea 185-238). Eliminarla completamente.

En todos los puntos donde se llamaba, reemplazar por `classify_recovery_status()` importado desde `app.core.recovery_thresholds`.

**Mapeo de sustitución para lógica existente:**

| Lógica actual | Nuevo equivalente |
|---|---|
| `_classify_status(recovery_pct, is_suspicious)` | `classify_recovery_status(recovery_pct, has_anomaly=is_suspicious)` |
| Retorno `"excellent"` / `"good"` | Ahora retorna `"full_recovery"` / `"advanced_recovery"` |
| Retorno `"moderate"` | Ahora retorna `"moderate_recovery"` |
| Retorno `"poor"` / `"critical"` | Ahora retorna `"early_recovery"` / `"stalled"` |
| Retorno `"suspicious"` | Ahora retorna `"anomaly_detected"` |
| Retorno `"unknown"` | Ahora retorna `"not_started"` |

---

### F4-03: verificar frontend sin cambios de código

El frontend `RecoveryStatusBadge` ya usa la taxonomía correcta (`early_recovery`, `moderate_recovery`, etc.) con fallback a `not_started` para valores desconocidos.

Una vez que el backend emita los estados correctos (F4-02), el frontend funciona sin modificación.

**Verificación:**
```bash
# Confirmar que el badge ya usa la taxonomía objetivo:
grep -A30 "statusConfig\|StatusConfig" frontend/src/components/monitoring/RecoveryStatusBadge.tsx
# Esperado: keys incluyen early_recovery, moderate_recovery, etc.

# Confirmar que el fallback existe:
grep "not_started\|default\|fallback" frontend/src/components/monitoring/RecoveryStatusBadge.tsx
# Esperado: al menos 1 resultado
```

---

### F4-04: actualizar endpoint de recovery para incluir campo recovery_metric

**Archivo:** `app/api/routes/monitoring.py`

En la respuesta de `GET /monitoring/recovery/{fire_event_id}`, agregar campos:

```python
# En el dict de respuesta, agregar:
"recovery_metric": "baseline_ratio",
"recovery_metric_description": "Porcentaje del NDVI pre-incendio alcanzado",
"legal_disclaimer": get_legal_disclaimer(),  # ver F4-05
```

---

### F4-05: agregar helper de disclaimer legal

**Archivo nuevo:** `app/core/legal.py`

```python
"""
Disclaimer legal para módulo VAE.
Decisión D-05: default estático + override dinámico desde API.
"""

DEFAULT_LEGAL_DISCLAIMER = (
    "Los resultados presentados constituyen alertas generadas mediante "
    "detección remota satelital (Sentinel-2) y análisis automatizado de "
    "índices de vegetación. No reemplazan la verificación técnica y legal "
    "presencial. Su interpretación requiere validación por profesionales "
    "habilitados conforme a la ley 26.815 y su modificatoria 27.604."
)


def get_legal_disclaimer(override: str | None = None) -> str:
    """Retorna el disclaimer legal, con posibilidad de override."""
    return override or DEFAULT_LEGAL_DISCLAIMER
```

---

### F4-06: sanitizar error messages

**Archivo:** `app/api/routes/monitoring.py` (~línea 423)

Buscar:
```python
raise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")
```

Reemplazar por:
```python
logger.error(f"Error processing NDVI analysis: {str(e)}", exc_info=True)
raise HTTPException(
    status_code=503,
    detail="Servicio de análisis temporalmente no disponible"
)
```

---

## Verificación integral post-implementación

### Checklist F1 (schema)
```bash
# Desde la VM, conectado a Supabase:
psql "$DATABASE_URL" -c "
SELECT 'uq_vm' AS check, conname FROM pg_constraint WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u'
UNION ALL
SELECT 'uq_luc', conname FROM pg_constraint WHERE conrelid = 'land_use_changes'::regclass AND contype = 'u'
UNION ALL
SELECT 'idx_count'::text, COUNT(*)::text FROM pg_indexes WHERE tablename = 'vegetation_monitoring' AND indexname LIKE 'idx_vm_%'
UNION ALL
SELECT 'rls_count', COUNT(*)::text FROM pg_policies WHERE tablename IN ('vegetation_monitoring', 'land_use_changes')
UNION ALL
SELECT 'col_confidence', column_name FROM information_schema.columns WHERE table_name = 'land_use_changes' AND column_name = 'confidence_score'
UNION ALL
SELECT 'col_pending', column_name FROM information_schema.columns WHERE table_name = 'vegetation_monitoring' AND column_name = 'pending_reason'
UNION ALL
SELECT 'col_cache', column_name FROM information_schema.columns WHERE table_name = 'fire_events' AND column_name = 'latest_recovery_status';
"
```

### Checklist F2 (umbrales)
```bash
# Verificar que no quedan umbrales hardcodeados:
grep -rn "if recovery_pct < 10\|if recovery_pct < 30\|if recovery_pct < 60" app/services/ workers/tasks/ app/api/routes/
# Esperado: 0 resultados

grep -rn "if pct >= 80\|if pct >= 50\|if pct >= 20\|if pct >= 95" app/services/ workers/tasks/ app/api/routes/
# Esperado: 0 resultados

# Verificar import centralizado:
grep -rn "from app.core.recovery_thresholds import" app/services/ workers/tasks/ app/api/routes/
# Esperado: 3 resultados (vae_service, recovery worker, monitoring API)
```

### Checklist F3 (colas)
```bash
# Verificar que cola 'gee' no existe en ningún archivo:
grep -rn "'gee'\|\"gee\"" workers/ app/ celery_app.py docker-compose.yml
# Esperado: 0 resultados

# Verificar que worker-gee consume vae:
docker compose exec worker-gee celery -A workers.celery_app inspect active_queues 2>/dev/null | grep -E "vae|analysis"
# Esperado: ambas colas listadas
```

### Checklist F4 (taxonomía)
```bash
# Verificar que la taxonomía vieja no existe:
grep -rn "excellent\|\"good\"\|\"poor\"\|\"critical\"\|\"suspicious\"\|\"unknown\"" app/api/routes/monitoring.py
# Esperado: 0 resultados (excepto en comentarios si los hay)

# Verificar que _classify_status no existe:
grep -rn "def _classify_status" app/api/routes/monitoring.py
# Esperado: 0 resultados

# Verificar disclaimer:
grep -rn "legal_disclaimer" app/api/routes/monitoring.py
# Esperado: al menos 1 resultado
```

---

## Orden de ejecución

```
F1 (schema) ──→ F2 (umbrales) ──→ F3 (colas) ──→ F4 (taxonomía)
     │                │                │                │
     │                │                │                └─ No requiere deploy
     │                │                └─ Requiere restart de workers
     │                └─ No requiere deploy (solo código)
     └─ Requiere migración SQL en Supabase

Deploy secuencia:
1. Aplicar migración SQL (F1) ← puede hacerse sin downtime
2. Deploy de código (F2 + F3 + F4) ← un solo deploy
3. Restart workers: docker compose restart worker-gee
4. Verificar logs: docker compose logs -f worker-gee --since=5m
```
