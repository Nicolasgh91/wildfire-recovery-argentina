# Casos de Uso — ForestGuard

Documentación detallada de los casos de uso implementados en la plataforma ForestGuard.

---

## UC-F01: Contacto y soporte

**Estado**: Implementado

Formulario de contacto con soporte para archivos adjuntos (máx 5MB, PDF/JPG/PNG), validación server-side y rate limiting por IP. El sistema soporta dos modos de envío: asíncrono vía Celery (cuando Redis está disponible) y sincrónico como fallback (envío SMTP directo cuando la cola no está operativa).

**Fuentes de datos**: Ninguna externa.
**Endpoints**: `POST /api/v1/contact`
**Servicios**: `contact_service.py`, SMTP
**Workers**: `notification.py` (queue: ingestion, cuando disponible)

---

## UC-F02: Estadísticas públicas

**Estado**: Implementado

Endpoint público que expone datos agregados y anónimos sobre incendios: total de eventos registrados, distribución por provincia, severidad promedio y hectáreas totales estimadas. Implementado como Supabase Edge Function con cache HTTP para minimizar carga sobre la base de datos.

**Fuentes de datos**: PostgreSQL (datos agregados).
**Endpoints**: `GET /functions/v1/public-stats`
**Servicios**: Supabase Edge Function

---

## UC-F03: Histórico y dashboard

**Estado**: Implementado

Dashboard interactivo que permite explorar el historial completo de incendios registrados en Argentina. Incluye filtros por provincia, rango de fechas, severidad y estado. Presenta KPIs resumidos (total de eventos, hectáreas acumuladas, incendios activos) y permite exportar resultados en formato CSV y GeoJSON.

**Fuentes de datos**: NASA FIRMS (ingesta previa), PostgreSQL.
**Endpoints**: `GET /api/v1/fires`, `GET /api/v1/fires/stats`, `GET /api/v1/fires/export`
**Servicios**: `fire_service.py`, `export_service.py`

---

## UC-F04: Calidad del dato

**Estado**: Implementado

Sistema de scoring que evalúa la confiabilidad de cada evento de incendio. El score se calcula ponderando cuatro dimensiones: cantidad y confianza de detecciones satelitales (40%), disponibilidad de imágenes Sentinel-2 (20%), correlación con datos climáticos (20%) y confirmación por fuentes independientes (20%). El resultado se clasifica en alta, media o baja confiabilidad.

**Fuentes de datos**: NASA FIRMS (confianza de detección), GEE (disponibilidad de imágenes), Open-Meteo (datos climáticos).
**Endpoints**: `GET /api/v1/quality/fire-event/{id}`
**Servicios**: `quality_service.py`

---

## UC-F05: Recurrencia y tendencias

**Estado**: Implementado

Análisis espacial de recurrencia de incendios utilizando indexación H3 (resolución 8). Cada celda hexagonal acumula estadísticas históricas: total de incendios, frecuencia en los últimos 5 años, FRP máximo registrado, hectáreas totales y score de recurrencia normalizado (0-1). Los datos se sirven desde una materialized view (`h3_recurrence_stats`) que se clasifica en recurrencia alta (>3 eventos en 5 años), media (1-3) o baja (<1). Incluye forecasting de tendencias.

**Fuentes de datos**: PostgreSQL + PostGIS (datos históricos agregados).
**Endpoints**: `GET /api/v1/analysis/recurrence`
**Servicios**: `recurrence_service.py`, `trends_service.py`

---

## UC-F06: Verificación de terreno

**Estado**: Implementado

Herramienta que permite a cualquier usuario consultar si una zona geográfica fue afectada por incendios forestales y si existen restricciones de uso del suelo según la Ley 26.815. El usuario ingresa coordenadas (manualmente o seleccionando un punto en el mapa), y el sistema busca episodios históricos en un radio configurable, calcula intersecciones con áreas protegidas, y presenta una línea de tiempo con evidencia visual (thumbnails satelitales).

El resultado incluye: episodios encontrados con su estado (activo, monitoreo, extinto), indicadores de recuperación de vegetación, galería de evidencia satelital, y — cuando aplica — el período de restricción de uso del suelo calculado según la ley.

