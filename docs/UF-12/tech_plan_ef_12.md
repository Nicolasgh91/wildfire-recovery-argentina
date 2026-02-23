Contexto
Analisis critico del plan de ejecucion definido en docs/UF-12/UC_F12_implementation_spec.md, cruzado contra el codigo fuente real del repositorio y el schema actual de Supabase (schema_v5).
Archivos inspeccionados: app/services/vae_service.py, app/api/routes/monitoring.py, app/main.py, celery_app.py, workers/tasks/recovery.py, workers/tasks/destruction.py, frontend/src/pages/FireDetail.tsx, frontend/src/components/fire-card.tsx, frontend/src/components/ndvi-chart.tsx, frontend/src/components/map/layers/FireMarkers.tsx, frontend/src/App.tsx, app/core/rate_limiter.py, app/api/auth_deps.py, schema Supabase v5.

1. ERRORES DE LOGICA
1.1 Workers son stubs puros — nunca persisten datos [CRITICO]
Archivos: workers/tasks/recovery.py:37-57, workers/tasks/destruction.py:41-62
Ambos workers retornan diccionarios con valores hardcodeados. No instancian VAEService, no consultan GEE, no escriben en la base de datos:
python# recovery.py:46-54
result = {
    'fire_event_id': fire_event_id,
    'recovery_percentage': 45.7,  # hardcodeado
    'ndvi_change': 0.23,          # hardcodeado
    'vegetation_status': 'recovering',
    ...
}
return result  # retorna dict, no persiste nada
Impacto: La spec asume (seccion 4.3) que los workers escriben en vegetation_monitoring y land_use_changes. Ambas tablas permanecen vacias. Los endpoints que lean de BD nunca encontraran datos. El endpoint actual de recovery (monitoring.py:328-425) llama directamente a VAEService en tiempo real como workaround, pero esto viola las restricciones de cuota (seccion 3.1).
Correccion: Reescribir los workers para:

Obtener geometria del evento desde fire_events (centroid, perimeter)
Instanciar VAEService y ejecutar analyze_recovery() / detect_land_use_change()
Persistir resultados en vegetation_monitoring / land_use_changes con upsert

1.2 Schema carece de UNIQUE constraint para idempotencia [CRITICO]
Tabla: vegetation_monitoring en schema v5
La tabla no tiene ningun UNIQUE constraint compuesto sobre (fire_event_id, monitoring_date) o (fire_event_id, months_after_fire). Esto hace imposible implementar un upsert seguro via ON CONFLICT. La PK es solo id (UUID autogenerado).
sql-- Schema actual: solo tiene PK en id
CONSTRAINT vegetation_monitoring_pkey PRIMARY KEY (id)
-- NO hay: UNIQUE (fire_event_id, monitoring_date)
Impacto: CT-UCF12-07 (idempotencia) no se puede resolver solo con logica de aplicacion. Sin un UNIQUE constraint, INSERT ... ON CONFLICT no tiene clausula sobre la cual actuar.
Correccion obligatoria: Agregar migracion:
sqlALTER TABLE vegetation_monitoring
  ADD CONSTRAINT uq_vm_event_date UNIQUE (fire_event_id, monitoring_date);
Lo mismo aplica a land_use_changes, que tampoco tiene constraint unico en (fire_event_id, change_detected_at).
1.3 Columna anomaly_type no existe en vegetation_monitoring [ALTO]
Archivo: app/api/routes/monitoring.py:196
El endpoint GET /monitoring/recovery/summary hace un JOIN que lee vm.anomaly_type:
sqlSELECT ... vm.anomaly_type
FROM fire_events fe
LEFT JOIN LATERAL (
    SELECT months_after_fire, recovery_percentage, anomaly_type  -- ← no existe
    FROM vegetation_monitoring ...
) vm ON true
Pero en el schema v5, la tabla vegetation_monitoring no tiene columna anomaly_type. Las columnas relevantes son:

land_use_classification (varchar)
human_activity_detected (boolean)
activity_type (varchar)

