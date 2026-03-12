# UC-F12: plan de testing y ejecución manual de workers

> **Fecha:** 2026-02-24  
> **Contexto:** el código UC-F12 fue implementado y deployado exitosamente (412 inserciones, 75 eliminaciones, 14 archivos). Sin embargo, los cambios en el frontend no se visualizan porque las tablas `vegetation_monitoring` y `land_use_changes` están vacías — los workers nunca ejecutaron aún.

---

## Diagnóstico: ¿por qué no se ven los cambios en la UI?

El flujo de datos de UC-F12 es:

```
Workers (Celery) → BD (vegetation_monitoring / land_use_changes) → API (GET endpoints) → UI (RecoveryPanel)
```

Los cambios deployados incluyen frontend, backend y workers. Pero los workers son **reactivos** — se ejecutan cuando:
1. Un admin dispara `POST /monitoring/recovery/trigger` manualmente, o
2. Celery Beat los ejecuta el día 1 de cada mes (schedule nuevo)

Como ninguna de las dos cosas ocurrió desde el deploy, las tablas están vacías y la UI muestra correctamente el estado "pending" (o no muestra nada si el RecoveryPanel está condicionado a tener datos).

---

## Parte 1: verificación de BD (ejecutar en la VM vía SSH)

> Nota 2026-03: la topología actual consolidó los workers en `worker-fast` y `worker-gee`.  
> La cola `vae` (UC-F12 / VAE) hoy es consumida por el contenedor `forestguard-worker-gee`.  
> Donde este documento menciona `worker-vae`, usar `worker-gee` y ver `docs/architecture/containers.md` para la topología actual de workers.

### 1.1 Verificar que el worker-gee está corriendo

```bash
ssh opc@<PROD_VM_HOST>

# Ver que el container worker-gee existe y está running
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "worker|gee|beat"
```

**Esperado:**
```
forestguard-worker-gee       Up X minutes
forestguard-celery-beat      Up X hours
forestguard-worker-fast      Up X hours
```

Si `worker-gee` no aparece:
```bash
cd /home/opc
docker compose up -d worker-gee
docker logs --tail 20 forestguard-worker-gee
```

### 1.2 Verificar que la cola vae está configurada

```bash
# Ver que el worker escucha las colas analysis y vae
docker logs forestguard-worker-gee 2>&1 | head -20
# Buscar línea tipo: "queues: analysis, vae"
```

### 1.3 Verificar estado de las tablas de monitoreo

```bash
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()

vm_count = db.execute(text('SELECT count(*) FROM vegetation_monitoring')).scalar()
luc_count = db.execute(text('SELECT count(*) FROM land_use_changes')).scalar()
events_count = db.execute(text(\"\"\"
    SELECT count(*) FROM fire_events 
    WHERE start_date > NOW() - INTERVAL '36 months'
    AND centroid IS NOT NULL
\"\"\")).scalar()

print(f'vegetation_monitoring rows: {vm_count}')
print(f'land_use_changes rows: {luc_count}')
print(f'Fire events eligible for VAE: {events_count}')
db.close()
"
```

**Esperado:** `vm_count = 0`, `luc_count = 0`, `events_count > 0`

### 1.4 Verificar constraints y RLS

```bash
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()

# UNIQUE constraints
constraints = db.execute(text(\"\"\"
    SELECT conname FROM pg_constraint 
    WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u'
\"\"\")).fetchall()
print(f'UNIQUE constraints on vegetation_monitoring: {[c[0] for c in constraints]}')

# RLS
rls = db.execute(text(\"\"\"
    SELECT tablename, policyname FROM pg_policies 
    WHERE tablename IN ('vegetation_monitoring', 'land_use_changes')
\"\"\")).fetchall()
print(f'RLS policies: {[(r[0], r[1]) for r in rls]}')

db.close()
"
```

### 1.5 Verificar que los endpoints responden correctamente

```bash
# Sin JWT → debe retornar 401 (auth obligatoria)
curl -s -o /dev/null -w "GET /monitoring/recovery/summary → HTTP %{http_code}\n" \
  http://localhost:8000/api/v1/monitoring/recovery/summary

# Con JWT → debe retornar 200
# (reemplazar <TOKEN> por un JWT válido de un usuario autenticado)
curl -s -o /dev/null -w "GET /monitoring/recovery/summary (auth) → HTTP %{http_code}\n" \
  -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/v1/monitoring/recovery/summary
```

---

## Parte 2: ejecución manual de workers para poblar datos

### Opción A: trigger individual para un evento específico (recomendada para testear)

