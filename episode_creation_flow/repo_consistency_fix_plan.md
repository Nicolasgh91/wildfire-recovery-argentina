# Plan de corrección por PRs pequeños y testeables

Fecha: 2026-02-16  
Objetivo: cerrar hallazgos FG-EP-CHECK con bajo riesgo y validación incremental.

## Orden recomendado
1. **PR1 (bloqueantes operativos/runtime)**
2. **PR2 (altas funcionales pipeline)**
3. **PR3 (medias/bajas + hardening/observabilidad)**

---

## PR1 — Bootstrap Celery robusto + limpieza de colisiones de tasks

### Alcance
- Resolver hallazgos: **FG-EP-CHECK-03**, **FG-EP-CHECK-04**.

### Cambios esperados
1. Validación explícita de `DATABASE_URL` para workers con error accionable (startup check).
2. Opcional: lazy init de `engine` para reducir fallas en import-time.
3. Eliminar/aislar módulos legacy con task names duplicados en `app/services/` (o renombrar nombres de task fuera de namespace `workers.tasks.*`).
4. Agregar smoke test de registry Celery que valide:
   - tasks críticas presentes,
   - no duplicidad de nombres.

### Archivos objetivo (estimados)
- `app/db/session.py`
- `workers/celery_app.py`
- `app/services/clustering.py` (legacy)
- `app/services/destruction.py` (legacy)
- tests nuevos en `tests/unit/` o `tests/integration/` para smoke Celery

### Riesgos
- Cambiar init de DB puede impactar tests que asumen engine global inmediato.
- Remover módulos legacy puede romper imports residuales ocultos.

### Tests de regresión
- `python -c "from workers.celery_app import celery_app; celery_app.loader.import_default_modules(); print('ok')"`
- suite smoke Celery dedicada
- subset de tests de workers críticos

### Criterios de aceptación
- Worker arranca con mensaje claro cuando falta config crítica.
- No existe colisión de task names en namespace productivo.
- Smoke de registry pasa en CI.

---

## PR2 — Alineación canónica del clustering de episodios + ingestión real

### Alcance
- Resolver hallazgos: **FG-EP-CHECK-01**, **FG-EP-CHECK-05**.

### Cambios esperados
1. `ClusteringService` debe leer `episode_spatial_epsilon_meters` y `episode_temporal_window_hours` desde `system_parameters` (vía helper canónico), con fallback seguro por entorno.
2. Mantener `clustering_versions` para trazabilidad/versionado, no como fuente principal de parámetros operativos (o documentar precedencia explícita si se decide lo contrario).
3. Integrar `download_firms_daily` con ingestión real (script/servicio) e idempotencia por lote/detección.
4. Añadir métricas de resultado de ingestión y de clustering episodio.

### Archivos objetivo (estimados)
- `app/services/clustering_service.py`
- `workers/tasks/ingestion.py`
- servicio/script de ingestión real (según diseño actual)
- tests de integración de pipeline y parámetros

### Riesgos
- Cambios en parámetros pueden mover frontera de clustering y modificar historiales esperados.
- Integración de ingestión puede aumentar carga DB si no hay batching/índices adecuados.

### Tests de regresión
- unit: resolución de parámetros canónicos episodio
- integración: fixture de eventos borde (espacio/tiempo)
- integración: ingestión idempotente (doble corrida no duplica)

### Criterios de aceptación
- Cambiar `system_parameters` impacta clustering de episodios sin tocar código.
- Worker de ingestión deja de ser stub y produce inserciones reales deduplicadas.

---

## PR3 — Consistencia de estados legacy, carrusel y enriquecimientos geográficos

### Alcance
- Resolver hallazgos: **FG-EP-CHECK-02**, **FG-EP-CHECK-06**, **FG-EP-CHECK-07**, **FG-EP-CHECK-08**.

### Cambios esperados
1. Eliminar referencias legacy a `controlled` en resolución de estado de episodios.
2. Unificar límite canónico de carrusel (generación + endpoints Home) en un parámetro único.
3. Definir task de enriquecimiento geográfico incremental (provincia/intersecciones áreas protegidas) y encadenarla tras clustering.
4. Refactor de subtasks bloqueantes (`.get()`) a canvas Celery (`chain/group/chord`) en tasks de análisis.
5. Incorporar métricas operativas sugeridas (duración, errores, throughput).

### Archivos objetivo (estimados)
- `app/services/episode_service.py`
- `app/services/imagery_service.py`
- `app/api/routes/episodes.py`
- `app/api/v1/fires.py` (si aplica)
- `workers/tasks/destruction.py`
- nuevo task de geo-enrichment + wiring en `workers/celery_app.py`

### Riesgos
- Ajustes de reglas de Home pueden cambiar contenido visible (producto/UI).
- Enriquecimiento incremental requiere cuidado para no bloquear colas de clustering.

### Tests de regresión
- unit: estado episodio sólo con set canónico
- integración: Home respeta límite único y thumbnails obligatorias
- integración: enriquecimiento geo post-clustering
- tests de orquestación Celery sin bloqueos por `.get()`

### Criterios de aceptación
- No queda lógica runtime dependiente de estados legacy.
- Generación/publicación de carrusel usa mismo límite canónico.
- Pipeline operativo incluye enriquecimiento geo reproducible.
- Tasks encadenadas no bloquean worker threads/processes.

---

## Checklist global de aceptación

- [ ] Hallazgos bloqueantes y alta severidad cerrados en PR1/PR2.
- [ ] Todos los PRs incluyen tests nuevos o ajustados y CI en verde.
- [ ] Documentación técnica actualizada (flujo, parámetros, colas, tasks).
- [ ] Smoke de Celery y pipeline mínimo pasan en entorno local/CI.
- [ ] Se define dueño operativo de parámetros canónicos y del schedule de enriquecimientos.