Impacto: Este query falla con error de columna desconocida. El catch generico en linea 219 lo silencia retornando results = [], enmascarando el bug.
Correccion: Reemplazar vm.anomaly_type por vm.activity_type y ajustar la logica de deteccion de is_suspicious en las lineas 258-266 para usar los campos reales.
1.4 monitoring_record_id en land_use_changes sin FK constraint [MEDIO]
Schema v5: La columna monitoring_record_id uuid existe en land_use_changes, pero no tiene constraint FK definido. La spec (seccion 3.3) dice: "FK opcional a vegetation_monitoring(id) (campo monitoring_record_id)".
Sin FK, la integridad referencial no se garantiza a nivel de BD. Un worker podria insertar un monitoring_record_id invalido sin error.
Correccion:
sqlALTER TABLE land_use_changes
  ADD CONSTRAINT land_use_changes_monitoring_record_id_fkey
  FOREIGN KEY (monitoring_record_id) REFERENCES vegetation_monitoring(id);
1.5 SQL defectuoso en query de summary: INTERVAL no se parametriza [ALTO]
Archivo: app/api/routes/monitoring.py:208
sqlAND fe.start_date < NOW() - INTERVAL ':min_months months'
SQLAlchemy text() no puede parametrizar dentro de un string literal de INTERVAL. El :min_months dentro de comillas simples es texto literal, no un bind parameter. La query falla silenciosamente o filtra mal.
Correccion:
sqlAND fe.start_date < NOW() - (INTERVAL '1 month' * :min_months)
1.6 recovery_percentage calcula ratio simple, no recuperacion real [BAJO]
Archivo: app/services/vae_service.py:302-303
pythonrecovery_pct = min(100, max(0, (current_ndvi / baseline_ndvi) * 100))
Calcula current/baseline * 100. Para un incendio que bajo NDVI de 0.6 a 0.1 y ahora esta en 0.35:

Formula actual: 0.35/0.6 * 100 = 58%
Recuperacion real: (0.35 - 0.1) / (0.6 - 0.1) * 100 = 50%

Recomendacion: Si se mantiene la formula actual, documentar explicitamente en la API que recovery_percentage es "porcentaje del NDVI baseline alcanzado" (no "porcentaje recuperado desde el nadir post-incendio").

2. SEGURIDAD
2.1 Endpoints de monitoring expuestos sin autenticacion [CRITICO]
Archivo: app/main.py:236-240
pythonapp.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    # ← SIN dependencies=[Depends(get_current_user)]
)
Comparar con reports (linea 248) que SI tiene dependencies=[Depends(get_current_user)].
Esto viola la restriccion 3.2 de la spec: "Autenticacion obligatoria: todos los endpoints deben requerir JWT." y el caso de prueba CT-UCF12-05 (401 sin JWT).
Correccion inmediata:
pythonapp.include_router(
    monitoring.router,
    prefix=f"{settings.API_V1_PREFIX}/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(get_current_user)],
)
2.2 Endpoint POST /trigger no implementado [CRITICO]
Archivo: app/api/routes/monitoring.py — No existe. La spec (seccion 6.1) exige:

POST /api/v1/monitoring/recovery/trigger → 202 (admin), 403 (no-admin), 429 (rate limit)
Rate limit para proteger cuota GEE (seccion 3.1)

Sin este endpoint, no hay forma controlada de disparar el procesamiento VAE.
2.3 Endpoint GET /land-use-changes no implementado [ALTO]
Toda la tabla land_use_changes no tiene endpoint de lectura. La spec lo requiere en seccion 2.2 y 6.1.
2.4 RLS ausente en tablas de monitoreo [ALTO]
Las tablas vegetation_monitoring y land_use_changes no tienen politicas RLS. Si Supabase tiene RLS habilitado por default (como es comun), esto significa que las queries directas fallaran para todos los roles. Si RLS no esta habilitado, el rol anon tiene acceso de lectura a datos sensibles de monitoreo.
La spec (seccion 6.3) provee las politicas exactas necesarias.
2.5 Error messages exponen internals de GEE [BAJO]
Archivo: app/api/routes/monitoring.py:423
pythonraise HTTPException(status_code=503, detail=f"Error processing NDVI analysis: {str(e)}")
str(e) puede contener URLs internas de GEE, tokens de servicio, o paths de infraestructura.
Correccion: Loguear str(e) con logger.error() y retornar mensaje generico: "Servicio de analisis temporalmente no disponible".

