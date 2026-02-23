# UC-F12: Recuperación y cambio de uso (VAE) — Especificación de implementación

> **Propósito de este documento:** guiar a Claude Code en el análisis del repositorio para validar que la implementación de UC-F12 no genera conflictos, regresiones ni viola restricciones arquitectónicas del proyecto ForestGuard.

---

## 1. Estado actual

### 1.1 Base técnica presente

| Componente | Archivo | Estado | Observación |
|---|---|---|---|
| Servicio GEE para NDVI | `app/services/vae_service.py` | ✅ Existe | Lógica implementada, no expuesta como endpoint |
| Worker de recuperación | `workers/tasks/recovery.py` | ✅ Existe | `analyze_recovery(fire_event_id)` en cola `analysis` |
| Worker de destrucción | `workers/tasks/destruction.py` | ✅ Existe | `detect_destruction(fire_event_id, check_date)` en cola `analysis` |
| Tabla `vegetation_monitoring` | `schema_v_4.sql` | ✅ En BD | Campos: `ndvi_mean`, `baseline_ndvi`, `recovery_percentage`, `human_activity_detected` |
| Tabla `land_use_changes` | `schema_v_4.sql` | ✅ En BD | Campos: `change_type`, `is_potential_violation`, `status`, `affected_area_hectares` |
| Router `/monitoring` | `app/api/routes/monitoring.py` | ⚠️ Parcial | Existe el archivo; verificar si los endpoints VAE están declarados o solo los de alertas |
| Registro en `main.py` | `app/main.py` | ❌ Sin verificar | Claude Code debe confirmar que el router VAE está incluido |
| RLS en tablas VAE | Supabase | ❌ Sin verificar | Sin política de acceso confirmada para `vegetation_monitoring` y `land_use_changes` |
| Cola separada `vae` | `celery_app.py` | ❌ Ausente | Actualmente usa cola `analysis` compartida con otros procesos |
| Frontend — pestaña recuperación | `frontend/src/` | ❌ Inexistente | No hay componente de visualización NDVI ni tarjetas de cambio de uso |

### 1.2 Arquitectura de workers actual

```
celery_app.py (include)
├── workers.tasks.ingestion      → cola: ingestion
├── workers.tasks.clustering     → cola: clustering
├── workers.tasks.recovery       → cola: analysis   ← compartida
└── workers.tasks.destruction    → cola: analysis   ← compartida (conflicto potencial)
```

### 1.3 Archivos que Claude Code debe inspeccionar

```
app/
├── services/vae_service.py           # Lógica GEE existente
├── main.py                           # Confirmar include_router monitoring
├── api/
│   ├── routes/monitoring.py          # ¿Declara endpoints VAE?
│   └── v1/monitoring.py              # ¿Existe esta versión consolidada?
workers/
├── tasks/recovery.py                 # Implementación actual
└── tasks/destruction.py              # Implementación actual
celery_app.py                         # Configuración de colas
frontend/src/
├── pages/                            # ¿Existe EventDetail o similar?
└── components/                       # ¿Existe FireCard o similar?
```

---

## 2. Objetivos de implementación

### 2.1 Objetivo principal

Convertir la base técnica existente (VAE) en un flujo de producto maduro y accesible mediante endpoints REST documentados y una interfaz de usuario visible en el detalle de cada evento de incendio.

### 2.2 Objetivos específicos

**Backend:**

- Exponer `GET /api/v1/monitoring/recovery/{fire_event_id}` que retorne la serie NDVI histórica desde `vegetation_monitoring`.
- Exponer `GET /api/v1/monitoring/land-use-changes/{fire_event_id}` que retorne registros de `land_use_changes`.
- Exponer `POST /api/v1/monitoring/recovery/trigger` para disparo manual (solo rol `admin`).
- Separar la cola `vae` de la cola `analysis` en `celery_app.py`.
- Aplicar RLS en Supabase para `vegetation_monitoring` y `land_use_changes`.