**Fuentes de datos**: NASA FIRMS (episodios), GEE/Sentinel-2 (imágenes de evidencia), áreas protegidas (IGN/APN).
**Endpoints**: `POST /api/v1/audit/land-use`, `GET /api/routes/audit/search`
**Servicios**: `audit_service.py`, `imagery_service.py`, `episode_service.py`

---

## UC-F08: Carrusel satelital

**Estado**: Implementado

Procesamiento diario automatizado que genera thumbnails satelitales para todos los episodios activos. El sistema selecciona la mejor imagen Sentinel-2 disponible aplicando progresión de umbrales de nubosidad (10% → 20% → 30% → 50%), genera múltiples visualizaciones por imagen (RGB, SWIR, NBR), aplica watermark con metadata (fecha, coordenadas, fuente) y almacena los resultados en Google Cloud Storage.

Las imágenes resultantes se presentan como carrusel en las tarjetas de incendios del feed principal.

**Fuentes de datos**: GEE/Sentinel-2 (imágenes multibanda).
**Endpoints**: `GET /api/routes/imagery/{episode_id}`
**Servicios**: `imagery_service.py`, `gee_service.py`, `gcs_service.py`
**Workers**: `carousel_task.py` (queue: analysis, batch diario vía Celery Beat)

---

## UC-F09: Reportes de cierre

**Estado**: Implementado

Generación de reportes de cierre para episodios finalizados. Incluye comparativa visual pre/post incendio, cálculo de severidad mediante dNBR (differenced Normalized Burn Ratio), estadísticas del episodio (duración, área estimada, detecciones, FRP máximo) y evaluación de señales de recuperación basada en NDVI.

**Fuentes de datos**: GEE/Sentinel-2 (imágenes pre/post), NASA FIRMS (datos del episodio).
**Endpoints**: `POST /api/routes/reports/closure/{episode_id}`
**Servicios**: `closure_report_service.py`, `gee_service.py`, `pdf_service.py`
**Workers**: `closure_report_task.py` (queue: analysis)

---

## UC-F11: Reportes técnicos verificables

**Estado**: Implementado

Generación de reportes PDF con cadena de custodia digital. Cada reporte incluye: datos del episodio, imágenes satelitales con metadata de adquisición, análisis de vegetación, timeline de detecciones, y un hash SHA-256 del contenido que permite verificación independiente. Se genera un código QR con el hash para verificación rápida.

Los reportes están diseñados para ser reproducibles: la metadata incluye los parámetros exactos de GEE (colección, fechas, bandas, filtros) para que cualquier persona con acceso a Earth Engine pueda regenerar las mismas imágenes.

**Fuentes de datos**: NASA FIRMS (detecciones), GEE/Sentinel-2 (imágenes), PostgreSQL (episodios, áreas protegidas).
**Endpoints**: `POST /api/v1/reports/judicial`
**Servicios**: `ers_service.py`, `pdf_service.py`, `gee_service.py`, `gcs_service.py`
**Workers**: Procesamiento asíncrono vía Celery (queue: analysis)

---

## UC-F13: Episodios macro

**Estado**: Implementado

Sistema de agrupación que convierte detecciones individuales de focos de calor en episodios de incendio coherentes. Utiliza clustering espacio-temporal (ST-DBSCAN) con parámetros versionados (distancia espacial, ventana temporal) para agrupar detecciones cercanas en espacio y tiempo. Cada episodio mantiene: fecha de inicio/fin, centroide, bounding box, área estimada, conteo de detecciones, FRP máximo y estado (activo, monitoreo, extinto, cerrado).

El versionado de parámetros de clustering permite reproducibilidad: cada versión registra epsilon espacial, ventana temporal y tamaño mínimo de cluster.

**Fuentes de datos**: NASA FIRMS (detecciones individuales).
**Endpoints**: `GET /api/routes/episodes`, `GET /api/routes/episodes/{id}`
**Servicios**: `detection_clustering_service.py`, `episode_service.py`
**Workers**: `clustering.py` (queue: clustering, diario vía Celery Beat), `episode_merge_task.py`

---

## Casos de uso planificados

| UC | Nombre | Descripción |
|----|--------|-------------|
| UC-F07 | Registro de visitantes | Registro offline para refugios con sincronización cuando hay conectividad |
| UC-F10 | Certificación monetizada | Emisión de certificados de uso del suelo con sistema de créditos |
| UC-F12 | VAE para cambio de uso del suelo | Detección automatizada de cambios post-incendio mediante Variational Autoencoder |