3. ROBUSTEZ
3.1 Cola analysis compartida — incumplimiento arquitectonico [ALTO]
Archivo: celery_app.py:69-73
python'workers.tasks.recovery.analyze_recovery': {'queue': 'analysis'},
'workers.tasks.destruction.detect_destruction': {'queue': 'analysis'},
'workers.tasks.carousel_task.generate_carousel': {'queue': 'analysis'},
La spec (seccion 3.2): "Colas separadas obligatorias: la documentacion de arquitectura establece explicitamente que VAE debe usar colas separadas de los workers de reportes (ERS) para evitar bloqueo."
generate_carousel puede ejecutarse por minutos, bloqueando la cola analysis para recovery/destruction.
Correccion: Separar a cola vae y agregar 'vae' al include de celery_app:
python'workers.tasks.recovery.analyze_recovery': {'queue': 'vae'},
'workers.tasks.destruction.detect_destruction': {'queue': 'vae'},
3.2 _get_baseline_ndvi retorna fallback 0.45 silenciosamente [ALTO]
Archivo: app/services/vae_service.py:704-707
pythonexcept GEEImageNotFoundError:
    logger.warning("No pre-fire image found, using default baseline")
    return 0.45
La spec (seccion 3.3): "El campo baseline_ndvi es critico: sin el, el estado del evento debe ser pending (CT-UCF12-04). No se debe retornar error 500, sino un estado explicito."
El fallback 0.45 produce datos ficticios que se presentan al usuario como reales. Un incendio en zona de bosque denso (baseline real ~0.75) tendria calculos de recuperacion completamente erroneos.
Correccion: El VAEService deberia:

Re-lanzar la excepcion (o una excepcion custom BaselineNotAvailableError)
El endpoint atrapa esta excepcion y retorna {"status": "pending", "monitoring_data": [], "baseline_ndvi": null}

3.3 Endpoint de recovery llama GEE en tiempo real sin cache [ALTO]
Archivo: app/api/routes/monitoring.py:370-376
Cada GET /monitoring/recovery/{fire_event_id} instancia VAEService() y ejecuta get_recovery_timeline() que internamente hace hasta 36 llamadas a GEE (una por mes, via get_recovery_time_series con interval_months=1).
Segun la propia documentacion del endpoint (linea 319): "Initial call may be slow (10-30s) due to GEE processing."
Impacto:

36 requests GEE * N usuarios concurrentes = agotamiento de cuota
Latencia 10-30s inaceptable para UX
Un refresh del browser duplica todas las llamadas

Patron correcto (alineado con la spec):

El endpoint lee de vegetation_monitoring (BD)
Si no hay datos, retorna status: "pending" y opcionalmente encola un job
Los workers populan la BD periodicamente via Celery Beat

3.4 No hay manejo de nubosidad (CT-UCF12-03) [MEDIO]
Archivo: app/services/vae_service.py:715-717
_get_current_ndvi usa max_cloud_cover=30. Si no hay imagen disponible con <30% nubosidad, GEE lanza GEEImageNotFoundError. No hay reintento con ventana temporal extendida como exige CT-UCF12-03.
Correccion en _get_current_ndvi: Implementar fallback escalonado:
pythonfor max_cloud in [30, 50, 70]:
    for window_days in [30, 60, 90]:
        try:
            collection = self._gee.get_sentinel_collection(
                bbox=bbox, start_date=target - timedelta(days=window_days),
                end_date=target + timedelta(days=window_days), max_cloud_cover=max_cloud
            )
            ...
            return ndvi_result.mean
        except GEEImageNotFoundError:
            continue
raise GEEImageNotFoundError("No image found after extended search")
3.5 batch_recovery_analysis enruta a cola analysis en vez de vae [BAJO]
Archivo: workers/tasks/recovery.py:88
pythonanalyze_recovery.s(fire_id, months).set(queue='analysis')
Si se cambia la cola principal a vae, este hardcode en batch_recovery_analysis seguira enviando a analysis.
3.6 is_potential_violation es nullable en schema [MEDIO]
Schema v5: is_potential_violation boolean DEFAULT false — tiene DEFAULT pero no tiene constraint NOT NULL. La spec (seccion 3.3) exige: "su valor no debe ser null en registros persistidos."
Correccion:
sqlALTER TABLE land_use_changes
  ALTER COLUMN is_potential_violation SET NOT NULL;

