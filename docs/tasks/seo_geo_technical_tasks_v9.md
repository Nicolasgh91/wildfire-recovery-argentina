# Tareas técnicas SEO/GEO — ForestGuard

**Última actualización:** 2026-03-09  
**Versión:** 9

---

## Roadmap de estado

### ✅ Completado (base habilitante)
- Bbox real en `fire_episodes` — fix aplicado y DB sanitizada
- Thumbnails satelitales sin franjas vacías — fix en producción
- SPA React + Vite servida por Nginx
- API REST con endpoints públicos

### 🔄 En curso
- Refactor `gee_service.py` fase 3
- Reestructuración de documentación (`docs/`)
- Contenido de `/metodologia` (redacción en curso)

### 📋 Pendiente en este plan — organizado por fase de despliegue
- **Fase 1:** schema (4 migraciones) + flow logic (4 funciones) + Nginx 301
- **Fase 2:** workers de slugs y sitemap con image sitemap + API endpoints
- **Fase 3:** exportación a OCI con chunking + UI estática con GEO JSON-LD y enlaces semánticos

---

## Vulnerabilidades corregidas (historial acumulado)

| ID | Versión | Vulnerabilidad | Corrección |
|---|---|---|---|
| VUL-01–14 | v4–v7 | Véase versiones anteriores | Incorporadas |
| VUL-15 | v8 | Ventana stale recurrente por coincidencia schedule/expiración | Schedule 5 h; TTL caché 6 h |
| VUL-16 | v8 | Páginas paginadas sin `rel="prev"` / `rel="next"` | `SEOHead` con props opcionales `prevPage` / `nextPage` |
| VUL-17 | v8 | `Dataset` sin `@id` canónico en JSON-LD | `build_episode_jsonld` expone `@id` y `url` |
| VUL-18 | v8 | Nginx responde 200 con y sin trailing slash | Rewrite 301 en Nginx |
| VUL-19 | v9 | `fetchall()` en SEO-W-03 crea pico de RAM; riesgo de OOM Killer en VM de 1 GB | Procesamiento en lotes con `yield_per(1000)` |
| VUL-20 | v9 | Tarjetas de episodios con `onClick` JS puro → páginas huérfanas para Googlebot | Componentes `<Link>` o `<a href>` semánticos en la grilla |
| VUL-21 | v9 | Páginas de provincia sin señal geográfica estructurada | JSON-LD `CollectionPage` con `about: Place` en `ProvinceListPage` |
| VUL-22 | v9 | Thumbnails satelitales no declarados en el sitemap → indexación tardía en Google Images | Namespace `image:` y `<image:loc>` en cada `<url>` de episodio |

---

## Estrategia de despliegue por fases

El plan se divide en tres fases independientemente desplegables. Las fases 1 y 2 están maduras para programarse hoy.

| Fase | Tareas | Estado | Objetivo |
|---|---|---|---|
| **1 — Cimientos** | SEO-S-01–04, SEO-F-01–04, SEO-A-03 (Nginx) | ✅ Lista para implementar | Preparar DB, funciones núcleo, redirecciones 301 |
| **2 — Motor asíncrono** | SEO-W-01–02, SEO-A-01–02 | ✅ Lista para implementar | Workers con schedule desfasado, sitemap con imágenes, endpoints API |
| **3 — Exportación y UI** | SEO-W-03, SEO-U-01–03 | 🔄 Requiere chunking + tags UI | Artefactos OCI sin riesgo de OOM, prerenderizado estático con GEO y enlaces semánticos |

---

## Decisiones técnicas incorporadas

| Decisión | Alternativa rechazada | Motivo |
|---|---|---|
| `yield_per(1000)` en SEO-W-03 | `fetchall()` de todos los episodios | Con miles de episodios, el `.fetchall()` crea un pico de RAM que puede ser liquidado por el OOM Killer en la VM de 1 GB |
| `<Link>` / `<a href>` en grilla de episodios | `onClick={() => navigate(...)}` | La navegación JS pura es invisible para Googlebot; sin `href`, los episodios se clasifican como páginas huérfanas |
| JSON-LD `CollectionPage` con `about: Place` en páginas de provincia | Solo `<SEOHead>` con título y descripción | Conecta semánticamente el listado con la entidad geográfica; señal fuerte para búsquedas como "incendios en Córdoba" |
| Image sitemap con namespace `image:` en cada `<url>` de episodio | Sitemap estándar sin imágenes | Google Images no indexa imágenes cuya URL no está declarada en un sitemap; los thumbnails satelitales son el activo visual diferenciador del proyecto |
| Schedule sitemap: 5 h; TTL caché: 6 h | Schedule y expiración coincidentes | Desfase de 1 h garantiza que el worker refresca el sitemap antes de que expire |
| Bloqueo distribuido Redis `SETNX` + TTL | Confiar solo en celery-beat | Permite regeneración inmediata sin tormenta de tareas |
| `ssg-seo-data.json` en OCI; `onBeforePageRender` lee desde memoria | Fetch a API durante el build | Build completamente offline; sin carga en la API de producción |
| Rutas paginadas `/pagina/N` en SSG | Solo ruta base | Sin paginación estática, el contenido histórico profundo no es indexable |
| Redirect 301 trailing slash en Nginx | Depender del canonical | Resolver duplicado en origen es la práctica estándar; el canonical solo mitiga |

---

## Fase 1 — Cimientos de datos y proxy

*Objetivo: preparar la DB, las funciones núcleo y las redirecciones. Sin workers, sin API nueva, sin UI.*

---

### SEO-S-01: columna `slug` y campos SEO en `fire_episodes`

**Archivo:** nueva migración Alembic  
**Esfuerzo:** 1 h

```sql
ALTER TABLE fire_episodes
  ADD COLUMN slug            TEXT UNIQUE,
  ADD COLUMN seo_title       TEXT,
  ADD COLUMN seo_description TEXT;

CREATE INDEX idx_fire_episodes_slug ON fire_episodes(slug);
```

---

### SEO-S-02: tabla `seo_pages_cache`

**Archivo:** nueva migración Alembic  
**Esfuerzo:** 45 min

