# Pipeline inventory (UC-F08R)
Fecha: 2026-02-05
Estado: inventario técnico inicial basado en código local (sin verificación en Supabase).

**Celery Beat**
| Tarea (queue) | Schedule (UTC) | Código | Estado |
| --- | --- | --- | --- |
| download_firms_daily (ingestion) | 00:00 | workers/tasks/ingestion.py → scripts/load_firms_incremental.py | Activo (pipeline real FIRMS) |
| cluster_detections (clustering) | 01:00 | workers/tasks/clustering.py -> app/services/detection_clustering_service.py | Activo (ST-DBSCAN) |
| cluster_fire_episodes (clustering) | 02:00 | workers/tasks/clustering_task.py -> app/services/clustering_service.py | Activo (agrega/mergea episodios) |
| generate_carousel (analysis) | 03:00 | workers/tasks/carousel_task.py -> app/services/imagery_service.py | Activo (carrusel por eventos) |

**Scripts / cron**
| Script | Trigger sugerido | Rol | Notas |
| --- | --- | --- | --- |
| scripts/load_firms_incremental.py | Cron diario 06:00 (ejemplo en script) | Ingesta FIRMS NRT | Filtra Argentina + confianza >= 50, dedup por hash, inserta en fire_detections, dispara clustering + área + cruce legal |
| scripts/load_firms_history.py | Manual/batch | Ingesta histórica FIRMS | Filtra confianza >= 80, calcula detected_at, inserta via pandas to_sql, sin dedup |
| scripts/cluster_fire_events_parallel.py | Manual | Clustering detecciones->eventos (legacy) | DBSCAN Haversine sobre acquisition_date, usa is_processed=false, crea fire_events y asigna fire_event_id |
| scripts/aggregate_fire_episodes.py | Manual/batch | Agrega episodios desde eventos | Lógica propia, no usa clustering_versions |
| scripts/process_satellite_slides.py | Cron diario (implícito) | Carrusel (episodios o eventos) | Por defecto usa episodios, actualiza slides_data, no escribe satellite_images |

**Deduplicación actual**
- Ingesta incremental: usa `detection_hash` (sha256) si existe la columna; si no, cae a hash legacy (MD5) de lat/lon (5 decimales) + acquisition_date + acquisition_time + satellite. Sin constraint única aún.
- Ingesta histórica: no dedup (pandas to_sql append).

**Campos y tablas clave**
- Ingesta -> fire_detections: satellite, instrument, latitude, longitude, acquisition_date/time, location, confidence_normalized, fire_radiative_power, is_processed=false, detected_at (incremental e histórica).
- Clustering detecciones->eventos -> fire_events: centroid, start_date/end_date (derivados de acquisition_date), métricas FRP/confianza, fire_detections.fire_event_id, fire_detections.is_processed.
- Agregación episodios -> fire_episodes + fire_episode_events + episode_mergers (en merges).
- Carrusel -> fire_events.slides_data + satellite_images (ImageryService) o fire_episodes.slides_data (process_satellite_slides.py).

**Desalineaciones vs UC-F08R (a resolver en tareas técnicas)**
- fire_detections.h3_index no existe en el esquema; la ingesta lo calcula solo si la columna existe.
- fire_events.clustering_version_id no existe ni se setea.
- fire_episodes.end_date es NOT NULL y no existe last_seen_at.
- Carrusel productivo (Celery) opera sobre fire_events, no sobre fire_episodes.
- process_satellite_slides.py no persiste satellite_images ni usa formato RGB/SWIR/NBR canónico.
- system_parameters usados en ImageryService no coinciden con los parámetros solicitados en UC-F08R (ej. cloud_coverage_thresholds vs max_cloud_coverage).