**Frontend:**

- Agregar badge de estado de recuperación (`RecoveryStatusBadge`) en la tarjeta de evento (`FireCard`).
- Agregar pestaña o sección "Recuperación" en la vista de detalle de evento (`/events/:id`).
- Mostrar gráfico NDVI temporal y tarjetas de cambios de uso detectados.
- Diferenciar visualmente en el mapa Leaflet los eventos con `is_potential_violation = true`.

---

## 3. Restricciones del proyecto

### 3.1 Restricciones de cuota (costo cero)

| Recurso | Límite free tier | Impacto en UC-F12 |
|---|---|---|
| GEE | 50 000 req/día, 40 simultáneas | Cada análisis NDVI consume requests GEE; el disparo manual debe tener rate limit estricto |
| Supabase | 500 MB | `vegetation_monitoring` puede crecer rápidamente con monitoreo mensual por 36 meses por evento |
| GCS / Oracle Object Storage | 5 GB / 10 GB | Imágenes satélite de VAE no se almacenan en HD; solo thumbnails si aplica |

### 3.2 Restricciones arquitectónicas

- **Colas separadas obligatorias:** la documentación de arquitectura establece explícitamente que VAE (recovery/destruction) debe usar colas separadas de los workers de reportes (ERS) para evitar bloqueo. La cola `analysis` compartida es un incumplimiento activo.
- **Sin HD persistente:** las imágenes utilizadas en el análisis VAE no deben almacenarse en storage permanente. Solo thumbnails si se requiere evidencia visual.
- **Autenticación obligatoria:** `vegetation_monitoring` y `land_use_changes` no son tablas públicas. Todos los endpoints deben requerir JWT.
- **RLS cerrada para `anon`:** ninguna tabla de análisis debe ser accesible por el rol anónimo de Supabase.
- **Rate limiting:** el endpoint de disparo manual `POST .../trigger` debe tener rate limit para proteger la cuota GEE.

### 3.3 Restricciones de schema

- La tabla `vegetation_monitoring` tiene FK a `fire_events(id)` y FK opcional a `satellite_images(id)`.
- La tabla `land_use_changes` tiene FK a `fire_events(id)` y FK opcional a `vegetation_monitoring(id)` (campo `monitoring_record_id`).
- El campo `baseline_ndvi` es crítico: sin él, el estado del evento debe ser `pending` (CT-UCF12-04). No se debe retornar error 500, sino un estado explícito.
- El campo `is_potential_violation` en `land_use_changes` activa lógica de alerta en UI y notificaciones; su valor no debe ser `null` en registros persistidos.

---

## 4. Impacto en el sistema

### 4.1 Impacto en backend

| Área | Tipo de cambio | Archivos afectados |
|---|---|---|
| Router de monitoring | Nuevos endpoints declarados | `app/api/routes/monitoring.py` o `app/api/v1/monitoring.py` |
| `main.py` | Registro del router (si no existe) | `app/main.py` |
| Celery | Nueva cola `vae` | `celery_app.py` |
| Workers | Reasignación de cola | `workers/tasks/recovery.py`, `workers/tasks/destruction.py` |
| Supabase | Políticas RLS | Migración SQL en Supabase |
| Schemas Pydantic | Modelos de respuesta nuevos | `app/schemas/monitoring.py` (verificar si existe) |

### 4.2 Impacto en frontend

| Componente existente | Cambio | Alcance |
|---|---|---|
| `FireCard` (tarjeta de evento en listado) | Agregar `RecoveryStatusBadge` | Afecta a todas las tarjetas del feed principal |
| Vista de detalle de evento | Agregar sección/tab "Recuperación" | Solo visible para usuarios autenticados |
| Mapa Leaflet | Marcador diferenciado para alertas de cambio de uso | Afecta la capa de markers existente |
| Sistema de rutas React | Posible nueva ruta `/events/:id/recovery` | Depende de si se usa tab o ruta separada |

