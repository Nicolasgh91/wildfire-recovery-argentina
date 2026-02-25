"""
Celery configuration for ForestGuard
Broker: Redis
Workers: Ingestion, Clustering, Recovery/Destruction Analysis
"""

from datetime import datetime, timezone

from celery import Celery, Task
from celery.exceptions import Ignore, Retry
from celery.schedules import crontab

from app.core.celery_runtime import (
    resolve_celery_broker_url,
    resolve_celery_result_backend,
)
from app.db.session import ensure_database_url_configured
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


def _validate_worker_runtime_configuration() -> None:
    ensure_database_url_configured(context="Celery worker startup")


_validate_worker_runtime_configuration()


# Inicializar app Celery
celery_app = Celery(
    'forestguard',
    broker=resolve_celery_broker_url(),
    backend=resolve_celery_result_backend(),
    include=[
        'workers.tasks.ingestion',
        'workers.tasks.clustering',
        'workers.tasks.clustering_task',
        'workers.tasks.geo_enrichment',
        'workers.tasks.episode_merge_task',
        'workers.tasks.carousel_task',
        'workers.tasks.episode_closer_task',
        'workers.tasks.closure_report_task',
        'workers.tasks.recovery',
        'workers.tasks.destruction',
        'workers.tasks.notification',
        'workers.tasks.exploration_hd_task',
        'workers.tasks.export_task',
        'workers.tasks.pdf_generation_task',
        'workers.tasks.cleanup_assets_task',
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
        'workers.tasks.clustering_task.cluster_fire_episodes_pipeline': {'queue': 'clustering'},
        'workers.tasks.event_status_task.update_event_statuses': {'queue': 'clustering'},
        'workers.tasks.geo_enrichment.enrich_recent_fire_events': {'queue': 'analysis'},
        'workers.tasks.carousel_task.generate_carousel': {'queue': 'analysis'},
        'workers.tasks.episode_closer_task.close_extinct_episodes': {'queue': 'analysis'},
        'workers.tasks.closure_report_task.generate_closure_reports': {'queue': 'analysis'},
        'workers.tasks.exploration_hd_task.generate_exploration_hd': {'queue': 'analysis'},
        'workers.tasks.recovery.analyze_recovery': {'queue': 'vae'},
        'workers.tasks.recovery.batch_recovery_analysis': {'queue': 'vae'},
        'workers.tasks.destruction.detect_destruction': {'queue': 'vae'},
        'workers.tasks.destruction.batch_destruction_detection': {'queue': 'vae'},
        'workers.tasks.notification.send_contact_email': {'queue': 'notification'},
        'workers.tasks.export_task.export_fires_async': {'queue': 'analysis'},
        'workers.tasks.pdf_generation_task.generate_pdf_for_job': {'queue': 'reports'},
        'workers.tasks.cleanup_assets_task.cleanup_expired_assets': {'queue': 'analysis'},
        'workers.tasks.episode_closer_task.close_extinct_episodes': {'queue': 'analysis'},
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
        'update-event-statuses-daily': {
            'task': 'workers.tasks.event_status_task.update_event_statuses',
            'schedule': crontab(hour=1, minute=30),  # 01:30 UTC (post clustering, pre enrichment)
            'options': {'queue': 'clustering'}
        },
        'enrich-events-daily': {
            'task': 'workers.tasks.geo_enrichment.enrich_recent_fire_events',
            'schedule': crontab(hour=1, minute=45),  # 01:45 UTC (post clustering, pre episodes)
            'kwargs': {'lookback_hours': 72, 'max_events': 5000},
            'options': {'queue': 'analysis'}
        },
        'cluster-episodes-daily': {
            'task': 'workers.tasks.clustering_task.cluster_fire_episodes_pipeline',
            'schedule': crontab(hour=2, minute=0),  # 02:00 UTC (post enrichment 01:45)
            'kwargs': {'days_back': 90, 'max_events': 5000},
            'options': {'queue': 'clustering'}
        },
        'carousel-daily': {
            'task': 'workers.tasks.carousel_task.generate_carousel',
            'schedule': crontab(hour=16, minute=48),  # TEMPORAL: forzar ejecucion inmediata, restaurar a crontab(hour=3, minute=0)
            'kwargs': {'max_fires': None, 'force_refresh': False},
            'options': {'queue': 'analysis'}
        },
        'closure-reports-daily': {
            'task': 'workers.tasks.closure_report_task.generate_closure_reports',
            'schedule': crontab(hour=8, minute=0),  # 08:00 UTC
            'kwargs': {'max_fires': None},
            'options': {'queue': 'analysis'}
        },
        'cleanup-expired-assets': {
            'task': 'workers.tasks.cleanup_assets_task.cleanup_expired_assets',
            'schedule': crontab(hour=4, minute=0),  # 04:00 UTC
            'options': {'queue': 'analysis'}
        },
        'close-extinct-episodes-daily': {
            'task': 'workers.tasks.episode_closer_task.close_extinct_episodes',
            'schedule': crontab(hour=5, minute=0),  # 05:00 UTC
            'options': {'queue': 'analysis'},
        },
        # UC-F12: Monthly VAE recovery analysis for active fire events
        'vae-recovery-monthly': {
            'task': 'workers.tasks.recovery.batch_recovery_analysis',
            'schedule': crontab(hour=5, minute=0, day_of_month=1),  # 05:00 UTC, 1st of each month
            'kwargs': {'max_events': 50},
            'options': {'queue': 'vae'},
        },
        # UC-F12: Monthly VAE destruction detection for active fire events
        'vae-destruction-monthly': {
            'task': 'workers.tasks.destruction.batch_destruction_detection',
            'schedule': crontab(hour=6, minute=0, day_of_month=1),  # 06:00 UTC, 1st of each month
            'kwargs': {'max_events': 50},
            'options': {'queue': 'vae'},
        },
        # UC-F12: Weekly VAE episode recovery analysis for carousel
        'vae-episodes-weekly': {
            'task': 'workers.tasks.recovery.batch_episode_recovery_analysis',
            'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 02:00 UTC
            'kwargs': {'max_episodes': 20, 'carousel_only': True},
            'options': {'queue': 'vae'},
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
