from fastapi import APIRouter

from app.core.metrics import build_metrics_snapshot

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def get_metrics():
    return build_metrics_snapshot()