### 4.3 Impacto en datos

- Ningún dato existente en `fire_events` o `fire_detections` se modifica.
- Se escriben nuevos registros en `vegetation_monitoring` (por worker) y `land_use_changes` (por worker).
- No hay migraciones destructivas.

---

## 5. Páginas y componentes afectados

### 5.1 Frontend — páginas

| Página / ruta | Cambio | Tipo |
|---|---|---|
| Feed principal (listado de eventos) | Badge de estado de recuperación en cada `FireCard` | Aditivo |
| Detalle de evento `/events/:id` | Nueva sección o pestaña "Recuperación" con gráfico NDVI y tarjetas de cambio de uso | Aditivo |
| Mapa principal | Marcador visual diferenciado para `is_potential_violation = true` | Modificación de capa existente |

### 5.2 Frontend — componentes nuevos

| Componente | Descripción | Datos que consume |
|---|---|---|
| `RecoveryStatusBadge` | Chip de color con estado: sin monitoreo / en recuperación / estancado / alerta | `vegetation_monitoring.recovery_percentage` |
| `RecoveryTimeline` | Gráfico de línea NDVI mes a mes con gradiente de color | `GET /monitoring/recovery/:id` |
| `LandUseChangeCard` | Tarjeta con tipo de cambio, severidad, flag de violación y fecha | `GET /monitoring/land-use-changes/:id` |
| `RecoveryPanel` | Contenedor que agrupa `RecoveryTimeline` + lista de `LandUseChangeCard` | Ambos endpoints |

### 5.3 Frontend — componentes modificados

| Componente | Modificación |
|---|---|
| `FireCard` | Agregar `RecoveryStatusBadge` condicionalmente (solo si el usuario está autenticado) |
| Capa de markers Leaflet | Nuevo ícono o color para eventos con alerta de cambio de uso |
| `EventDetail` (si existe) | Agregar tab o sección colapsable con `RecoveryPanel` |

---

## 6. Estado esperado tras la implementación

### 6.1 Backend

```
GET  /api/v1/monitoring/recovery/{fire_event_id}
     → 200: array de registros NDVI ordenados por monitoring_date
     → 200 vacío: evento sin baseline (incluir campo status: "pending")
     → 401: sin JWT
     → 404: fire_event_id inexistente

GET  /api/v1/monitoring/land-use-changes/{fire_event_id}
     → 200: array de cambios detectados
     → 401: sin JWT
     → 404: fire_event_id inexistente

POST /api/v1/monitoring/recovery/trigger
     → 202: job encolado en cola "vae"
     → 401: sin JWT
     → 403: JWT sin rol admin
     → 429: rate limit excedido
```

### 6.2 Workers

```
celery_app.py (task_routes actualizado)
├── workers.tasks.ingestion      → cola: ingestion
├── workers.tasks.clustering     → cola: clustering
├── workers.tasks.recovery       → cola: vae        ← separada
└── workers.tasks.destruction    → cola: vae        ← separada
```

### 6.3 Supabase RLS esperadas

```sql
-- vegetation_monitoring
-- Solo usuarios autenticados pueden leer
CREATE POLICY "auth_read_vegetation" ON vegetation_monitoring
  FOR SELECT TO authenticated USING (true);

-- Solo service_role puede insertar/actualizar (workers)
CREATE POLICY "system_write_vegetation" ON vegetation_monitoring
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- land_use_changes
CREATE POLICY "auth_read_land_use" ON land_use_changes
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "system_write_land_use" ON land_use_changes
  FOR ALL TO service_role USING (true) WITH CHECK (true);
```

### 6.4 Frontend

- `FireCard` muestra `RecoveryStatusBadge` para usuarios autenticados; para anónimos, no renderiza el badge.
- La pestaña "Recuperación" en detalle de evento es visible solo con sesión activa.
- El mapa diferencia visualmente (color rojo / ícono especial) los eventos con `is_potential_violation = true` en `land_use_changes`.
- Los estados vacíos (sin monitoreo, sin baseline) muestran mensajes descriptivos, no errores.