4. ESCALABILIDAD
4.1 36 llamadas GEE por request de timeline [CRITICO]
Archivo: app/services/vae_service.py:441
get_recovery_timeline() llama a get_recovery_time_series(interval_months=1, max_months=36). Esto genera hasta 36 iteraciones, cada una con analyze_recovery() que a su vez llama _get_current_ndvi() (1 request GEE cada una). Mas la llamada a _get_baseline_ndvi() = 37 requests GEE por request HTTP.
Con el free tier de 50,000 req/dia:

1,351 requests de timeline/dia maximo
40 simultaneas → con 37 por request, solo 1 usuario puede usar el timeline a la vez

4.2 Crecimiento descontrolado de vegetation_monitoring [MEDIO]
36 registros/mes por evento * N eventos activos * 12 meses/ano. Con 1,000 eventos:

36,000 registros/ano = manejable
Pero sin indice en (fire_event_id, monitoring_date), las queries de timeline seran lentas

Recomendacion: Crear indice compuesto:
sqlCREATE INDEX idx_vm_event_date ON vegetation_monitoring(fire_event_id, monitoring_date);
4.3 VAEService se instancia en cada request [BAJO]
Archivo: app/api/routes/monitoring.py:371
pythonvae = VAEService()
Cada request crea un nuevo GEEService() y StorageService(). Si estos inicializan conexiones o autenticacion, esto multiplica el overhead.
Correccion: Usar get_vae_service() como dependency injection de FastAPI (ya existe en vae_service.py:967) con un singleton scoped.

5. UI/UX
5.1 RecoveryStatusBadge no existe [FALTANTE]
Archivo: frontend/src/components/fire-card.tsx
Solo tiene badges de severity y status. No hay badge de estado de recuperacion. La spec (seccion 5.2) requiere un chip de color con estado: sin monitoreo / en recuperacion / estancado / alerta.
Patron recomendado: Crear RecoveryStatusBadge.tsx que mapee:

null → no renderizar (usuario anonimo o sin datos)
not_started → gris "Sin monitoreo"
early_recovery / moderate_recovery → amarillo "En recuperacion"
advanced_recovery / full_recovery → verde "Recuperado"
anomaly_detected → rojo "Alerta"

5.2 FireDetail sin seccion Recuperacion [FALTANTE]
Archivo: frontend/src/pages/FireDetail.tsx
Solo muestra: mapa, info cards, quality indicator, areas protegidas, stats. La spec exige RecoveryPanel con:

RecoveryTimeline (grafico NDVI)
Lista de LandUseChangeCard

Este panel debe ser condicional al estado de autenticacion (seccion 6.4): visible solo con sesion activa.
5.3 NdviChart existe pero con interfaz incompatible [MEDIO]
Archivo: frontend/src/components/ndvi-chart.tsx:14-16
tsxinterface NdviChartProps {
  data: { month: string; value: number }[]
}
La respuesta del API devuelve MonthlyNDVI:
pythonclass MonthlyNDVI:
    month: int       # ← es int, no string
    date: str
    ndvi_mean: float # ← se llama ndvi_mean, no value
    recovery_percentage: Optional[float]
    cloud_cover_pct: Optional[float]
Ademas, el componente actual:

No muestra linea de baseline (solo una ReferenceLine fija en y=0.5)
No tiene gradiente de color por zona de recuperacion
No muestra tooltips con recovery_percentage

5.4 Mapa sin diferenciacion para violaciones [FALTANTE]
Archivo: frontend/src/components/map/layers/FireMarkers.tsx
Los markers usan solo severity para determinar icono/color. La spec (seccion 5.3) requiere icono rojo especial para is_potential_violation = true.
5.5 Ruta /fires/:id es publica — seccion recuperacion debe ser condicional [MEDIO]
Archivo: frontend/src/App.tsx:146
tsx<Route path="/fires/:id" element={<FireDetailPage />} />
No usa ProtectedRoute (correcto, la pagina base debe ser publica). Pero la seccion de recuperacion dentro de ella debe renderizarse solo para usuarios autenticados, sin generar fetch no autenticados. Esto requiere useAuth() dentro de FireDetail para renderizado condicional del RecoveryPanel.

