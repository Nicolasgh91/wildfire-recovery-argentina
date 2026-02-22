"""
Celery Configuration for ForestGuard
====================================

This module initializes the Celery application and defines its configuration.
It serves as the entry point for all background task processing in the ForestGuard system.

Key Components:
1.  **Broker**: Redis (CELERY_BROKER_URL > REDIS_URL > local fallback).
2.  **Backend**: Redis (CELERY_RESULT_BACKEND > broker URL).
3.  **Workers**:
    -   `ingestion`: Handles data fetching (e.g., FIRMS API).
    -   `clustering`: Runs DBSCAN and other clustering algorithms.
    -   `analysis`: Performs heavy computations (recovery, destruction, carousel generation).

Task Routing:
-   `workers.tasks.ingestion.download_firms_daily` -> `ingestion` queue
-   `workers.tasks.clustering.cluster_detections` -> `clustering` queue
-   `workers.tasks.recovery.analyze_recovery` -> `analysis` queue
-   `workers.tasks.destruction.detect_destruction` -> `analysis` queue
-   `workers.tasks.carousel_task.generate_carousel` -> `analysis` queue

Schedule (Beat):
-   `download-firms-daily`: Runs at 00:00 UTC.
-   `cluster-daily`: Runs at 01:00 UTC (processing previous day's data).

Author: ForestGuard Team
"""

from pathlib import Path
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

from app.core.celery_runtime import (
    resolve_celery_broker_url,
    resolve_celery_result_backend,
)

# Load .env for local development (Pydantic only loads it for FastAPI)
# This ensures that when running celery locally, environment variables are available.
load_dotenv(Path(__file__).parent / ".env")

# Initialize Celery app
celery_app = Celery(
    'forestguard',
    broker=resolve_celery_broker_url(),
    backend=resolve_celery_result_backend(),
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
        'workers.tasks.carousel_task',
    ]
)

# Configuración principal
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Routing
    task_routes={
        'workers.tasks.ingestion.download_firms_daily': {'queue': 'ingestion'},
        'workers.tasks.clustering.cluster_detections': {'queue': 'clustering'},
        'workers.tasks.recovery.analyze_recovery': {'queue': 'analysis'},
        'workers.tasks.destruction.detect_destruction': {'queue': 'analysis'},
        'workers.tasks.carousel_task.generate_carousel': {'queue': 'analysis'},
    },
    
    # Retry policy
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Procesa 1 task a la vez
    task_max_retries=3,
    task_default_retry_delay=60,
    
    # Beat schedule (tareas automáticas)
    beat_schedule={
        'download-firms-daily': {
            'task': 'workers.tasks.ingestion.download_firms_daily',
            'schedule': crontab(hour=0, minute=0),  # 00:00 UTC
            'options': {'queue': 'ingestion'}
        },
        'cluster-daily': {
            'task': 'workers.tasks.clustering.cluster_detections',
            'schedule': crontab(hour=1, minute=0),  # 01:00 UTC
            'kwargs': {'days_back': 1},
            'options': {'queue': 'clustering'}
        },
    },
    
    # Worker settings
    worker_max_tasks_per_child=1000,
)

# Define default queue
celery_app.conf.task_default_queue = 'default'

@celery_app.task(bind=True)
def debug_task(self):
    """Test task para verificar Celery funciona"""
    print(f'Request: {self.request!r}')
