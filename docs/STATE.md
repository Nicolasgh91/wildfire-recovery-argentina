# Estado del sistema

## Resumen del sistema

ForestGuard (Vestigia) es una plataforma de exploración guiada de incendios históricos con evidencia satelital reproducible para personas no técnicas. El flujo principal conecta la ingesta de datos térmicos de NASA FIRMS, el procesamiento de eventos y episodios, la generación de imágenes satelitales y la visualización en el frontend.

- Exploración guiada de incendios históricos con generación de assets HD y reportes en PDF.
- Mapa y dashboard de incendios con filtros y estadísticas.
- Módulo avanzado de verificación de terreno con enfoque legal.
- Pagos y créditos mediante MercadoPago con caveats operativos.

## Flujos core

Los flujos core describen el recorrido de los datos desde la fuente externa hasta la interfaz de usuario.

- **Ingesta de detecciones**: descarga diaria de datos FIRMS, normalización y guardado en `fire_detections`.
- **Clustering de detecciones**: agrupación espacio-temporal en `fire_events`.
- **Episodios**: fusión de eventos en `fire_episodes` con perímetros y bounding boxes.
- **Selección de imágenes**: búsqueda de imágenes Sentinel-2, filtrado por nubosidad y cobertura espacial.
- **Thumbnails y carrusel**: renderizado de miniaturas (RGB, SWIR, NBR) y actualización de `slides_data`.
- **Recuperación y NDVI**: análisis VAE y NDVI sobre episodios seleccionados. El baseline NDVI se calcula en tres pasos: (1) quality mosaic 365 días pre-incendio, (2) 730 días pre-incendio si falla, (3) fallback post-incendio 180–540 días (6–18 meses) para eventos sin Sentinel-2 pre-incendio (p. ej. pre-2016). El origen del baseline se registra en `vegetation_monitoring.notes` (`baseline_v2_max_ndvi_annual`, `baseline_v2_post_fire_fallback`). La tarea Celery `recompute_baselines` (workers.tasks.backfill) permite re-procesar baselines mejorados para eventos que ya tienen monitoreo, sin recalcular NDVI actual.

Para un detalle extendido de los flujos, ver `docs/architecture/flows.md`.

## Estado de features

El estado de producto se organiza por casos de uso funcionales.

- **UC-F01 contacto y soporte**: listo en producción, formulario público con adjuntos.
- **UC-F03 histórico y dashboard**: listo en producción, filtros, estadísticas y export.
- **UC-F06 verificar terreno**: listo en producción como módulo avanzado. Los presets de área no seleccionados usan `variant="outline"` con clases `border-emerald-600 text-emerald-700 hover:bg-emerald-50` (dark: `border-emerald-500 text-emerald-400`); el preset seleccionado usa `variant="default"`. Los botones de paginación siguen el mismo patrón emerald; en estado `disabled` no muestran verde. La sección `result.fires` muestra `fire_event_id` truncado (8 chars) con tooltip del ID completo, fallback "N/D" cuando es null, y botón `ExternalLink` que navega a `/fires/:id` con `ReturnContext.audit` discriminado (`origin: 'search' | 'land-use'`). La columna de ID en grilla de episodios queda bloqueada por backend pendiente (ver `docs/tech_audit_debt.md`).
- **UC-F08 carrusel satelital de activos**: listo en producción, thumbnails operativos y refresco de imágenes.
- **UC-F11 exploración y reportes especializados**: listo en producción, wizard de exploración con assets HD y PDF.
- **UC-F12 recuperación y cambio de uso (VAE)**: en progreso, base técnica presente pero experiencia de producto en consolidación. La grilla de históricos (/fires/history) muestra estado de vegetación (badge por evento) y cada fila enlaza al detalle (/fires/:id), donde el RecoveryPanel muestra NDVI y métricas para eventos con datos VAE.

La tabla completa de casos de uso y estado se encuentra en `docs/product/casos-de-uso-y-estado.md`. Este archivo mantiene un resumen curado de alto nivel.

## Infraestructura y workers

La infraestructura se basa en servicios Docker orquestados con `docker-compose`, una base de datos Postgres con extensiones geoespaciales y Redis como broker de tareas.

Contenedores principales:

- **api**: servicio FastAPI que expone los endpoints públicos y autenticados.
- **frontend**: aplicación React + Vite que implementa las rutas de producto.
- **db**: instancia Postgres con soporte PostGIS para geometrías y consultas espaciales.
- **redis**: broker y backend de resultados para Celery.
- **worker-fast**: procesa colas `ingestion`, `clustering`, `reports`, `notification` y `default`.
- **worker-gee**: procesa colas `analysis` y `vae` y recibe tareas enrutadas a GEE y VAE.
- **celery-beat**: agenda tareas periódicas (ingesta, clustering, carrusel, cierres y limpieza).
- **flower**: dashboard de monitorización de tareas Celery.

Los detalles por contenedor, colas y tareas típicas se documentan en `docs/architecture/containers.md`.

## Estado actual

- Pipeline de ingesta, clustering y carrusel operativo en entorno de producción.
- Frontend estable para exploración, mapa, historial, login y contenido de soporte. La navegación entre Home/carrusel, grilla de históricos (`/fires/history`), mapa y detalle de incendio (`/fires/:id`) preserva la pantalla de origen mediante un contexto de retorno: el botón de volver en el mapa del detalle regresa al Home, Historial o Mapa según el flujo desde el que se llegó, y se oculta cuando no hay página previa (acceso directo o refresh).
- Módulos con caveats: pagos (dependencias de webhook y sesión), citizen report (envío final mock), certificados y refugios (feature flags).
- Producto de recuperación y cambio de uso (VAE) en fase de consolidación de UX.
- Fase F1 de geocodificación completada (`assign_province_department` + checks) y F1-BIS cerrada: `regions` poblada con `DEPARTAMENTO` (`529`) y `PROVINCIA` (`24`), validación de Córdoba (`Córdoba/Capital`) correcta y backfill histórico de `fire_events` ejecutado por batches.
- Fase F2 integrada en clustering de detecciones: cada `fire_event` nuevo intenta resolver `province`/`department` desde `assign_province_department` al momento del `INSERT` (con fallback a `NULL` + warning cuando no hay cobertura). La propagación de `provinces` en `fire_episodes` continúa resuelta en `EpisodeService.update_episode_metrics`.
- Hardening operativo F2 en tasks: `cluster_detections` ejecuta fallback post-clustering para geo-asignar eventos recientes sin `province/department` usando `assign_province_department`, y `cluster_fire_episodes` sincroniza explícitamente `fire_episodes.provinces` desde `fire_events` vinculados.
- Fase F3 integrada en workers: disponible ingesta manual desde CSV local (`workers.tasks.ingestion.ingest_firms_csv`) y orquestación completa (`workers.tasks.ingestion.run_full_ingestion_pipeline`) con cadena `ingesta -> cluster_detections(days_back=30) -> cluster_fire_episodes_pipeline`.
- Fase F4 integrada en API: endpoints admin `POST /api/v1/admin/ingest-firms` (upload + encolado) y `GET /api/v1/admin/ingest-firms/{task_id}` (estado), con validaciones de rol admin, tamaño/headers de CSV, almacenamiento temporal y rate limit operacional.

La referencia de estado detallado se encuentra en `docs/product/estado-real-del-producto.md`.

## Inconsistencias conocidas

Esta sección registra conflictos entre documentación y código o entre distintas fuentes de documentación.

- Pueden existir documentos históricos bajo `docs/archive/` que describen topologías de workers legacy. La topología vigente consolida workers en `worker-fast` y `worker-gee` según `docs/architecture/containers.md`.
- Algunos documentos de planificación bajo `docs/Carrusel fix/` describen comportamientos previos del carrusel que ya fueron endurecidos en la implementación actual de selección de imágenes y cobertura espacial.

Cualquier nueva inconsistencia detectada debe registrarse aquí sin modificar el código fuente de forma unilateral.

## Última actualización

- Fecha: 2026-03-27
- Commit: pendiente de actualizar al realizar el commit correspondiente
- Cambio: cierre del gap central F2 solicitado en tasks de clustering. Se agregó fallback idempotente de asignación `province/department` en `workers/tasks/clustering.py` y sincronización explícita de `provinces[]` en `workers/tasks/clustering_task.py`, manteniendo intacta la lógica ST-DBSCAN y merge de episodios.