6. INCONSISTENCIAS ENTRE SPEC Y CODEBASE
6.1 Numeracion de UC conflictiva [MEDIO]
Archivo: app/main.py:123-126
python{
    "name": "visitor-logs",
    "description": "**Visitor Logs (UC-12)** - Offline-first visitor registration records."
}
```

El tag OpenAPI asigna UC-12 a "Visitor Logs", pero la spec es UC-F12 para "Recuperacion y cambio de uso (VAE)". Hay conflicto de namespace. La spec usa `UC-F12` (con F), lo cual implica que es un UC de feature adicional vs el UC-12 core. Pero el tag en `main.py` usa "UC-12" sin F.

**Recomendacion:** Crear un tag separado `"monitoring"` o `"vae"` para los endpoints de UC-F12, independiente del tag `"visitor-logs"`.

### 6.2 La spec referencia `app/api/v1/monitoring.py` — no existe [BAJO]

**Seccion 1.3 y 4.1 de la spec:** Lista `app/api/v1/monitoring.py` como archivo a inspeccionar. Solo existe `app/api/routes/monitoring.py`. La spec debe actualizarse.

### 6.3 `schema_v_4.sql` referenciado no existe [BAJO]

La spec (seccion 1.1) referencia `schema_v_4.sql`. El schema real es v5 y no estaba en el repo. Esto dificulta la verificacion automatizada descrita en la seccion 8.

### 6.4 Discrepancia ruta frontend: spec dice `/events/:id`, codigo usa `/fires/:id` [MEDIO]

**Spec seccion 5.1:** "Detalle de evento `/events/:id`"
**Codigo real:** `App.tsx:146` → `<Route path="/fires/:id" ...>`

Si se implementa como dice la spec, habria ruta huerfana. El frontend usa `/fires/:id` consistentemente.

---

## 7. DEFECTOS EN LA PROPIA SPEC

### 7.1 La spec no define el modelo de respuesta de `land-use-changes` [MEDIO]

Seccion 6.1 dice:
```
GET /api/v1/monitoring/land-use-changes/{fire_event_id}
    → 200: array de cambios detectados
Pero no define el schema de respuesta. Los campos disponibles en la tabla son:
change_type, change_severity, affected_area_hectares, is_potential_violation, violation_confidence, status, change_detected_at, months_after_fire, notes
Se deberia definir un LandUseChangeResponse Pydantic model en la spec.
7.2 La spec no define estrategia de poblacion inicial de datos [ALTO]
La spec asume que los workers ya escriben datos, pero son stubs. No hay instrucciones para:

Backfill historico (eventos existentes sin datos de monitoreo)
Estrategia de procesamiento inicial (que eventos procesar primero)
Limites de batch para el backfill (evitar agotar cuota GEE)

7.3 La spec no menciona indices de BD necesarios [MEDIO]
Para que los endpoints funcionen con performance aceptable, se necesitan:
sqlCREATE INDEX idx_vm_event_date ON vegetation_monitoring(fire_event_id, monitoring_date);
CREATE INDEX idx_luc_event ON land_use_changes(fire_event_id, change_detected_at);
7.4 La spec no define comportamiento del RecoveryStatusBadge en estado de carga [BAJO]
Si el FireCard muestra un badge de recuperacion, necesita hacer un fetch por cada card en el listado. Con 50 cards visibles:

50 requests simultaneos a /monitoring/recovery/{id} (si lee de GEE = 50*37 = 1,850 GEE requests)
O 50 queries a BD (aceptable)

La spec deberia especificar que el badge se obtiene de un campo ya incluido en la respuesta de listado de eventos (e.g., ultimo recovery_status cacheado en fire_events), no de un fetch individual.

