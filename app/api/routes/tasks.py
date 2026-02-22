from fastapi import APIRouter, HTTPException
from workers.celery_app import celery_app
from workers.tasks.ingestion import download_firms_daily

router = APIRouter()


@router.post("/download-firms", summary="Trigger FIRMS download")
async def task_download_firms():
    """
    Enqueue FIRMS download task.
    """
    task = download_firms_daily.delay()
    return {
        "task_id": task.id,
        "status": "enqueued",
        "task_name": "download_firms_daily",
    }


@router.post("/cluster", summary="Trigger clustering")
async def task_cluster():
    """
    Enqueue clustering task (last 24h).
    """
    try:
        # Lazy import to avoid importing sklearn at API startup time.
        from workers.tasks.clustering import cluster_detections
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Clustering runtime unavailable in this environment "
                "(blocked or missing native dependencies)."
            ),
        ) from exc

    task = cluster_detections.delay(days_back=1)
    return {
        "task_id": task.id,
        "status": "enqueued",
        "task_name": "cluster_detections",
    }


@router.get("/{task_id}", summary="Get task status")
async def get_task_status(task_id: str):
    """
    Get Celery task status.
    """
    task = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None,
        "error": str(task.info) if task.failed() else None,
    }
