# Deuda técnica y desvíos (SEO/GEO Fases 1-2)

**Actualizado:** 2026-03-10

Desvíos respecto al plan de referencia (v9 y plan de viabilidad) que se documentan para no perder contexto.

## Migraciones

- **No hay `Alembic env.py`** en uso: las migraciones son scripts con revision IDs manuales (001, 002, 003, …). Las nuevas SEO son 003–006 con `down_revision` encadenado.

## Configuración

- **`SITE_BASE_URL`** no existía en `app/core/config.py`: se añadió con default `https://forestguard.freedynamicdns.org`. Debe configurarse en producción al dominio canónico para evitar contenido duplicado.

## Código nuevo

- **`app/utils/ssg_routes.py`** no existía: se creó con constantes `PROVINCES`, `STRATEGIC_ZONES` (dict `zone_slug -> [province_slugs]`), `PAGE_SIZE`, `_paginated_routes` y `build_ssg_routes_payload`. No se usa tabla `strategic_zones` en DB.

## API

- **Router de episodios** está en `app/api/routes/episodes.py` (no en `app/api/v1/`). Los endpoints `by-slug/{slug}/seo-data` y `stats/counts` se añadieron ahí.
- **Router SEO** (`/sitemap.xml`) está en `app/api/v1/seo.py` y se monta con `prefix=""` para servir la ruta en la raíz de la API.

## Nginx

- Nginx hace **proxy al frontend (frontend:80)**, no sirve estáticos desde `/usr/share/nginx/html`. La regla de `/metodologia` hace proxy a `http://frontend:80/metodologia`. Si el frontend no expone aún esa ruta o un HTML estático, queda documentado aquí hasta tener la página.

## Modelo de datos

- **`fire_episodes.provinces`** es `ARRAY(String)` (nombres, ej. "Córdoba"). No existen columnas `province_slug`, `thumbnail_url`, `has_satellite_images` ni `duration_days`; se derivan en tiempo de ejecución en workers y API (slug desde nombre, thumbnail desde `slides_data`, etc.).

## Celery

- **Slugs (SEO-W-01):** schedule a las 03:00 ART para no solaparse con clustering (02:00 ART).
- **Sitemap (SEO-W-02):** schedule cada 5 h (`crontab(minute=0, hour='*/5')`).
