---
name: Analisis flujo thumbnails
overview: Correccion del flujo de thumbnails del carrusel alineado con la revision arquitectural. 10 tareas tecnicas con modelo de doble condicion para extinct, episode_id en satellite_images, y alineacion API/worker.
todos:
  - id: t01
    content: "DDL: indice parcial en fire_episodes.extinct_at (columna ya existe)"
    status: completed
  - id: t02
    content: "DDL: agregar episode_id FK nullable en satellite_images + backfill + indice"
    status: completed
  - id: t03
    content: Refactorizar _resolve_episode_status con modelo doble condicion (ventana temporal + todos eventos extinct)
    status: completed
  - id: t04
    content: Setear extinct_at automaticamente en update_episode_metrics (transicion a extinct)
    status: completed
  - id: t05
    content: Ampliar _fetch_priority_episodes para incluir extinct recientes (<30d)
    status: completed
  - id: t06
    content: Migrar cache key de fire_event_id a episode_id en gee_scene_cache.py e imagery_service.py
    status: completed
  - id: t07
    content: Limpieza de assets huerfanos en storage tras rollback parcial en _process_episode
    status: completed
  - id: t08
    content: Alinear endpoint API /fire-episodes?mode=active con politica de visibilidad del carousel
    status: completed
  - id: t09
    content: "Sincronizar system_parameters: carousel_extinct_grace_days=30"
    status: completed
  - id: t10
    content: Actualizar documentacion workers en flujo_ingesta_procesamiento.md
    status: completed
  - id: t11
    content: "Tests: pytest para _resolve_episode_status + extinct_at + carousel fetch + cache + SQL validacion"
    status: completed
isProject: false
---

# Correccion del flujo de thumbnails del carrusel

Fuente de verdad: revision arquitectural del usuario (2026-02-25).

## Modelo canonico de estado de episodios (doble condicion para extinct)

- **Active**: al menos 1 evento `active`
- **Monitoring**: ningun evento `active` Y no se cumplen ambas condiciones de extinct
- **Extinct**: `now() - last_seen_at >= episode_temporal_window_hours` (720h) **Y** todos los eventos estan `extinct`
- **Closed**: `episode_closer_task` a los 30 dias de `extinct_at`

## Tareas (orden de ejecucion)

### Fase 1 — DDL y parametros (paralelizable)

- **T-01**: Indice parcial en `fire_episodes.extinct_at` (columna ya existe por EVT-007)
- **T-02**: `ALTER TABLE satellite_images ADD COLUMN episode_id UUID REFERENCES fire_episodes(id) ON DELETE SET NULL` + backfill + indice
- **T-09**: INSERT `carousel_extinct_grace_days = 30` en `system_parameters`

### Fase 2 — Logica core (secuencial)

- **T-03**: Refactorizar `_resolve_episode_status` en [`app/services/episode_service.py`](app/services/episode_service.py) (lineas 139-185)
- **T-04**: Auto-setear `extinct_at` en `update_episode_metrics` (lineas 529+)
- **T-07**: Cleanup de assets huerfanos en `_process_episode` de [`app/services/imagery_service.py`](app/services/imagery_service.py)

### Fase 3 — Carousel alignment (secuencial)

- **T-05**: Ampliar `_fetch_priority_episodes` en `imagery_service.py`
- **T-06**: Migrar cache key a `episode_id` en [`app/services/gee_scene_cache.py`](app/services/gee_scene_cache.py)
- **T-08**: Alinear endpoint en [`app/api/routes/episodes.py`](app/api/routes/episodes.py)

### Fase 4 — Docs y tests

- **T-10**: Actualizar [`docs/Carrusel fix/flujo_ingesta_procesamiento.md`](docs/Carrusel%20fix/flujo_ingesta_procesamiento.md)
- **T-11**: Tests pytest + validacion SQL

## Ruta critica

```
T-09 ──────────────────────────────────────────────────────┐
T-01 ──> T-03 ──> T-04 ──> T-05 ──> T-08                  ├──> T-11
T-02 ──> T-06                                              │
T-07 ──────────────────────────────────────────────────────┘
T-10 ──────────────────────────────────────────────────────┘
```
