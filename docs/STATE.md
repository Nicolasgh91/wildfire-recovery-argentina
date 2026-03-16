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
- **UC-F06 verificar terreno**: listo en producción como módulo avanzado. Los CTAs secundarios de auditoría (presets de área, paginación e ingreso a detalle en `result.fires`) usan la opción A de estilos emerald documentada en `tasks_UC-06.md`: botones no seleccionados con `variant="outline"` y clases `border-emerald-600 text-emerald-700 hover:bg-emerald-50`, y botón seleccionado sin clases emerald adicionales. La grilla de resultados de búsqueda (`/audit/search`) incorpora una columna de \"ID de incendio\" que muestra el `fire_event_id` representativo de cada episodio (UUID truncado con tooltip de valor completo) y permite navegar al detalle `/fires/:id` cuando existe evento asociado; en ausencia de evento se muestra `N/D` sin link.
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

La referencia de estado detallado se encuentra en `docs/product/estado-real-del-producto.md`.

## Inconsistencias conocidas

Esta sección registra conflictos entre documentación y código o entre distintas fuentes de documentación.

- Pueden existir documentos históricos bajo `docs/archive/` que describen topologías de workers legacy. La topología vigente consolida workers en `worker-fast` y `worker-gee` según `docs/architecture/containers.md`.
- Algunos documentos de planificación bajo `docs/Carrusel fix/` describen comportamientos previos del carrusel que ya fueron endurecidos en la implementación actual de selección de imágenes y cobertura espacial.

Cualquier nueva inconsistencia detectada debe registrarse aquí sin modificar el código fuente de forma unilateral.

## Última actualización

- Fecha: 2026-03-16
- Commit: pendiente de actualizar al realizar el commit correspondiente
- Cambio: Ajustes de UC-F06 — backend de `/audit/search` extendido con `fire_event_id` por episodio (join vía `fire_episode_events` + `fire_events` con criterio `max_frp DESC, start_date ASC`), navegación de auditoría hacia `/fires/:id` con `ReturnContext.audit` minimal (búsqueda textual: `{ origin: 'search', q, radius_km, page }`; búsqueda puntual: `{ origin: 'land-use', lat, lon, radius_m, page }`), y contrato de estilos de botones que alinea presets, paginación y botones secundarios de auditoría con la opción emerald documentada (outline verde solo en botones no seleccionados y habilitados).
