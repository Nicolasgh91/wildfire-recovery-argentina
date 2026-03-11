"""
SEO workers:
- SEO-W-01: generación de slugs (FOR UPDATE SKIP LOCKED).
- SEO-W-02: caché de sitemap con cuota minor y upsert seo_pages_cache.
- SEO-W-03: exportación de artefactos SSG (rutas y datos SEO) hacia storage OCI.
"""
import json
import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.storage_service import BUCKETS, get_storage_service
from app.utils.jsonld_utils import build_episode_jsonld
from app.utils.seo_filters import classify_episode_for_sitemap, get_regional_threshold
from app.utils.slug_utils import generate_episode_slug, normalize_province_to_slug
from app.utils.ssg_routes import STRATEGIC_ZONES, ZONE_SLUGS, build_ssg_routes_payload
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

MINOR_QUOTA_MAX = 100
CHUNK_SIZE = 1000
SITEMAP_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">"""
SITEMAP_FOOTER = "</urlset>"


def _url_entry(
    loc: str,
    changefreq: str,
    priority: str,
    lastmod: str | None = None,
    image_url: str | None = None,
    base_url: str = "https://forestguard.freedynamicdns.org",
) -> str:
    base = base_url.rstrip("/")
    full_loc = f"{base}{loc}"
    parts = [f"  <url><loc>{full_loc}</loc>"]
    if lastmod:
        parts.append(f"    <lastmod>{lastmod}</lastmod>")
    parts.append(f"    <changefreq>{changefreq}</changefreq>")
    parts.append(f"    <priority>{priority}</priority>")
    if image_url:
        parts.append(f"    <image:image><image:loc>{image_url}</image:loc></image:image>")
    parts.append("  </url>")
    return "\n".join(parts)


def _build_sitemap_xml(url_entries: list[str]) -> str:
    return SITEMAP_HEADER + "\n" + "\n".join(url_entries) + "\n" + SITEMAP_FOOTER


def _province_to_slug(province_name: str) -> str:
    normalized = unicodedata.normalize("NFD", province_name)
    ascii_str = normalized.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_str.lower()).strip("-")


def _derive_episode_dict(row: dict) -> dict:
    """
    Traduce columnas reales de fire_episodes al contrato que esperan
    classify_episode_for_sitemap y build_episode_jsonld.
    """
    provinces = row.get("provinces") or []
    prov_name = provinces[0] if provinces else "argentina"
    prov_slug = _province_to_slug(prov_name)

    slides = row.get("slides_data") or []
    has_images = row.get("slides_status") == "ready"
    thumbnail = next(
        (s.get("thumbnail_url") for s in slides if s.get("thumbnail_url")),
        None,
    )

    start = row.get("start_date")
    end = row.get("end_date") or row.get("last_seen_at")
    dur = (end - start).days if (start and end) else None

    return {
        "slug": row["slug"],
        "seo_title": row.get("seo_title"),
        "seo_description": row.get("seo_description"),
        "status": row.get("status"),
        "affected_area_ha": row.get("estimated_area_hectares") or 0,
        "province_slug": prov_slug,
        "province_name": prov_name,
        "has_satellite_images": has_images,
        "thumbnail_url": thumbnail,
        "duration_days": dur,
        "started_at": start.isoformat() if start else None,
        "ended_at": end.isoformat() if end else None,
        "bbox_minx": row.get("bbox_minx"),
        "bbox_miny": row.get("bbox_miny"),
        "bbox_maxx": row.get("bbox_maxx"),
        "bbox_maxy": row.get("bbox_maxy"),
        "updated_at": row.get("updated_at"),
        "slides_status": row.get("slides_status"),
    }