```bash
# 1. Obtener un fire_event_id válido con geometría
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
events = db.execute(text(\"\"\"
    SELECT id, province, start_date, 
           ST_AsText(ST_Centroid(centroid)) as centroid_text
    FROM fire_events 
    WHERE centroid IS NOT NULL 
    AND start_date > NOW() - INTERVAL '12 months'
    ORDER BY start_date DESC 
    LIMIT 5
\"\"\")).fetchall()
for e in events:
    print(f'ID: {e[0]} | Provincia: {e[1]} | Fecha: {e[2]} | Centroide: {e[3]}')
db.close()
"
```

```bash
# 2. Ejecutar worker de recovery para UN evento específico
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.recovery.analyze_recovery \
  --args='["<FIRE_EVENT_ID>"]'

# 3. Monitorear logs en tiempo real
docker logs --tail 50 -f forestguard-worker-gee
```

**Esperado en logs:**
```
[INFO] Recovery analysis persisted for event <ID>
```

O si GEE falla:
```
[WARNING] GEE analysis failed for <ID>: <error>
[INFO] Retrying in 60s...
```

```bash
# 4. Verificar que se creó el registro
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
rows = db.execute(text(\"\"\"
    SELECT fire_event_id, monitoring_date, ndvi_mean, baseline_ndvi, recovery_percentage
    FROM vegetation_monitoring 
    ORDER BY created_at DESC LIMIT 5
\"\"\")).fetchall()
for r in rows:
    print(f'Event: {r[0][:8]}... | Date: {r[1]} | NDVI: {r[2]} | Baseline: {r[3]} | Recovery: {r[4]}%')
db.close()
"
```

### Opción B: trigger de destruction para un evento

```bash
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.destruction.detect_destruction \
  --args='["<FIRE_EVENT_ID>"]'
```

### Opción C: batch — procesar todos los eventos elegibles (cuidado con cuota GEE)

```bash
# Ejecutar batch de recovery (máx 50 eventos por defecto)
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.recovery.batch_recovery_analysis

# Ejecutar batch de destruction
docker exec forestguard-worker-gee celery -A workers.celery_app call \
  workers.tasks.destruction.batch_destruction_detection
```

**Precaución con cuota GEE:** cada evento consume al menos 2 requests GEE (baseline + current). Con 50 eventos serían ~100 requests. El free tier permite 50,000/día, así que es seguro. Pero no ejecutar múltiples batches seguidos sin verificar.

### Opción D: trigger vía API (si tenés sesión de admin en el browser)

```bash
# Desde la VM o cualquier máquina con acceso:
curl -X POST https://<TU_DOMINIO>/api/v1/monitoring/recovery/trigger \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"fire_event_id": "<FIRE_EVENT_ID>"}'
# Esperado: HTTP 202 Accepted
```

O directamente desde Swagger UI: ir a `https://<TU_DOMINIO>/docs`, autenticarse, y ejecutar el endpoint `POST /monitoring/recovery/trigger`.

---

## Parte 3: verificación de la UI después de poblar datos

### 3.1 Verificar el detalle de un incendio con datos

1. Abrir el browser e ir a `https://<TU_DOMINIO>/fires/<FIRE_EVENT_ID>` (el mismo ID que usaste para el trigger manual).
2. Iniciar sesión con Google OAuth (el RecoveryPanel requiere autenticación).

**Qué debería verse (usuario autenticado):**
- `RecoveryStatusBadge` con el estado correcto (ej: "Recuperación temprana" en amarillo, "Recuperado" en verde, etc.)
- Tarjetas métricas: baseline NDVI, NDVI actual, porcentaje de recuperación
- Gráfico NDVI (si hay más de un dato de monitoreo)
- Tarjetas de cambio de uso (si se detectaron)

**Qué debería verse (usuario NO autenticado):**
- La página de detalle del incendio con mapa, info, stats
- SIN RecoveryPanel (oculto por el gate `isAuthenticated`)

### 3.2 Verificar el feed (Home)

1. Ir a `https://<TU_DOMINIO>/` (página principal).
2. Con sesión activa, buscar en las tarjetas de episodios si aparece el `RecoveryStatusBadge`.

**Nota:** el badge en el feed depende de que el endpoint de listado incluya `recovery_status` en la respuesta. Si no aparece, puede que el endpoint de episodios no incluya ese campo aún. Verificar:
```bash
curl -s -H "Authorization: Bearer <TOKEN>" \
  https://<TU_DOMINIO>/api/v1/fire-episodes/ | python3 -m json.tool | grep -i recovery
```

### 3.3 Verificar el mapa

