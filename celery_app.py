"""
Celery configuration for ForestGuard
Broker: Redis
Workers: Ingestion, Clustering, Recovery/Destruction Analysis
"""

import os
from pathlib import Path
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Load .env for local development (Pydantic only loads it for FastAPI)
load_dotenv(Path(__file__).parent / ".env")

# Inicializar app Celery
celery_app = Celery(
    'forestguard',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1'),
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
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
