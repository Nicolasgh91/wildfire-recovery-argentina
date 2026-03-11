"""
SEO workers: generación de slugs (SEO-W-01) y caché de sitemap (SEO-W-02).
FOR UPDATE SKIP LOCKED en slugs; cuota minor y upsert seo_pages_cache.
"""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.db.session import SessionLocal
from app.utils.seo_filters import classify_episode_for_sitemap, get_regional_threshold
from app.utils.slug_utils import generate_episode_slug, normalize_province_to_slug
from app.utils.ssg_routes import ZONE_SLUGS
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

MINOR_QUOTA_MAX = 100
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

        # Provincias: una URL por provincia (página 1); paginación no en sitemap por ahora
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