1. Ir a `https://<TU_DOMINIO>/map`.
2. Si hay un evento con `is_potential_violation = true` en `land_use_changes`, su marcador debería tener un ícono diferenciado (rojo con alerta).

**Nota:** la diferenciación de marcadores depende de que el endpoint de episodios incluya `is_potential_violation`. Verificar:
```bash
docker exec forestguard-api python -c "
from app.db.session import SessionLocal
from sqlalchemy import text
db = SessionLocal()
violations = db.execute(text(\"\"\"
    SELECT fire_event_id, change_type, is_potential_violation 
    FROM land_use_changes WHERE is_potential_violation = true
\"\"\")).fetchall()
print(f'Violations found: {len(violations)}')
for v in violations:
    print(f'  Event: {v[0][:8]}... | Type: {v[1]}')
db.close()
"
```

### 3.4 Verificar empty state (pending)

1. Ir a `/fires/<UN_EVENTO_SIN_DATOS>` (un fire_event_id que NO haya sido procesado por el worker).
2. Con sesión activa, debería verse el empty state con el ícono de planta y el texto "Análisis de recuperación pendiente".

---

## Parte 4: checklist rápida de smoke test

```
INFRAESTRUCTURA
[ ] worker-gee está running en docker ps
[ ] worker-gee escucha colas 'analysis' y 'vae'
[ ] celery-beat está running

BASE DE DATOS (post ejecución manual)
[ ] vegetation_monitoring tiene al menos 1 row
[ ] land_use_changes tiene al menos 0-1 rows (puede no haber cambios)
[ ] UNIQUE constraints existen en ambas tablas
[ ] RLS policies existen (4 políticas total)

API
[ ] GET /monitoring/recovery/summary sin JWT → 401
[ ] GET /monitoring/recovery/<id> con JWT → 200 con datos
[ ] POST /monitoring/recovery/trigger con admin JWT → 202

FRONTEND
[ ] /fires/<id> con sesión → muestra RecoveryPanel con datos
[ ] /fires/<id> sin sesión → NO muestra RecoveryPanel
[ ] /fires/<id-sin-datos> con sesión → muestra empty state "pendiente"
[ ] Home feed → badge de recovery visible (si el endpoint lo incluye)
[ ] Mapa → marcador diferenciado para violaciones (si hay violaciones)
```

---

## Troubleshooting

### "worker-gee no arranca"
```bash
docker logs forestguard-worker-gee 2>&1 | tail -30
# Buscar: ModuleNotFoundError, ConnectionError, authentication errors
```

Causa probable: faltan variables de entorno GEE. Verificar:
```bash
docker exec forestguard-worker-gee env | grep GEE
# Debe mostrar GEE_PROJECT_ID, GEE_SERVICE_ACCOUNT_EMAIL, GEE_PRIVATE_KEY_PATH
```

### "Worker arranca pero el task falla"
```bash
docker logs forestguard-worker-gee 2>&1 | grep -i "error\|failed\|exception" | tail -20
```

Causas probables:
- **GEE auth:** `ee.Initialize()` falla → verificar que el secret `gcp-sa.json` está montado
- **BD connection:** `SessionLocal()` falla → verificar `DATABASE_URL` en env vars
- **Geometría null:** el evento no tiene centroid → elegir otro evento con centroid no null

### "RecoveryPanel no aparece aunque hay datos"
1. Verificar que estás logueado (el panel requiere `isAuthenticated`)
2. Verificar que NO estás en vista de episodio (el panel se oculta con `isEpisodeDetail`)
3. Verificar que la ruta es `/fires/<fire_event_id>`, no `/episodes/<episode_id>`
4. Abrir DevTools → Network → buscar request a `/monitoring/recovery/<id>`:
   - Si no hay request: el componente no se montó (verificar auth gate)
   - Si hay request 401: el token JWT expiró o no se envía
   - Si hay request 200 con `"recovery_status": "pending"`: no hay datos para ese evento
   - Si hay request 200 con datos: el componente debería renderizar

### "El badge muestra 'Sin monitoreo' a pesar de tener datos"
Verificar la taxonomía de estados. El endpoint debe retornar uno de:
`full_recovery`, `advanced_recovery`, `moderate_recovery`, `early_recovery`, `stalled`, `anomaly_detected`, `pending`, `not_started`

```bash
curl -s -H "Authorization: Bearer <TOKEN>" \
  https://<DOMINIO>/api/v1/monitoring/recovery/<FIRE_EVENT_ID> | python3 -m json.tool | grep recovery_status
```

Si retorna un valor diferente (como `excellent`, `good`, `poor`), la tarea 3.1 (unificación de taxonomía) no se aplicó correctamente.
