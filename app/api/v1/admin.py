"""Admin endpoints for system monitoring."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api import deps
from app.core.gee_semaphore import gee_semaphore
from app.models.episode import FireEpisode
from app.models.exploration import InvestigationAsset

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/storage-usage", tags=["admin"])
def get_storage_usage(db: Session = Depends(deps.get_db)):
    """
    Return storage and GEE usage metrics.
    For administrators only.
    """
    # GEE semaphore usage
    gee_usage = gee_semaphore.get_usage()

    # Count HD assets in DB
    total_assets = db.query(func.count(InvestigationAsset.id)).scalar() or 0

    # Count episodes with valid slides
    episodes_with_slides = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM fire_episodes "
                "WHERE slides_data IS NOT NULL "
                "AND jsonb_array_length(slides_data) > 0"
            )
        ).scalar()
        or 0
    )

    total_episodes = db.query(func.count(FireEpisode.id)).scalar() or 0

    slides_pct = (
        round(episodes_with_slides / total_episodes * 100, 1)
        if total_episodes > 0
        else 0
    )

    return {
        "gee": gee_usage,
        "storage": {
            "total_hd_assets": total_assets,
            "episodes_with_slides": episodes_with_slides,
            "episodes_total": total_episodes,
            "slides_coverage_pct": slides_pct,
        },
        "note": "Para uso real de storage en bytes, consultar la consola de Oracle Cloud.",
    }