---

## 7. Regresiones que Claude Code debe verificar

### 7.1 Regresiones en API

| Escenario | Verificación | Criterio de fallo |
|---|---|---|
| Endpoints existentes en `monitoring.py` | Confirmar que los nuevos endpoints no solapan paths existentes | Cualquier `404` en endpoints previamente funcionales |
| `main.py` — routers registrados | Confirmar que el include del router monitoring no duplica prefijos | Error de startup o paths duplicados en `/docs` |
| Schema OpenAPI | Comparar paths antes y después con `curl /openapi.json` | Diferencias en endpoints preexistentes |
| Cola `analysis` | Confirmar que otros workers que usan `analysis` no se ven afectados por la separación | Workers de analysis existentes sin cambio de cola involuntario |

### 7.2 Regresiones en base de datos

| Escenario | Verificación |
|---|---|
| FK integridad | Confirmar que los workers no insertan en `vegetation_monitoring` con `fire_event_id` inexistente |
| Campo `baseline_ndvi` nulo | El endpoint debe retornar `status: "pending"` sin error 500 cuando `baseline_ndvi IS NULL` |
| `is_potential_violation` | No debe persistirse como `null`; usar `false` como default explícito |
| RLS existentes | Confirmar que las nuevas políticas no entran en conflicto con políticas existentes en otras tablas |

### 7.3 Regresiones en frontend

| Escenario | Verificación |
|---|---|
| `FireCard` para usuario anónimo | El badge no debe renderizarse ni generar llamadas autenticadas para usuarios no logueados |
| Mapa Leaflet — capa de markers | El nuevo marcador diferenciado no debe romper el render de los markers estándar existentes |
| Rutas React | Si se agrega `/events/:id/recovery`, confirmar que no colisiona con rutas existentes |
| Llamadas a API desde frontend | Los nuevos fetch deben usar el interceptor de auth existente (`api.ts`) con JWT |

### 7.4 Regresiones en workers

| Escenario | Verificación |
|---|---|
| Celery Beat — schedule existente | La nueva cola `vae` no debe afectar el schedule de `ingestion` y `clustering` |
| Idempotencia de `analyze_recovery` | Si el worker se re-encola y ejecuta dos veces, no debe duplicar registros en `vegetation_monitoring` |
| Idempotencia de `detect_destruction` | Igual para `land_use_changes`; verificar si hay upsert o insert naïve |

---

## 8. Checklist de validación para Claude Code

### Backend

```bash
# 1. Verificar que el router VAE existe y tiene los endpoints correctos
grep -n "recovery\|land.use" app/api/routes/monitoring.py app/api/v1/monitoring.py 2>/dev/null

# 2. Verificar que main.py registra el router
grep -n "monitoring" app/main.py

# 3. Verificar cola de workers
grep -n "queue\|vae\|analysis" celery_app.py workers/tasks/recovery.py workers/tasks/destruction.py

# 4. Verificar autenticación en endpoints
grep -n "Depends\|get_current_user\|api_key" app/api/routes/monitoring.py 2>/dev/null || \
grep -n "Depends\|get_current_user\|api_key" app/api/v1/monitoring.py 2>/dev/null

# 5. Verificar rate limit en trigger
grep -n "rate_limit\|RateLimiter\|limiter" app/api/routes/monitoring.py 2>/dev/null || \
grep -n "rate_limit\|RateLimiter\|limiter" app/api/v1/monitoring.py 2>/dev/null

# 6. Confirmar que no hay paths duplicados en OpenAPI
python -c "from app.main import app; print([r.path for r in app.routes])" | grep -i monitoring
```

### Base de datos

