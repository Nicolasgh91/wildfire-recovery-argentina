"""Parcha la tabla de workers en flujo_ingesta_procesamiento.md."""
import pathlib

doc = pathlib.Path("docs/Carrusel fix/flujo_ingesta_procesamiento.md")
content = doc.read_text(encoding="utf-8")

# Marcadores que delimitan la tabla (son únicos en el archivo)
START = "| Worker | Archivo | Cola | Schedule | Función |\n|--------|---------|------|----------|---------|"
END_MARKER = "\n\n### 5.2 Servicios"

start_idx = content.find(START)
end_idx = content.find(END_MARKER, start_idx)
if start_idx == -1 or end_idx == -1:
    raise ValueError(f"Marcadores no encontrados. start={start_idx}, end={end_idx}")

new_table = (
    "| Worker | Archivo | Cola | Schedule | Función |\n"
    "|--------|---------|------|----------|----------|\n"
    "| Ingestion | `workers/tasks/ingestion.py` | `ingestion` | 00:00 UTC | Descarga CSV de NASA FIRMS, parsea, deduplica, inserta en `fire_detections` |\n"
    "| Clustering | `workers/tasks/clustering.py` | `clustering` | 01:00 UTC | Ejecuta ST-DBSCAN sobre detecciones pendientes, crea `fire_events`, actualiza `fire_detections` |\n"
    "| Event status | `workers/tasks/event_status_task.py` | `clustering` | 01:30 UTC | Persiste transiciones de estado `fire_events`: `active → monitoring` (7d) y `monitoring → extinct` (14d + check espacial 2km) |\n"
    "| Geo-enrichment | `workers/tasks/geo_enrichment.py` | `analysis` | 01:45 UTC | Enriquece `fire_events` con provincia/departamento y cruza con áreas protegidas |\n"
    "| Episode aggregation | `workers/tasks/clustering_task.py` | `clustering` | 02:00 UTC | Agrupa eventos en `fire_episodes`, mantiene `fire_episode_events`, ejecuta fusiones, recalcula `gee_candidate`/`gee_priority` y `extinct_at` |\n"
    "| Carousel (GEE) | `workers/tasks/carousel_task.py` | `analysis` | 03:00 UTC | Genera 3 thumbnails por episodio (RGB/SWIR/NBR) vía GEE para `active`, `monitoring` y `extinct` recientes (≤30d) |\n"
    "| Cleanup | `workers/tasks/cleanup_assets_task.py` | `analysis` | 04:00 UTC | Limpieza de assets HD y PDFs expirados en storage |\n"
    "| Episode closer | `workers/tasks/episode_closer_task.py` | `analysis` | 05:00 UTC | Transiciona episodios `extinct` a `closed` cuando `extinct_at + 30d < NOW()` |\n"
    "| Closure reports | `workers/tasks/closure_report_task.py` | `analysis` | 08:00 UTC | Genera PDFs de cierre para episodios con dNBR |\n"
    "| Clustering manual | `workers/tasks/clustering_task.py` | `clustering` | Manual | Trigger manual de clustering para un rango de fechas específico |\n"
    "| Recovery (VAE) | `workers/tasks/recovery.py` | `vae` | Manual/trigger | Análisis de recuperación de vegetación (NDVI) post-fuego |\n"
    "| Destruction (VAE) | `workers/tasks/destruction.py` | `vae` | Manual/trigger | Detección de cambios de uso del suelo en áreas quemadas |\n"
    "| Episode merge | `workers/tasks/episode_merge_task.py` | `default` | Manual/trigger | Fusión manual de episodios relacionados |"
)

new_content = content[:start_idx] + new_table + content[end_idx:]
doc.write_text(new_content, encoding="utf-8")
print("OK — tabla de workers actualizada")