8. PLAN DE CORRECCIONES PRIORIZADO
P0 — Seguridad (bloquean deploy)
#CorreccionArchivoEsfuerzo1Agregar dependencies=[Depends(get_current_user)] al router monitoringapp/main.py:2361 linea2Crear endpoint POST /monitoring/recovery/trigger con admin check + rate limitapp/api/routes/monitoring.py~50 lineas3Crear endpoint GET /monitoring/land-use-changes/{fire_event_id} con authapp/api/routes/monitoring.py~40 lineas4Sanitizar error messages (no exponer str(e))app/api/routes/monitoring.py:4233 lineas5Crear migracion RLS (spec seccion 6.3 provee SQL exacto)Supabase migration8 lineas SQL
P1 — Integridad de datos (funcionalidad rota)
#CorreccionArchivoEsfuerzo6Agregar UNIQUE constraint (fire_event_id, monitoring_date) en vegetation_monitoringMigracion SQL2 lineas7Agregar UNIQUE constraint (fire_event_id, change_detected_at) en land_use_changesMigracion SQL2 lineas8Agregar NOT NULL a is_potential_violationMigracion SQL1 linea9Agregar FK constraint en monitoring_record_idMigracion SQL2 lineas10Agregar indice (fire_event_id, monitoring_date) en vegetation_monitoringMigracion SQL1 linea11Corregir referencia a anomaly_type → activity_type en query summarymonitoring.py:1963 lineas12Corregir SQL INTERVAL parametrizationmonitoring.py:2081 linea
P2 — Logica de negocio
#CorreccionArchivoEsfuerzo13Reescribir analyze_recovery worker (VAEService + persistencia + upsert)workers/tasks/recovery.py~100 lineas14Reescribir detect_destruction worker (VAEService + persistencia + upsert)workers/tasks/destruction.py~80 lineas15Endpoint recovery: leer de BD primero, GEE solo como fallback asyncmonitoring.py:328-425~60 lineas16Separar cola vae de analysiscelery_app.py:69-734 lineas17Corregir _get_baseline_ndvi para propagar error en vez de fallback 0.45vae_service.py:704-707~10 lineas18Implementar reintento con ventana extendida por nubosidad (CT-UCF12-03)vae_service.py:709-722~20 lineas
P3 — Frontend
#CorreccionArchivoEsfuerzo19Crear RecoveryStatusBadgeNuevo componente~40 lineas20Crear RecoveryPanel con RecoveryTimeline + LandUseChangeCardNuevo componente~150 lineas21Integrar en FireDetail condicional a authFireDetail.tsx~30 lineas22Adaptar NdviChart para formato real del API + linea baselinendvi-chart.tsx~25 lineas23Agregar marcador diferenciado en mapa para is_potential_violationFireMarkers.tsx~20 lineas24Agregar badge de recovery a FireCard condicional a authfire-card.tsx~15 lineas
P4 — Escalabilidad
#CorreccionArchivoEsfuerzo25Agregar tarea Celery Beat para procesamiento periodico VAEcelery_app.py~15 lineas26Definir estrategia de backfill con batchingworkers/tasks/recovery.py~30 lineas

9. TESTS DE VERIFICACION
Regresion backend
bash# Confirmar auth obligatoria
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/monitoring/recovery/summary
# Esperado: 401 (actualmente: 200 ← BUG)

# Confirmar que el trigger no existe
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/monitoring/recovery/trigger
# Esperado: 405 o 401 (actualmente: 405 ← falta implementar)
Integridad de schema
sql-- Verificar que el UNIQUE constraint existe despues de migracion
SELECT conname FROM pg_constraint
WHERE conrelid = 'vegetation_monitoring'::regclass AND contype = 'u';
-- Esperado: uq_vm_event_date

-- Verificar RLS activa
SELECT tablename, policyname FROM pg_policies
WHERE tablename IN ('vegetation_monitoring', 'land_use_changes');
-- Esperado: 4 politicas (2 por tabla)
Idempotencia de workers (CT-UCF12-07)
sql-- Antes de ejecutar worker 2 veces
SELECT COUNT(*) FROM vegetation_monitoring WHERE fire_event_id = :test_id;
-- Ejecutar worker 2 veces con mismo fire_event_id y monitoring_date
-- Despues
SELECT COUNT(*) FROM vegetation_monitoring WHERE fire_event_id = :test_id;
-- Debe ser igual al primer count (no duplicados)