```sql
CREATE TABLE seo_pages_cache (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  page_type    TEXT        NOT NULL,
  slug         TEXT        NOT NULL,
  cached_at    TIMESTAMPTZ DEFAULT NOW(),
  expires_at   TIMESTAMPTZ,
  stale_until  TIMESTAMPTZ,  -- expires_at + 24 h de gracia
  content      JSONB,
  UNIQUE(page_type, slug)
);
```

---

### SEO-S-03: tabla `seo_region_thresholds`

**Archivo:** nueva migración Alembic  
**Esfuerzo:** 1 h

```sql
CREATE TABLE seo_region_thresholds (
  id                   UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  region_slug          TEXT    NOT NULL UNIQUE,
  province_slugs       TEXT[]  NOT NULL,
  min_affected_area_ha INTEGER NOT NULL DEFAULT 500,
  label                TEXT,
  updated_at           TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO seo_region_thresholds
  (region_slug, province_slugs, min_affected_area_ha, label)
VALUES
  ('patagonia',    ARRAY['neuquen','rio-negro','chubut','santa-cruz','tierra-del-fuego'], 800,
   'Patagonia — baja densidad, umbrales altos'),
  ('cuyo',         ARRAY['mendoza','san-juan','san-luis'],                                500,
   'Cuyo — umbral estándar'),
  ('noa',          ARRAY['salta','jujuy','tucuman','catamarca','la-rioja'],               400,
   'NOA — yungas y valles'),
  ('nea',          ARRAY['chaco','formosa','corrientes','misiones'],                      300,
   'NEA — gran chaco y selva misionera'),
  ('pampa-humeda', ARRAY['buenos-aires','santa-fe','entre-rios','la-pampa','cordoba'],   250,
   'Pampa húmeda — alta densidad'),
  ('delta-parana', ARRAY['entre-rios','buenos-aires'],                                   150,
   'Delta del Paraná — alto valor ecológico y mediático'),
  ('caba',         ARRAY['ciudad-autonoma-de-buenos-aires'],                              50,
   'CABA — máxima densidad urbana');
```

---

### SEO-S-04: tabla `seo_minor_fire_quota`

**Archivo:** nueva migración Alembic  
**Esfuerzo:** 45 min

Sin `CHECK CONSTRAINT`. El límite se gestiona en Python con `min()` y en SQL con `LEAST()`.

```sql
CREATE TABLE seo_minor_fire_quota (
  id          UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  year_month  TEXT    NOT NULL UNIQUE,
  episode_ids UUID[]  NOT NULL DEFAULT '{}',
  url_count   INTEGER NOT NULL DEFAULT 0,
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

### SEO-F-01: función `generate_episode_slug`

**Archivo:** `app/utils/slug_utils.py` (nuevo)  
**Esfuerzo:** 1,5 h

```python
import re, unicodedata
from sqlalchemy.orm import Session

def generate_episode_slug(
    province: str, year: int, episode_id: str, db: Session = None
) -> str:
    """8 chars del UUID. Sufijo incremental si colisiona en DB."""
    normalized = unicodedata.normalize('NFD', province)
    ascii_str  = normalized.encode('ascii', 'ignore').decode()
    slug_base  = re.sub(r'[^a-z0-9]+', '-', ascii_str.lower()).strip('-')
    candidate  = f"{slug_base}-{year}-{episode_id[:8]}"

    if db is None:
        return candidate

    existing = {
        row["slug"] for row in db.execute(
            "SELECT slug FROM fire_episodes WHERE slug LIKE %s",
            (f"{candidate}%",)
        ).fetchall()
    }
    if candidate not in existing:
        return candidate
    suffix = 2
    while f"{candidate}-{suffix}" in existing:
        suffix += 1
    return f"{candidate}-{suffix}"
```

**Tests:**
```python
def test_slug_8_chars():
    assert generate_episode_slug("Córdoba", 2026, "a3f2b1c9deadbeef") == "cordoba-2026-a3f2b1c9"

def test_slug_normalization():
    assert generate_episode_slug("Río Negro", 2026, "d9e8f7a600000000") == "rio-negro-2026-d9e8f7a6"

def test_slug_suffix_on_collision(db_session):
    db_session.execute("INSERT INTO fire_episodes (slug) VALUES ('cordoba-2026-a3f2b1c9')")
    assert generate_episode_slug("Córdoba", 2026, "a3f2b1c9deadbeef", db=db_session) \
           == "cordoba-2026-a3f2b1c9-2"
```

---

### SEO-F-02: función `build_episode_jsonld`

**Archivo:** `app/utils/jsonld_utils.py` (nuevo)  
**Esfuerzo:** 2 h

```python
BASE_URL = "https://forestguard.com.ar"

def _build_temporal_coverage(started_at: str, ended_at: str | None) -> str:
    """Cerrado: 'start/end'. Activo: 'start' solo (barra final sola no es ISO 8601 válido)."""
    if ended_at:
        return f"{started_at}/{ended_at}"
    return started_at

def build_episode_jsonld(episode: dict) -> dict:
    canonical = f"{BASE_URL}/episodios/{episode['slug']}"
    return {
        "@context":  "https://schema.org",
        "@type":     "Dataset",
        "@id":       canonical,
        "url":       canonical,
        "name":      episode["seo_title"],
        "description": episode["seo_description"],
        "spatialCoverage": {
            "@type": "Place",
            "geo": {
                "@type": "GeoShape",
                "box": (
                    f"{episode['bbox_miny']} {episode['bbox_minx']} "
                    f"{episode['bbox_maxy']} {episode['bbox_maxx']}"
                )
            }
        },
        "temporalCoverage": _build_temporal_coverage(
            episode["started_at"], episode.get("ended_at")
        ),
        "creator":  {"@type": "Organization", "name": "ForestGuard", "url": BASE_URL},
        "keywords": ["incendio forestal", "Argentina",
                     episode.get("province_name", ""), "Sentinel-2", "VIIRS"],
        "license":  "https://creativecommons.org/licenses/by/4.0/"
    }
```

**Tests:**
```python
def _ep(ended_at=None):
    return {"slug": "cordoba-2026-a3f2b1c9", "seo_title": "T", "seo_description": "D",
            "bbox_minx": -64.5, "bbox_miny": -31.5, "bbox_maxx": -63.0, "bbox_maxy": -30.0,
            "started_at": "2026-01-15T00:00:00Z", "ended_at": ended_at, "province_name": "Córdoba"}