```sql
-- Verificar RLS activa en tablas VAE
SELECT schemaname, tablename, policyname, roles, cmd
FROM pg_policies
WHERE tablename IN ('vegetation_monitoring', 'land_use_changes');

-- Verificar que anon no puede leer
-- (ejecutar con rol anon en Supabase SQL editor)
SET ROLE anon;
SELECT COUNT(*) FROM vegetation_monitoring; -- debe retornar error de permisos

-- Verificar integridad de baseline_ndvi
SELECT COUNT(*) FROM vegetation_monitoring WHERE baseline_ndvi IS NULL;
-- Documentar el resultado; estos registros deben retornar status: "pending"
```

### Frontend

```bash
# Verificar que FireCard no llama endpoints autenticados sin JWT
grep -rn "monitoring\|recovery\|land_use" frontend/src/components/ 2>/dev/null

# Verificar que los nuevos componentes usan el interceptor de auth
grep -rn "apiFetch\|api\.get\|supabase" frontend/src/components/RecoveryPanel.tsx 2>/dev/null || \
echo "Componente RecoveryPanel aún no existe"

# Confirmar que las rutas no colisionan
grep -rn "events/:id\|/recovery" frontend/src/App.tsx frontend/src/router/ 2>/dev/null
```

### Workers

```bash
# Verificar idempotencia de recovery worker
grep -n "upsert\|on_conflict\|INSERT.*ON CONFLICT" workers/tasks/recovery.py

# Verificar idempotencia de destruction worker
grep -n "upsert\|on_conflict\|INSERT.*ON CONFLICT" workers/tasks/destruction.py

# Verificar que el beat schedule no se rompe
python -c "from celery_app import celery_app; print(celery_app.conf.beat_schedule)"
```

---

## 9. Casos de prueba de referencia

| ID | Entrada | Pasos | Resultado esperado |
|---|---|---|---|
| CT-UCF12-01 | Evento con `baseline_ndvi` calculado | `GET /monitoring/recovery/:id` | Array de registros NDVI con `recovery_percentage` |
| CT-UCF12-02 | Cambio de uso simulado en worker | Ejecutar `detect_destruction` | Registro creado en `land_use_changes` con `status = pending_review` |
| CT-UCF12-03 | Nubosidad GEE > umbral | Ejecutar monitoreo | Reintento automático con ventana extendida; no error 500 |
| CT-UCF12-04 | Evento sin `baseline_ndvi` | `GET /monitoring/recovery/:id` | Respuesta 200 con `status: "pending"`, array vacío |
| CT-UCF12-05 | Request sin JWT | `GET /monitoring/recovery/:id` | 401 Unauthorized |
| CT-UCF12-06 | Request con JWT sin rol admin | `POST /monitoring/recovery/trigger` | 403 Forbidden |
| CT-UCF12-07 | Worker ejecutado dos veces para el mismo evento | Verificar `vegetation_monitoring` | Sin registros duplicados (idempotencia) |

---

## 10. Dependencias con otros casos de uso

| UC relacionado | Tipo de dependencia | Descripción |
|---|---|---|
| UC-F13 (agrupación macro) | Opcional | Los episodios de UC-F13 pueden enriquecer el contexto del análisis VAE, pero no es un prerequisito |
| UC-F08 (carrusel de imágenes) | Compartida | Ambos consumen `satellite_images`; confirmar que las políticas RLS no generan conflicto |
| UC-F09 (reporte de cierre) | Compartida | El reporte de cierre puede referenciar datos de `vegetation_monitoring`; no modificar campos que usa |
| UC-F11 (reportes especializados) | Consumidor | UC-F11 puede consumir datos de `vegetation_monitoring` para reportes judiciales; el schema debe mantenerse estable |

---

*Generado: 2026-02-22*
*Versión: 1.0*
*UC de referencia: UC-F12 — Recuperación y cambio de uso (VAE)*
*Estado del UC: en progreso — base técnica presente, no expuesta como flujo de producto maduro*
