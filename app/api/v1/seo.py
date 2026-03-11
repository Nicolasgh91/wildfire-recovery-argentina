"""
SEO: sitemap.xml con stale-while-revalidate y bloqueo Redis.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import deps
from app.services.redis_service import redis_client

router = APIRouter()

SITEMAP_REGEN_LOCK_KEY = "seo:sitemap:regen_lock"
SITEMAP_REGEN_LOCK_TTL = 300


def _try_enqueue_sitemap_regen():
    acquired = redis_client.set(
        SITEMAP_REGEN_LOCK_KEY, "1", nx=True, ex=SITEMAP_REGEN_LOCK_TTL
    )
    if acquired:
        from workers.tasks.seo import generate_sitemap_cache

        generate_sitemap_cache.delay()
        return True
    return False


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap(db: Session = Depends(deps.get_db)):
    """Sirve el sitemap desde seo_pages_cache. Stale-while-revalidate; encola regeneración si expirado."""
    row = db.execute(
        text(
            "SELECT content, expires_at, stale_until FROM seo_pages_cache "
            "WHERE page_type = 'sitemap' AND slug = 'main'"
        )
    ).fetchone()

    if not row:
        raise HTTPException(
            status_code=503,
            detail="Sitemap en generación inicial. Reintente en unos minutos.",
        )

    content, expires_at, stale_until = row[0], row[1], row[2]
    xml = content.get("xml") if isinstance(content, dict) else None
    if not xml:
        raise HTTPException(status_code=503, detail="Sitemap no disponible.")

    now = datetime.now(timezone.utc)
    enqueued = _try_enqueue_sitemap_regen()

    if expires_at and expires_at >= now:
        return Response(
            content=xml,
            media_type="application/xml",
            headers={"Cache-Control": "public, max-age=21600"},
        )

    if stale_until and stale_until >= now:
        return Response(
            content=xml,
            media_type="application/xml",
            headers={
                "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
                "X-Cache-Status": "stale",
                "X-Regen-Enqueued": "true" if enqueued else "false",
            },
        )

    return Response(
        content=xml,
        media_type="application/xml",
        headers={
            "Cache-Control": "public, max-age=300",
            "X-Cache-Status": "very-stale",
            "X-Regen-Enqueued": "true" if enqueued else "false",
        },
    )