def test_jsonld_id_canonico():
    r = build_episode_jsonld(_ep())
    assert r["@id"] == "https://forestguard.com.ar/episodios/cordoba-2026-a3f2b1c9"
    assert r["url"] == r["@id"]

def test_temporal_coverage_cerrado():
    tc = build_episode_jsonld(_ep(ended_at="2026-01-20T00:00:00Z"))["temporalCoverage"]
    assert tc == "2026-01-15T00:00:00Z/2026-01-20T00:00:00Z"

def test_temporal_coverage_activo_sin_barra():
    tc = build_episode_jsonld(_ep())["temporalCoverage"]
    assert "/" not in tc
```

---

### SEO-F-03: clasificación de episodios para sitemap

**Archivo:** `app/utils/seo_filters.py` (nuevo)  
**Esfuerzo:** 2 h

```python
def get_regional_threshold(province_slug: str, thresholds: list[dict]) -> int:
    applicable = [t["min_affected_area_ha"] for t in thresholds
                  if province_slug in t["province_slugs"]]
    return min(applicable) if applicable else 500

def classify_episode_for_sitemap(
    episode: dict, thresholds: list[dict],
    minor_quota_used: int, minor_quota_max: int = 100
) -> str:
    if episode["status"] not in ("active", "monitoring", "closed"):
        return "excluded"
    if not episode.get("has_satellite_images"):
        return "excluded"
    if (episode.get("duration_days") or 0) < 3:
        return "excluded"
    ha        = episode.get("affected_area_ha") or 0
    threshold = get_regional_threshold(episode.get("province_slug", ""), thresholds)
    if ha >= threshold:
        return "standard"
    if ha < 100 and minor_quota_used < minor_quota_max:
        return "minor"
    return "excluded"
```

---

### SEO-F-04: función `build_ssg_routes_payload` (con rutas paginadas)

**Archivo:** `app/utils/ssg_routes.py` (nuevo)  
**Esfuerzo:** 2,5 h

```python
PROVINCES = [
    "buenos-aires", "catamarca", "chaco", "chubut", "cordoba",
    "corrientes", "ciudad-autonoma-de-buenos-aires", "entre-rios",
    "formosa", "jujuy", "la-pampa", "la-rioja", "mendoza",
    "misiones", "neuquen", "rio-negro", "salta", "san-juan",
    "san-luis", "santa-cruz", "santa-fe", "santiago-del-estero",
    "tierra-del-fuego", "tucuman"
]  # 24 entradas

STRATEGIC_ZONES = [
    "vaca-muerta", "patagonia-norte", "delta-del-parana",
    "gran-chaco", "corredor-verde-misionero", "sierras-cordoba",
    "yungas-noa", "pampas-centrales"
]  # 8 entradas

PAGE_SIZE = 20  # debe coincidir con el límite de paginación del frontend