@celery_app.task(
    bind=True,
    name="workers.tasks.seo.generate_slugs_batch",
    queue="default",
    max_retries=2,
)
def generate_slugs_batch(self):
    """Genera slugs para episodios que no lo tienen. FOR UPDATE SKIP LOCKED para evitar carreras."""
    db = SessionLocal()
    try:
        result = db.execute(
            text(
                "SELECT id, provinces, start_date FROM fire_episodes "
                "WHERE slug IS NULL ORDER BY id LIMIT 500 FOR UPDATE SKIP LOCKED"
            )
        )
        rows = result.fetchall()
        updated = errors = 0
        for row in rows:
            ep_id, provinces, start_date = row[0], row[1], row[2]
            province_name = (provinces[0] if provinces else "argentina") or "argentina"
            year = start_date.year if start_date else datetime.now(timezone.utc).year
            try:
                slug = generate_episode_slug(
                    province_name, year, str(ep_id), db=db
                )
                db.execute(
                    text(
                        "UPDATE fire_episodes SET slug = :slug WHERE id = :id AND slug IS NULL"
                    ),
                    {"slug": slug, "id": ep_id},
                )
                updated += 1
            except Exception as exc:
                logger.error("generate_slugs_batch error for %s: %s", ep_id, exc)
                errors += 1
        db.commit()
        logger.info("generate_slugs_batch: %s generated, %s errors", updated, errors)
        return {"updated": updated, "errors": errors}
    except Exception as exc:
        db.rollback()
        logger.exception("generate_slugs_batch failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="workers.tasks.seo.generate_sitemap_cache",
    queue="default",
    max_retries=2,
)
def generate_sitemap_cache(self, base_url: str | None = None):
    """Genera sitemap XML con image:loc y upsert en seo_pages_cache. Actualiza seo_minor_fire_quota si hay minor."""
    from app.core.config import settings

    base = (base_url or getattr(settings, "SITE_BASE_URL", "") or "https://forestguard.freedynamicdns.org").rstrip("/")

    db = SessionLocal()
    try:
        # Umbrales por región (province_slugs, min_affected_area_ha)
        th_rows = db.execute(
            text("SELECT province_slugs, min_affected_area_ha FROM seo_region_thresholds")
        ).fetchall()
        thresholds = [
            {"province_slugs": r[0], "min_affected_area_ha": r[1]} for r in th_rows
        ]

        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        quota_row = db.execute(
            text("SELECT url_count FROM seo_minor_fire_quota WHERE year_month = :ym"),
            {"ym": year_month},
        ).fetchone()
        minor_quota_used = min(quota_row[0] if quota_row else 0, MINOR_QUOTA_MAX)

        urls: list[str] = []
        minor_added = 0

        for path in ["/metodologia", "/acerca"]:
            urls.append(_url_entry(path, "monthly", "1.0", base_url=base))
        for p in ZONE_SLUGS:
            urls.append(_url_entry(f"/zonas/{p}", "weekly", "0.8", base_url=base))

        # Provincias: una URL por provincia (página 1)
        from app.utils.ssg_routes import PROVINCES

        for p in PROVINCES:
            urls.append(_url_entry(f"/provincias/{p}", "daily", "0.9", base_url=base))

        # Episodios con slug
        ep_result = db.execute(
            text("""
                SELECT slug, updated_at, estimated_area_hectares, status,
                       slides_data, provinces, start_date, end_date, last_seen_at
                FROM fire_episodes WHERE slug IS NOT NULL
            """)
        )
        for row in ep_result:
            slug, updated_at, est_ha, status, slides_data, provinces, start_date, end_date, last_seen = row
            has_satellite = bool(
                slides_data
                and len(slides_data) > 0
                and any(s.get("thumbnail_url") for s in (slides_data or []))
            )
            end = end_date or last_seen
            duration_days = (end - start_date).days if (start_date and end) else None
            province_slug = normalize_province_to_slug(
                (provinces[0] if provinces else "") or "argentina"
            )
            thumbnail_url = next(
                (s.get("thumbnail_url") for s in (slides_data or []) if s.get("thumbnail_url")),
                None,
            )

            episode_dict = {
                "status": status,
                "has_satellite_images": has_satellite,
                "duration_days": duration_days,
                "affected_area_ha": float(est_ha) if est_ha is not None else 0,
                "province_slug": province_slug,
            }
            quota_snapshot = min(minor_quota_used + minor_added, MINOR_QUOTA_MAX)
            cls = classify_episode_for_sitemap(
                episode_dict, thresholds, quota_snapshot, MINOR_QUOTA_MAX
            )
            lastmod_str = str(updated_at.date()) if updated_at else None

            if cls == "standard":
                urls.append(
                    _url_entry(
                        f"/episodios/{slug}",
                        "daily",
                        "0.7",
                        lastmod=lastmod_str,
                        image_url=thumbnail_url,
                        base_url=base,
                    )
                )
            elif cls == "minor":
                urls.append(
                    _url_entry(
                        f"/episodios/{slug}",
                        "weekly",
                        "0.5",
                        lastmod=lastmod_str,
                        image_url=thumbnail_url,
                        base_url=base,
                    )
                )
                minor_added += 1

        if minor_added > 0:
            db.execute(
                text("""
                    INSERT INTO seo_minor_fire_quota (year_month, url_count)
                    VALUES (:ym, :cnt)
                    ON CONFLICT (year_month) DO UPDATE SET
                      url_count = LEAST(seo_minor_fire_quota.url_count + :cnt2, 100),
                      updated_at = NOW()
                """),
                {"ym": year_month, "cnt": minor_added, "cnt2": minor_added},
            )

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=6)
        stale_until = now + timedelta(hours=30)
        # Paginación de provincias (DT-F3-06): descomentar la llamada cuando Search Console
        # reporte rastreo significativo de rutas /provincias/*/pagina/N.
        # _add_paginated_province_urls(urls, db)

        xml = _build_sitemap_xml(urls)
        content_json = json.dumps({"xml": xml})
        db.execute(
            text("""
                INSERT INTO seo_pages_cache (page_type, slug, cached_at, expires_at, stale_until, content)
                VALUES ('sitemap', 'main', :cached_at, :expires_at, :stale_until, CAST(:content AS jsonb))
                ON CONFLICT (page_type, slug) DO UPDATE SET
                  content = EXCLUDED.content,
                  cached_at = EXCLUDED.cached_at,
                  expires_at = EXCLUDED.expires_at,
                  stale_until = EXCLUDED.stale_until
            """),
            {
                "cached_at": now,
                "expires_at": expires_at,
                "stale_until": stale_until,
                "content": content_json,
            },
        )
        db.commit()
        logger.info("generate_sitemap_cache: %s URLs (%s minor)", len(urls), minor_added)
        return {"url_count": len(urls), "minor_added": minor_added}
    except Exception as exc:
        db.rollback()
        logger.exception("generate_sitemap_cache failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


def _add_paginated_province_urls(urls: list[str], db) -> None:
    """
    Agrega URLs paginadas de provincias al sitemap principal.

    Implementación basada en el fragmento canónico de DT-F3-06:
    - Deriva province_name desde provinces[1] (ARRAY) en SQL.
    - Usa _province_to_slug() para derivar el slug en Python.
    - Calcula total_pages con settings.PAGE_SIZE.
    - Emite solo páginas >= 2 (la página 1 ya se agregó en generate_sitemap_cache).

    Esta función debe activarse solo cuando Search Console reporte rastreo de
    rutas paginadas; por defecto permanece inactiva para minimizar ruido SEO.
    """
    from app.utils.ssg_routes import PROVINCES

    PAGE_SIZE = settings.PAGE_SIZE

    province_rows = db.execute(
        text(
            """
            SELECT provinces[1] AS province_name, COUNT(*) AS count
            FROM fire_episodes
            WHERE slug IS NOT NULL
              AND provinces IS NOT NULL
              AND cardinality(provinces) > 0
            GROUP BY provinces[1]
            """
        )
    ).fetchall()

    for row in province_rows:
        province_name = row["province_name"]
        if province_name is None:
            continue
        prov_slug = _province_to_slug(province_name)
        # Solo considerar provincias que existen en PROVINCES para evitar slugs huérfanos
        if prov_slug not in PROVINCES:
            continue
        total_count = int(row["count"])
        if total_count <= 0:
            continue
        total_pages = max(1, -(-total_count // PAGE_SIZE))  # división techo
        if total_pages <= 1:
            continue
        for page_n in range(2, total_pages + 1):
            urls.append(
                _url_entry(
                    f"/provincias/{prov_slug}/pagina/{page_n}",
                    "weekly",
                    "0.4",
                    base_url=getattr(settings, "SITE_BASE_URL", "")
                    or "https://forestguard.freedynamicdns.org",
                )
            )


@celery_app.task(
    bind=True,
    name="workers.tasks.seo.export_ssg_artifacts",
    queue="default",
    max_retries=2,
)
def export_ssg_artifacts(self):
    """
    SEO-W-03: exporta artefactos SSG hacia storage (OCI o backend configurado).
    Genera:
    - seo/ssg-routes.json
    - seo/ssg-seo-data.json
    """
    db = SessionLocal()
    storage = get_storage_service()
    try:
        # Umbrales por región (province_slugs, min_affected_area_ha)
        th_rows = db.execute(
            text("SELECT province_slugs, min_affected_area_ha FROM seo_region_thresholds")
        ).fetchall()
        thresholds = [
            {"province_slugs": r[0], "min_affected_area_ha": r[1]} for r in th_rows
        ]

        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
        quota_row = db.execute(
            text("SELECT url_count FROM seo_minor_fire_quota WHERE year_month = :ym"),
            {"ym": year_month},
        ).fetchone()
        minor_quota_used = min(quota_row[0] if quota_row else 0, MINOR_QUOTA_MAX)

        eligible_slugs: list[str] = []
        minor_n = 0
        seo_data_map: dict[str, dict] = {}
        province_counts: dict[str, int] = {}

        # Query principal: solo columnas existentes y slides_status = 'ready'
        result = db.execute(
            text(
                """
                SELECT slug, status, estimated_area_hectares,
                       slides_data, slides_status, provinces,
                       start_date, end_date, last_seen_at,
                       bbox_minx, bbox_miny, bbox_maxx, bbox_maxy,
                       seo_title, seo_description, updated_at
                FROM fire_episodes
                WHERE slug IS NOT NULL
                  AND slides_status = 'ready'
                ORDER BY id
                """
            )
        )

        base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/") or "https://forestguard.freedynamicdns.org"

        while True:
            chunk = result.fetchmany(CHUNK_SIZE)
            if not chunk:
                break
            for raw in chunk:
                ep = _derive_episode_dict(dict(raw))
                quota_snapshot = min(minor_quota_used + minor_n, MINOR_QUOTA_MAX)
                cls = classify_episode_for_sitemap(
                    {
                        "status": ep["status"],
                        "has_satellite_images": ep["has_satellite_images"],
                        "duration_days": ep["duration_days"],
                        "affected_area_ha": ep["affected_area_ha"],
                        "province_slug": ep["province_slug"],
                    },
                    thresholds,
                    quota_snapshot,
                    MINOR_QUOTA_MAX,
                )
                if cls in ("standard", "minor"):
                    slug = ep["slug"]
                    eligible_slugs.append(slug)
                    if cls == "minor":
                        minor_n += 1

                    canonical = f"{base_url}/episodios/{slug}"
                    seo_data_map[slug] = {
                        "title": ep["seo_title"],
                        "description": ep["seo_description"],
                        "jsonld": build_episode_jsonld(ep, base_url),
                        "og_image": ep["thumbnail_url"],
                        "og_image_width": 1200,
                        "og_image_height": 630,
                        "canonical": canonical,
                    }

                    p = ep["province_slug"]
                    province_counts[p] = province_counts.get(p, 0) + 1

        # zone_counts a partir de STRATEGIC_ZONES localmente, sin HTTP
        zone_counts: dict[str, int] = {
            zone_slug: sum(province_counts.get(p, 0) for p in prov_list)
            for zone_slug, prov_list in STRATEGIC_ZONES.items()
        }

        now = datetime.now(timezone.utc)
        generated_at = now.isoformat().replace("+00:00", "Z")

        routes_payload = build_ssg_routes_payload(
            episode_slugs=eligible_slugs,
            generated_at=generated_at,
            episodes_per_province=province_counts,
            episodes_per_zone=zone_counts,
        )

        routes_content = json.dumps(routes_payload, indent=2, ensure_ascii=False)
        seo_content = json.dumps(
            {"generated_at": generated_at, "episodes": seo_data_map},
            indent=2,
            ensure_ascii=False,
        )

        storage.upload_bytes(
            data=routes_content.encode("utf-8"),
            key="seo/ssg-routes.json",
            bucket=BUCKETS["reports"],
            content_type="application/json",
        )
        storage.upload_bytes(
            data=seo_content.encode("utf-8"),
            key="seo/ssg-seo-data.json",
            bucket=BUCKETS["reports"],
            content_type="application/json",
        )

        db.commit()
        logger.info(
            "export_ssg_artifacts: %s rutas, %s episodios SEO",
            routes_payload["total"],
            len(seo_data_map),
        )
        return {
            "routes_total": routes_payload["total"],
            "seo_data_count": len(seo_data_map),
            "province_counts": province_counts,
            "zone_counts": zone_counts,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("export_ssg_artifacts failed: %s", exc)
        raise self.retry(exc=exc)
    finally:
        db.close()
