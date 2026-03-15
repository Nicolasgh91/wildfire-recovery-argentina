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
- **Recuperación y NDVI**: análisis VAE y NDVI sobre episodios seleccionados. El baseline NDVI se calcula como composite de máximo NDVI (quality mosaic) sobre 12 meses pre-incendio, con fallback a 24 meses si no hay datos suficientes.

Para un detalle extendido de los flujos, ver `docs/architecture/flows.md`.

## Estado de features

El estado de producto se organiza por casos de uso funcionales.

- **UC-F01 contacto y soporte**: listo en producción, formulario público con adjuntos.
- **UC-F03 histórico y dashboard**: listo en producción, filtros, estadísticas y export.
- **UC-F06 verificar terreno**: listo en producción como módulo avanzado.
- **UC-F08 carrusel satelital de activos**: listo en producción, thumbnails operativos y refresco de imágenes.
- **UC-F11 exploración y reportes especializados**: listo en producción, wizard de exploración con assets HD y PDF.
- **UC-F12 recuperación y cambio de uso (VAE)**: en progreso, base técnica presente pero experiencia de producto en consolidación.

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
- Frontend estable para exploración, mapa, historial, login y contenido de soporte.
- Módulos con caveats: pagos (dependencias de webhook y sesión), citizen report (envío final mock), certificados y refugios (feature flags).
- Producto de recuperación y cambio de uso (VAE) en fase de consolidación de UX.

La referencia de estado detallado se encuentra en `docs/product/estado-real-del-producto.md`.

## Inconsistencias conocidas

Esta sección registra conflictos entre documentación y código o entre distintas fuentes de documentación.

- Pueden existir documentos históricos bajo `docs/archive/` que describen topologías de workers legacy. La topología vigente consolida workers en `worker-fast` y `worker-gee` según `docs/architecture/containers.md`.
- Algunos documentos de planificación bajo `docs/Carrusel fix/` describen comportamientos previos del carrusel que ya fueron endurecidos en la implementación actual de selección de imágenes y cobertura espacial.

Cualquier nueva inconsistencia detectada debe registrarse aquí sin modificar el código fuente de forma unilateral.

## Última actualización

- Fecha: 2026-03-15
- Commit: pendiente de actualizar al realizar el commit correspondiente
- Cambio: baseline NDVI por quality mosaic (12/24 meses pre-incendio), ver `docs/decisions/ADR-0002-baseline-ndvi-quality-mosaic.md`