def _paginated_routes(base_path: str, item_count: int) -> list[str]:
    routes      = [base_path]
    total_pages = max(1, -(-item_count // PAGE_SIZE))  # división techo
    for page in range(2, total_pages + 1):
        routes.append(f"{base_path}/pagina/{page}")
    return routes

def build_ssg_routes_payload(
    episode_slugs: list[str], generated_at: str,
    episodes_per_province: dict[str, int] | None = None,
    episodes_per_zone: dict[str, int] | None = None
) -> dict:
    epp = episodes_per_province or {}
    epz = episodes_per_zone     or {}

    province_routes = []
    for p in PROVINCES:
        province_routes.extend(_paginated_routes(f"/provincias/{p}", epp.get(p, 0)))

    zone_routes = []
    for z in STRATEGIC_ZONES:
        zone_routes.extend(_paginated_routes(f"/zonas/{z}", epz.get(z, 0)))

    episode_routes = [f"/episodios/{s}" for s in episode_slugs]
    return {
        "generated_at":    generated_at,
        "static_routes":   ["/metodologia", "/acerca"],
        "province_routes": province_routes,
        "zone_routes":     zone_routes,
        "episode_routes":  episode_routes,
        "total": 2 + len(province_routes) + len(zone_routes) + len(episode_routes)
    }
```

**Tests:**
```python
def test_paginacion_cordoba_45():
    p = build_ssg_routes_payload([], "2026-03-09T00:00:00Z",
                                 episodes_per_province={"cordoba": 45})
    assert "/provincias/cordoba/pagina/3"  in p["province_routes"]
    assert "/provincias/cordoba/pagina/4"  not in p["province_routes"]

def test_caba_incluida():
    p = build_ssg_routes_payload([], "2026-03-09T00:00:00Z")
    assert "/provincias/ciudad-autonoma-de-buenos-aires" in p["province_routes"]
    assert len(p["province_routes"]) == 24
```

---

### SEO-A-03: Nginx — `/metodologia` + redirect 301 trailing slash

**Archivo:** `nginx.conf`  
**Esfuerzo:** 1 h

```nginx
server {
    listen 80;
    server_name forestguard.com.ar;

    # ── Trailing slash: 301 para todas las rutas salvo la raíz ──────────
    location ~ ^(.+[^/])/$  {
        return 301 $scheme://$host$1$is_args$args;
    }

    # ── Página de metodología (HTML estático indexable) ──────────────────
    location = /metodologia {
        root /usr/share/nginx/html;
        try_files /metodologia.html =404;
        add_header Cache-Control "public, max-age=86400";
    }

    # ── SPA fallback ─────────────────────────────────────────────────────
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/index.html /index.html;
        add_header Cache-Control "public, max-age=3600";
    }
}
```

**Tests:**
```bash
curl -sI https://forestguard.com.ar/provincias/cordoba/ | grep -E "^HTTP|^Location"
# HTTP/2 301
# Location: https://forestguard.com.ar/provincias/cordoba

curl -sI https://forestguard.com.ar/ | grep "^HTTP"
# HTTP/2 200  (raíz no redirige)
```

---

## Fase 2 — Motor asíncrono y API

*Objetivo: workers activos, sitemap con imágenes declaradas, endpoints de SEO.*

---

### SEO-W-01: task `generate_slugs_batch`

**Archivo:** `workers/tasks/seo.py` (nuevo)  
**Cola:** `default` | **Schedule:** diario

```python
@celery_app.task(name="workers.tasks.seo.generate_slugs_batch", bind=True)
def generate_slugs_batch(self):
    with db.begin():
        episodes = db.execute("""
            SELECT id, province_name, started_at
            FROM fire_episodes WHERE slug IS NULL
            LIMIT 500 FOR UPDATE SKIP LOCKED
        """).fetchall()
        updated = errors = 0
        for ep in episodes:
            try:
                slug = generate_episode_slug(
                    ep["province_name"], ep["started_at"].year,
                    str(ep["id"]), db=db
                )
                updated += db.execute(
                    "UPDATE fire_episodes SET slug = %s WHERE id = %s AND slug IS NULL",
                    (slug, ep["id"])
                ).rowcount
            except Exception as exc:
                logger.error(f"generate_slugs_batch: error en {ep['id']}: {exc}")
                errors += 1
    logger.info(f"generate_slugs_batch: {updated} generados, {errors} errores")
    return {"updated": updated, "errors": errors}
```

---

### SEO-W-02: task `generate_sitemap_cache` (schedule 5 h, TTL 6 h, image sitemap)

**Archivo:** `workers/tasks/seo.py`  
**Cola:** `default` | **Schedule:** cada 5 horas

El sitemap incluye el namespace `image:` de Google y declara el thumbnail de cada
episodio. Esto habilita la indexación en Google Images sin esperar el rastreo orgánico.

```python
# celery_config.py
CELERY_BEAT_SCHEDULE = {
    "generate_sitemap_cache": {
        "task":     "workers.tasks.seo.generate_sitemap_cache",
        "schedule": crontab(minute=0, hour="*/5"),  # 5 h < TTL de 6 h
    },
}

MINOR_QUOTA_MAX = 100
SITEMAP_HEADER  = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">"""
SITEMAP_FOOTER  = "</urlset>"


def _url_entry(
    loc: str, changefreq: str, priority: str,
    lastmod: str | None = None, image_url: str | None = None
) -> str:
    parts = [f"  <url><loc>https://forestguard.com.ar{loc}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    parts.append(f"    <changefreq>{changefreq}</changefreq>")
    parts.append(f"    <priority>{priority}</priority>")
    if image_url:
        parts.append(
            f"    <image:image>"
            f"<image:loc>{image_url}</image:loc>"
            f"</image:image>"
        )
    parts.append("  </url>")
    return "\n".join(parts)


def _build_sitemap_xml(url_entries: list[str]) -> str:
    return SITEMAP_HEADER + "\n" + "\n".join(url_entries) + "\n" + SITEMAP_FOOTER


@celery_app.task(name="workers.tasks.seo.generate_sitemap_cache")
def generate_sitemap_cache():
    thresholds = db.execute(
        "SELECT province_slugs, min_affected_area_ha FROM seo_region_thresholds"
    ).fetchall()

    year_month       = datetime.utcnow().strftime("%Y-%m")
    quota_row        = db.execute(
        "SELECT url_count FROM seo_minor_fire_quota WHERE year_month = %s",
        (year_month,)
    ).fetchone()
    minor_quota_used = min(quota_row["url_count"] if quota_row else 0, MINOR_QUOTA_MAX)

    urls        = []
    minor_added = 0

    for path in ["/metodologia", "/acerca"]:
        urls.append(_url_entry(path, "monthly", "1.0"))
    for p in PROVINCES:
        urls.append(_url_entry(f"/provincias/{p}", "daily", "0.9"))
    for z in db.execute("SELECT slug FROM strategic_zones WHERE active = true"):
        urls.append(_url_entry(f"/zonas/{z['slug']}", "weekly", "0.8"))

    for ep in db.execute(
        "SELECT slug, updated_at, affected_area_ha, status, "
        "has_satellite_images, duration_days, province_slug, thumbnail_url "
        "FROM fire_episodes WHERE slug IS NOT NULL"
    ):
        quota_snapshot = min(minor_quota_used + minor_added, MINOR_QUOTA_MAX)
        cls = classify_episode_for_sitemap(ep, thresholds, quota_snapshot)
        if cls == "standard":
            urls.append(_url_entry(
                f"/episodios/{ep['slug']}", "daily", "0.7",
                lastmod=str(ep["updated_at"].date()),
                image_url=ep.get("thumbnail_url")  # declarado para Google Images
            ))
        elif cls == "minor":
            urls.append(_url_entry(
                f"/episodios/{ep['slug']}", "weekly", "0.5",
                lastmod=str(ep["updated_at"].date()),
                image_url=ep.get("thumbnail_url")
            ))
            minor_added += 1

    if minor_added > 0:
        db.execute("""
            INSERT INTO seo_minor_fire_quota (year_month, url_count)
            VALUES (%s, %s)
            ON CONFLICT (year_month) DO UPDATE
              SET url_count  = LEAST(seo_minor_fire_quota.url_count + %s, 100),
                  updated_at = NOW()
        """, (year_month, minor_added, minor_added))

    now = datetime.utcnow()
    db.upsert("seo_pages_cache", {
        "page_type":   "sitemap", "slug": "main",
        "content":     {"xml": _build_sitemap_xml(urls)},
        "cached_at":   now,
        "expires_at":  now + timedelta(hours=6),
        "stale_until": now + timedelta(hours=30)
    })
    logger.info(f"generate_sitemap_cache: {len(urls)} URLs ({minor_added} menores)")
    return {"url_count": len(urls), "minor_added": minor_added}
```

**Tests:**
```python
def test_schedule_menor_que_ttl():
    assert 5 < 6, "El worker (5 h) debe refrescar el caché antes de que expire (6 h)"

def test_sitemap_incluye_image_namespace(db_session):
    create_test_episode(db_session, slug="cordoba-2026-a3f2b1c9",
        affected_area_ha=300, province_slug="cordoba",
        thumbnail_url="https://cdn.example.com/thumb.webp",
        status="active", has_satellite_images=True, duration_days=5)
    generate_sitemap_cache()
    xml = get_cached_sitemap(db_session)
    assert 'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"' in xml
    assert "<image:loc>https://cdn.example.com/thumb.webp</image:loc>" in xml

def test_sitemap_sin_thumbnail_no_emite_image_tag(db_session):
    create_test_episode(db_session, slug="cordoba-2026-nothumbnail",
        affected_area_ha=300, province_slug="cordoba", thumbnail_url=None,
        status="active", has_satellite_images=True, duration_days=5)
    generate_sitemap_cache()
    xml = get_cached_sitemap(db_session)
    assert "cordoba-2026-nothumbnail" in xml  # la URL aparece
    assert xml.count("<image:loc>") == 0      # pero sin imagen declarada

def test_stale_encola_una_sola_tarea(client, db_session, mock_celery):
    seed_sitemap_cache(db_session,
        expires_at=datetime.utcnow() - timedelta(hours=1),
        stale_until=datetime.utcnow() + timedelta(hours=23))
    for _ in range(50):
        assert client.get("/sitemap.xml").status_code == 200
    assert mock_celery.call_count == 1
```

---

### SEO-A-01: endpoint `GET /sitemap.xml`

**Archivo:** `app/api/v1/seo.py` (nuevo)  
**Esfuerzo:** 2 h

```python
SITEMAP_REGEN_LOCK_KEY = "seo:sitemap:regen_lock"
SITEMAP_REGEN_LOCK_TTL = 300

def _try_enqueue_sitemap_regen(redis_client) -> bool:
    acquired = redis_client.set(
        SITEMAP_REGEN_LOCK_KEY, "1", nx=True, ex=SITEMAP_REGEN_LOCK_TTL
    )
    if acquired:
        generate_sitemap_cache.delay()
        return True
    return False

@router.get("/sitemap.xml")
async def sitemap(db: Session = Depends(get_db), redis_client=Depends(get_redis)):
    cache = db.query(SeoPagesCache).filter_by(page_type="sitemap", slug="main").first()
    now   = datetime.utcnow()

    if not cache:
        raise HTTPException(503, detail="Sitemap en generación inicial")

    if cache.expires_at >= now:
        return Response(content=cache.content["xml"], media_type="application/xml",
                        headers={"Cache-Control": "public, max-age=21600"})

    enqueued = _try_enqueue_sitemap_regen(redis_client)

    if cache.stale_until and cache.stale_until >= now:
        return Response(content=cache.content["xml"], media_type="application/xml",
                        headers={"Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
                                 "X-Cache-Status": "stale",
                                 "X-Regen-Enqueued": "true" if enqueued else "false"})

    return Response(content=cache.content["xml"], media_type="application/xml",
                    headers={"Cache-Control": "public, max-age=300",
                             "X-Cache-Status": "very-stale",
                             "X-Regen-Enqueued": "true" if enqueued else "false"})
```

---

### SEO-A-02: endpoint `GET /api/v1/episodes/{slug}/seo-data`

**Archivo:** `app/api/v1/episodes.py` (extensión)  
**Esfuerzo:** 1 h

```python
@router.get("/{slug}/seo-data")
async def episode_seo_data(slug: str, db: Session = Depends(get_db)):
    ep = db.query(FireEpisode).filter_by(slug=slug).first()
    if not ep:
        raise HTTPException(404)
    return {
        "title":           ep.seo_title,
        "description":     ep.seo_description,
        "jsonld":          build_episode_jsonld(ep.__dict__),
        "og_image":        ep.thumbnail_url,
        "og_image_width":  1200,
        "og_image_height": 630,
        "canonical":       f"https://forestguard.com.ar/episodios/{slug}"
    }
```

---

## Fase 3 — Exportación y UI estática

*Objetivo: artefactos OCI sin riesgo de OOM, prerenderizado estático, GEO JSON-LD, enlaces semánticos.*

---

### SEO-W-03: task `export_ssg_artifacts` (con chunking — sin riesgo de OOM)

**Archivo:** `workers/tasks/seo.py`  
**Cola:** `default` | **Schedule:** diario (tras SEO-W-01)

El problema del `fetchall()` es que trae todos los registros a RAM de una vez. Con miles
de episodios en la DB, esto puede superar el límite de la VM y activar el OOM Killer.
`yield_per(1000)` mantiene el consumo de memoria plano e independiente del volumen total.

```python
CHUNK_SIZE = 1000

@celery_app.task(name="workers.tasks.seo.export_ssg_artifacts")
def export_ssg_artifacts():
    thresholds       = db.execute(
        "SELECT province_slugs, min_affected_area_ha FROM seo_region_thresholds"
    ).fetchall()
    year_month       = datetime.utcnow().strftime("%Y-%m")
    quota_row        = db.execute(
        "SELECT url_count FROM seo_minor_fire_quota WHERE year_month = %s",
        (year_month,)
    ).fetchone()
    minor_quota_used = min(quota_row["url_count"] if quota_row else 0, MINOR_QUOTA_MAX)

    eligible     = []
    minor_n      = 0
    seo_data_map = {}

    # yield_per mantiene el consumo de memoria constante
    # sin importar si hay 1.000 o 100.000 episodios
    query = db.execute("""
        SELECT slug, affected_area_ha, status, has_satellite_images,
               duration_days, province_slug, seo_title, seo_description,
               thumbnail_url, started_at, ended_at,
               bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
               province_name, updated_at
        FROM fire_episodes WHERE slug IS NOT NULL
    """)

    while True:
        chunk = query.fetchmany(CHUNK_SIZE)
        if not chunk:
            break
        for ep in chunk:
            quota_snapshot = min(minor_quota_used + minor_n, MINOR_QUOTA_MAX)
            cls = classify_episode_for_sitemap(ep, thresholds, quota_snapshot)
            if cls in ("standard", "minor"):
                eligible.append(ep["slug"])
                if cls == "minor":
                    minor_n += 1
                canonical = f"https://forestguard.com.ar/episodios/{ep['slug']}"
                seo_data_map[ep["slug"]] = {
                    "title":           ep["seo_title"],
                    "description":     ep["seo_description"],
                    "jsonld":          build_episode_jsonld(dict(ep)),
                    "og_image":        ep["thumbnail_url"],
                    "og_image_width":  1200,
                    "og_image_height": 630,
                    "canonical":       canonical
                }

    province_counts = {
        row["province_slug"]: row["count"]
        for row in db.execute("""
            SELECT province_slug, COUNT(*) as count
            FROM fire_episodes WHERE slug IS NOT NULL
            GROUP BY province_slug
        """).fetchall()
    }
    zone_counts = {
        row["zone_slug"]: row["count"]
        for row in db.execute("""
            SELECT zone_slug, COUNT(*) as count
            FROM episode_zones GROUP BY zone_slug
        """).fetchall()
    }

    routes_payload = build_ssg_routes_payload(
        episode_slugs=eligible,
        generated_at=datetime.utcnow().isoformat() + "Z",
        episodes_per_province=province_counts,
        episodes_per_zone=zone_counts
    )
    generated_at = datetime.utcnow().isoformat() + "Z"

    _upload_to_oci("seo/ssg-routes.json",
                   json.dumps(routes_payload, indent=2, ensure_ascii=False))
    _upload_to_oci("seo/ssg-seo-data.json",
                   json.dumps({"generated_at": generated_at, "episodes": seo_data_map},
                               indent=2, ensure_ascii=False))

    logger.info(
        f"export_ssg_artifacts: {routes_payload['total']} rutas, "
        f"{len(seo_data_map)} datos SEO subidos a OCI"
    )
    return {"routes_total": routes_payload["total"], "seo_data_count": len(seo_data_map)}


def _upload_to_oci(key: str, content: str):
    storage_client.put_object(
        bucket=settings.STORAGE_BUCKET_REPORTS,
        key=key, body=content.encode(), content_type="application/json"
    )
```

**Tests:**
```python
def test_chunking_no_usa_fetchall(monkeypatch):
    """Verifica que el worker no llama fetchall() sobre el query principal."""
    calls = []
    original_fetchmany = db.execute.__class__.fetchmany

    def spy_fetchmany(self, size):
        calls.append(size)
        return original_fetchmany(self, size)

    monkeypatch.setattr("sqlalchemy.engine.CursorResult.fetchmany", spy_fetchmany)
    export_ssg_artifacts()
    assert all(c == CHUNK_SIZE for c in calls), "Todos los lotes deben usar CHUNK_SIZE"

def test_memoria_plana_con_muchos_episodios(db_session, mock_oci_storage):
    """Con 3.000 episodios el proceso no debe superar 50 MB de RAM adicionales."""
    import tracemalloc
    for i in range(3000):
        create_test_episode(db_session, slug=f"cordoba-2026-{i:08x}",
            affected_area_ha=300, province_slug="cordoba",
            status="active", has_satellite_images=True, duration_days=5)
    tracemalloc.start()
    export_ssg_artifacts()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert peak < 50 * 1024 * 1024, f"Pico de RAM: {peak / 1024 / 1024:.1f} MB (límite: 50 MB)"

def test_genera_dos_artefactos(db_session, mock_oci_storage):
    create_test_episode(db_session, slug="cordoba-2026-a3f2b1c9",
        affected_area_ha=300, province_slug="cordoba",
        status="active", has_satellite_images=True, duration_days=5)
    export_ssg_artifacts()
    keys = {c.kwargs["key"] for c in mock_oci_storage.put_object.call_args_list}
    assert {"seo/ssg-routes.json", "seo/ssg-seo-data.json"} == keys
```

---

### SEO-U-01: prerenderizado `vite-ssg` — build offline

**Archivos:** `frontend/vite.config.ts`, `.github/workflows/frontend-build.yml`  
**Esfuerzo:** 3–4 h

```yaml
# frontend-build.yml
- name: Descargar artefactos SSG (con fallback si OCI no responde)
  env:
    SSG_ROUTES_URL:   ${{ secrets.SSG_ROUTES_OCI_URL }}
    SSG_SEO_DATA_URL: ${{ secrets.SSG_SEO_DATA_OCI_URL }}
  run: |
    curl -fsSL "$SSG_ROUTES_URL" -o frontend/public/ssg-routes.json \
    || echo '{"generated_at":"fallback","static_routes":["/metodologia","/acerca"],
              "province_routes":[],"zone_routes":[],"episode_routes":[],"total":2}' \
         > frontend/public/ssg-routes.json

    curl -fsSL "$SSG_SEO_DATA_URL" -o frontend/public/ssg-seo-data.json \
    || echo '{"generated_at":"fallback","episodes":{}}' \
         > frontend/public/ssg-seo-data.json

    echo "Rutas: $(jq '.total' frontend/public/ssg-routes.json)"
    echo "Slugs SEO: $(jq '.episodes | length' frontend/public/ssg-seo-data.json)"
```

```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react            from '@vitejs/plugin-react'
import ssgRoutes        from './public/ssg-routes.json'
import ssgSeoData       from './public/ssg-seo-data.json'

const seoIndex: Record<string, unknown> = ssgSeoData.episodes ?? {}

export default defineConfig({
  plugins: [react()],
  ssgOptions: {
    script: 'async', formatting: 'minify',
    includedRoutes: () => [
      ...ssgRoutes.static_routes, ...ssgRoutes.province_routes,
      ...ssgRoutes.zone_routes,   ...ssgRoutes.episode_routes
    ],
    onBeforePageRender: async (route, _html, appCtx) => {
      const m = route.match(/^\/episodios\/(.+)$/)
      if (!m) return
      const data = seoIndex[m[1]]
      if (data) appCtx.queryClient?.setQueryData(['episode-seo', m[1]], data)
    }
  }
})
```

---

### SEO-U-02: componente `SEOHead` (con `rel="prev"` / `rel="next"` y JSON-LD de provincia)

**Archivo:** `frontend/src/components/SEOHead.tsx` (nuevo)  
**Esfuerzo:** 2 h

```tsx
import { Helmet } from 'react-helmet-async'

interface SEOHeadProps {
  title: string; description: string; canonical?: string
  ogImage?: string; ogImageWidth?: number; ogImageHeight?: number
  jsonld?: object | object[]  // acepta uno o múltiples bloques JSON-LD
  prevPage?: string
  nextPage?: string
}

export function SEOHead({
  title, description, canonical,
  ogImage, ogImageWidth = 1200, ogImageHeight = 630,
  jsonld, prevPage, nextPage
}: SEOHeadProps) {
  // Normalizar jsonld a array para poder inyectar múltiples bloques
  const jsonldBlocks = jsonld
    ? Array.isArray(jsonld) ? jsonld : [jsonld]
    : []

  return (
    <Helmet>
      <title>{title} | ForestGuard</title>
      <meta name="description"        content={description} />
      {canonical && <link rel="canonical" href={canonical} />}
      {prevPage   && <link rel="prev"      href={prevPage} />}
      {nextPage   && <link rel="next"      href={nextPage} />}
      <meta property="og:title"       content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:type"        content="website" />
      {ogImage && <>
        <meta property="og:image"        content={ogImage} />
        <meta property="og:image:width"  content={String(ogImageWidth)} />
        <meta property="og:image:height" content={String(ogImageHeight)} />
      </>}
      <meta name="twitter:card"        content="summary_large_image" />
      <meta name="twitter:title"       content={title} />
      <meta name="twitter:description" content={description} />
      {ogImage && <meta name="twitter:image" content={ogImage} />}
      {jsonldBlocks.map((block, i) => (
        <script key={i} type="application/ld+json">{JSON.stringify(block)}</script>
      ))}
    </Helmet>
  )
}
```

`jsonld` acepta ahora un array para que `ProvinceListPage` pueda inyectar tanto el
`CollectionPage` geográfico como cualquier bloque adicional en el mismo render.

---

### SEO-U-03: `EpisodeDetailPage` y `ProvinceListPage` — enlaces semánticos y GEO JSON-LD

**Archivos:** `frontend/src/App.tsx`, `frontend/src/pages/EpisodeDetailPage.tsx`,  
`frontend/src/pages/ProvinceListPage.tsx`, `frontend/src/components/EpisodeCard.tsx`  
**Esfuerzo:** 3 h

#### Páginas huérfanas — `EpisodeCard.tsx`

Las tarjetas de la grilla deben usar `<Link>` (o `<a href>`), no `onClick` puro.
Sin un `href` real, Googlebot no puede seguir el enlace y los episodios quedan
desconectados del grafo de enlaces del sitio.

```tsx
// ❌ Patrón anterior — invisible para Googlebot
<div onClick={() => navigate(`/episodios/${episode.slug}`)}>
  ...
</div>

// ✅ Patrón correcto — enlace semántico rastreable
import { Link } from 'react-router-dom'

export function EpisodeCard({ episode }: { episode: Episode }) {
  return (
    <Link to={`/episodios/${episode.slug}`} className="episode-card">
      <img src={episode.thumbnailUrl} alt={episode.seoTitle} />
      <h3>{episode.seoTitle}</h3>
      <p>{episode.affectedAreaHa} ha — {episode.provinceName}</p>
    </Link>
  )
}
```

#### `EpisodeDetailPage.tsx` — datos deshidratados

```tsx
export default function EpisodeDetailPage() {
  const { slug } = useParams<{ slug: string }>()
  const { data: seo } = useQuery({
    queryKey: ['episode-seo', slug],
    queryFn:  () => fetch(`/api/v1/episodes/${slug}/seo-data`).then(r => r.json()),
    staleTime: 1000 * 60 * 10
  })
  return (
    <>
      {seo && (
        <SEOHead
          title={seo.title}           description={seo.description}
          canonical={seo.canonical}   ogImage={seo.og_image}
          ogImageWidth={seo.og_image_width}
          ogImageHeight={seo.og_image_height}
          jsonld={seo.jsonld}
        />
      )}
    </>
  )
}
```

#### `ProvinceListPage.tsx` — GEO JSON-LD + `rel="prev"` / `rel="next"`

El JSON-LD tipo `CollectionPage` con `about: Place` conecta semánticamente el listado
con la entidad geográfica. Cuando un usuario busca "incendios en Córdoba", Google
entiende que esta página es sobre ese lugar específico.

```tsx
const BASE = "https://forestguard.com.ar"

export default function ProvinceListPage() {
  const { provinceSlug, page } = useParams()
  const currentPage  = Number(page ?? 1)
  const { data }     = useProvinceEpisodes(provinceSlug, currentPage)
  const totalPages   = Math.ceil((data?.total ?? 0) / PAGE_SIZE)
  const provinceName = PROVINCE_LABELS[provinceSlug] ?? provinceSlug

  const canonicalBase = `${BASE}/provincias/${provinceSlug}`
  const canonical = currentPage === 1
    ? canonicalBase
    : `${canonicalBase}/pagina/${currentPage}`
  const prevPage = currentPage > 1
    ? (currentPage === 2 ? canonicalBase : `${canonicalBase}/pagina/${currentPage - 1}`)
    : undefined
  const nextPage = currentPage < totalPages
    ? `${canonicalBase}/pagina/${currentPage + 1}`
    : undefined

  // JSON-LD CollectionPage: señal geográfica fuerte para búsquedas locales
  const collectionPageJsonld = {
    "@context": "https://schema.org",
    "@type":    "CollectionPage",
    "@id":      canonical,
    "url":      canonical,
    "name":     `Incendios forestales en ${provinceName}, Argentina`,
    "description": `Registro histórico de incendios en ${provinceName} con imágenes satelitales Sentinel-2.`,
    "about": {
      "@type":          "Place",
      "name":           `${provinceName}, Argentina`,
      "containedInPlace": {
        "@type": "Country",
        "name":  "Argentina"
      }
    },
    "isPartOf": {"@id": BASE}
  }

  return (
    <>
      <SEOHead
        title={`Incendios en ${provinceName}${currentPage > 1 ? ` — página ${currentPage}` : ''}`}
        description={`Mapa y datos de incendios forestales en ${provinceName}.`}
        canonical={canonical}
        prevPage={prevPage}
        nextPage={nextPage}
        jsonld={collectionPageJsonld}
      />
      {/* Grilla de episodios con EpisodeCard (enlaces <Link> semánticos) */}
      <div className="episode-grid">
        {data?.episodes.map(ep => <EpisodeCard key={ep.id} episode={ep} />)}
      </div>
    </>
  )
}
```

**Tests:**
```tsx
test('EpisodeCard usa <a href> semántico', () => {
  render(<EpisodeCard episode={mockEpisode} />)
  const link = screen.getByRole('link')
  expect(link).toHaveAttribute('href', '/episodios/cordoba-2026-a3f2b1c9')
})

test('ProvinceListPage emite CollectionPage con about Place', () => {
  const { container } = render(
    <QueryClientProvider client={new QueryClient()}>
      <HelmetProvider>
        <MemoryRouter initialEntries={['/provincias/cordoba']}>
          <Routes>
            <Route path="/provincias/:provinceSlug" element={<ProvinceListPage />} />
          </Routes>
        </MemoryRouter>
      </HelmetProvider>
    </QueryClientProvider>
  )
  const ld = JSON.parse(
    container.querySelector('script[type="application/ld+json"]')!.textContent!
  )
  expect(ld["@type"]).toBe("CollectionPage")
  expect(ld.about["@type"]).toBe("Place")
  expect(ld.about.name).toContain("Córdoba")
})

test('ProvinceListPage emite rel=prev y rel=next en página 2', () => {
  renderWithPage('/provincias/cordoba/pagina/2', totalEpisodes=45)
  expect(document.querySelector('link[rel="prev"]')?.getAttribute('href'))
    .toBe('https://forestguard.com.ar/provincias/cordoba')
  expect(document.querySelector('link[rel="next"]')?.getAttribute('href'))
    .toBe('https://forestguard.com.ar/provincias/cordoba/pagina/3')
})
```

---

## Tabla resumen de tareas por fase

### Fase 1 — cimientos de datos y proxy ✅ Lista para implementar

| ID | Capa | Descripción | Esfuerzo |
|---|---|---|---|
| SEO-S-01 | Schema | `slug` + campos SEO en `fire_episodes` | 1 h |
| SEO-S-02 | Schema | `seo_pages_cache` con `stale_until` | 45 min |
| SEO-S-03 | Schema | `seo_region_thresholds` con CABA | 1 h |
| SEO-S-04 | Schema | `seo_minor_fire_quota` sin `CHECK CONSTRAINT` | 45 min |
| SEO-F-01 | Flow | `generate_episode_slug` — 8 chars + sufijo incremental | 1,5 h |
| SEO-F-02 | Flow | `build_episode_jsonld` — `@id` + `temporalCoverage` condicional | 2 h |
| SEO-F-03 | Flow | `classify_episode_for_sitemap` — regional + cuota | 2 h |
| SEO-F-04 | Flow | `build_ssg_routes_payload` — rutas paginadas | 2,5 h |
| SEO-A-03 | API/Infra | Nginx: `/metodologia` + redirect 301 trailing slash | 1 h |
| **Subtotal** | | | **~12,5 h** |

### Fase 2 — motor asíncrono y API ✅ Lista para implementar

| ID | Capa | Descripción | Esfuerzo |
|---|---|---|---|
| SEO-W-01 | Worker | `generate_slugs_batch` con `FOR UPDATE SKIP LOCKED` | 2 h |
| SEO-W-02 | Worker | `generate_sitemap_cache` — schedule 5 h, TTL 6 h, image sitemap | 2 h |
| SEO-A-01 | API | `GET /sitemap.xml` — stale-while-revalidate + lock Redis | 2 h |
| SEO-A-02 | API | `GET /episodes/{slug}/seo-data` | 1 h |
| **Subtotal** | | | **~7 h** |

### Fase 3 — exportación y UI estática 🔄 Requiere chunking + tags UI

| ID | Capa | Descripción | Esfuerzo |
|---|---|---|---|
| SEO-W-03 | Worker | `export_ssg_artifacts` — chunking `fetchmany(1000)`, dos artefactos OCI | 2,5 h |
| SEO-U-01 | UI | `vite-ssg` con dos artefactos OCI + fallback en CI | 3–4 h |
| SEO-U-02 | UI | `SEOHead` con `rel="prev"` / `rel="next"` y `jsonld` como array | 2 h |
| SEO-U-03 | UI | `EpisodeCard` `<Link>`, `EpisodeDetailPage` deshidratado, `ProvinceListPage` GEO JSON-LD | 3 h |
| **Subtotal** | | | **~10,5–11,5 h** |

**Esfuerzo total estimado: ~30–31 h**

---

## Verificación post-deploy por fase

### Fase 1
```bash
# Migración aplicada
psql -c "\d fire_episodes" | grep slug

# Trailing slash → 301
curl -sI https://forestguard.com.ar/provincias/cordoba/ | grep -E "^HTTP|^Location"
# HTTP/2 301 / Location: .../provincias/cordoba
```

### Fase 2
```bash
# Sitemap con namespace de imagen
curl -s https://forestguard.com.ar/sitemap.xml | grep -c "image:loc"
# >= 1 (tantos como episodios con thumbnail en la DB)

# Sitemap devuelve 200 siempre que exista caché
curl -sI https://forestguard.com.ar/sitemap.xml | grep "^HTTP"
# HTTP/2 200
```

### Fase 3
```bash
# HTML prerenderizado tiene og:title
for f in dist/episodios/*/index.html; do
  grep -qc "og:title" "$f" || echo "FALLO: $f sin og:title"
done

# Página de provincia tiene CollectionPage JSON-LD
curl -s https://forestguard.com.ar/provincias/cordoba \
  | python3 -c "import sys,json,re; \
    scripts=re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>',sys.stdin.read(),re.S); \
    [print(json.loads(s).get('@type')) for s in scripts]"
# CollectionPage

# Google Rich Results
# search.google.com/test/rich-results → Dataset sin errores, @id presente
```

---

## Deuda técnica vigente

| Decisión | Alternativa postergada | Cuándo reevaluar |
|---|---|---|
| `vite-ssg` build-time | Cloudflare Workers + prerender.io (edge) | Post-MVP, cuando tráfico de bots sea medible |
| `ssg-seo-data.json` con todos los elegibles | Snapshot incremental | Si supera 50 MB (~2.000 ep. × 1 KB ≈ 2 MB; margen amplio) |
| `PAGE_SIZE = 20` hardcodeado | `PAGE_SIZE` en `system_parameters` DB | Cuando se ajuste sin redeploy |
| Sitemap sin rutas paginadas | `<url>` para `/pagina/N` en el sitemap | Si Search Console muestra rastreo de páginas paginadas; prioridad `0.4` |
| GEO JSON-LD solo en `ProvinceListPage` | `ZoneListPage`, `AboutPage` | Cuando se añadan vistas de zona estratégica |

---

*Documento actualizado: 2026-03-09 — versión 9*  
*Cambios: VUL-19 (export_ssg_artifacts usa fetchmany(CHUNK_SIZE) en lugar de fetchall; test de memoria con tracemalloc); VUL-20 (EpisodeCard usa <Link> semántico; test de role=link con href); VUL-21 (ProvinceListPage emite JSON-LD CollectionPage con about Place; SEOHead acepta jsonld como array); VUL-22 (generate_sitemap_cache incluye namespace image: y <image:loc> por episodio; tests de namespace y ausencia de tag sin thumbnail); plan reorganizado en tres fases de despliegue con subtotales de esfuerzo*
