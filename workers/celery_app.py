"""
Celery configuration for ForestGuard
Broker: Redis
Workers: Ingestion, Clustering, Recovery/Destruction Analysis
"""

import os
from datetime import datetime, timezone

from celery import Celery, Task
from celery.exceptions import Ignore, Retry
from celery.schedules import crontab

from app.workers.dlq import enqueue_failure

class DlqTask(Task):
    """Base task that sends terminal failures to the DLQ."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        if isinstance(exc, (Retry, Ignore)):
            return super().on_failure(exc, task_id, args, kwargs, einfo)

        max_retries = getattr(self, "max_retries", None)
        retries = getattr(self.request, "retries", 0)
        if max_retries is not None and retries < max_retries:
            return super().on_failure(exc, task_id, args, kwargs, einfo)

        delivery = getattr(self.request, "delivery_info", {}) or {}
        payload = {
            "task_id": task_id,
            "task_name": self.name,
            "queue": delivery.get("routing_key"),
            "args": args,
            "kwargs": kwargs,
            "retries": retries,
            "max_retries": max_retries,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback": getattr(einfo, "traceback", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hostname": getattr(self.request, "hostname", None),
        }
        enqueue_failure(payload)

        return super().on_failure(exc, task_id, args, kwargs, einfo)


# Inicializar app Celery
celery_app = Celery(
    'forestguard',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/1'),
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.clustering_task',
        'workers.tasks.episode_merge_task',
        'workers.tasks.carousel_task',
        'workers.tasks.closure_report_task',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
        'workers.tasks.notification',
        'workers.tasks.exploration_hd_task',
        'workers.tasks.export_task',
    ]
)

celery_app.Task = DlqTask

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
        'workers.tasks.clustering_task.cluster_fire_episodes': {'queue': 'clustering'},
        'workers.tasks.carousel_task.generate_carousel': {'queue': 'analysis'},
        'workers.tasks.closure_report_task.generate_closure_reports': {'queue': 'analysis'},
        'workers.tasks.exploration_hd_task.generate_exploration_hd': {'queue': 'analysis'},
        'workers.tasks.recovery.analyze_recovery': {'queue': 'analysis'},
        'workers.tasks.destruction.detect_destruction': {'queue': 'analysis'},
        'workers.tasks.notification.send_contact_email': {'queue': 'notification'},
        'workers.tasks.export_task.export_fires_async': {'queue': 'analysis'},
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
        'cluster-episodes-daily': {
            'task': 'workers.tasks.clustering_task.cluster_fire_episodes',
            'schedule': crontab(hour=2, minute=0),  # 02:00 UTC
            'kwargs': {'days_back': 90, 'max_events': 5000},
            'options': {'queue': 'clustering'}
        },
        'carousel-daily': {
            'task': 'workers.tasks.carousel_task.generate_carousel',
            'schedule': crontab(hour=3, minute=0),  # 03:00 UTC
            'kwargs': {'max_fires': None, 'force_refresh': False},
            'options': {'queue': 'analysis'}
        },
        'closure-reports-daily': {
            'task': 'workers.tasks.closure_report_task.generate_closure_reports',
            'schedule': crontab(hour=8, minute=0),  # 08:00 UTC
            'kwargs': {'max_fires': None},
            'options': {'queue': 'analysis'}
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
