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
        'workers.tasks.seo',
    ]
)

celery_app.Task = DlqTask

# Configuración principal
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Argentina/Buenos_Aires',  # UTC-3 (ART)
    enable_utc=False,
    
    # Routing (GEE tasks → cola gee, gee_spec §3.3)
    task_routes={
        'workers.tasks.ingestion.*': {'queue': 'ingestion'},
        'workers.tasks.clustering.*': {'queue': 'clustering'},
        'workers.tasks.clustering_task.*': {'queue': 'clustering'},
        'workers.tasks.recovery.*': {'queue': 'gee'},
        'workers.tasks.destruction.*': {'queue': 'gee'},
        'workers.tasks.carousel_task.generate_carousel': {'queue': 'gee'},
        'workers.tasks.carousel_task.*': {'queue': 'analysis'},
        'workers.tasks.closure_report_task.*': {'queue': 'reports'},
        'workers.tasks.notification.*': {'queue': 'notification'},
        
        # Remaining existing tasks
        'workers.tasks.geo_enrichment.*': {'queue': 'analysis'},
        'workers.tasks.episode_closer_task.*': {'queue': 'analysis'},
        'workers.tasks.exploration_hd_task.*': {'queue': 'analysis'},
        'workers.tasks.export_task.*': {'queue': 'analysis'},
        'workers.tasks.cleanup_assets_task.*': {'queue': 'analysis'},
        'workers.tasks.pdf_generation_task.*': {'queue': 'reports'},
        'workers.tasks.seo.*': {'queue': 'default'},
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
            'schedule': crontab(hour=0, minute=0),  # 00:00 ART (UTC-3)
            'options': {'queue': 'ingestion'}
        },
        'cluster-daily': {
            'task': 'workers.tasks.clustering.cluster_detections',
            'schedule': crontab(hour=1, minute=0),  # 01:00 ART
            'kwargs': {'days_back': 1},
            'options': {'queue': 'clustering'}
        },
        'cluster-episodes-daily': {
            'task': 'workers.tasks.clustering_task.cluster_fire_episodes_pipeline',
            'schedule': crontab(hour=2, minute=0),  # 02:00 ART
            'kwargs': {'days_back': 90, 'max_events': 5000, 'geo_lookback_hours': 96},
            'options': {'queue': 'clustering'}
        },
        'seo-generate-slugs-daily': {
            'task': 'workers.tasks.seo.generate_slugs_batch',
            'schedule': crontab(hour=3, minute=0),  # 03:00 ART (después de clustering)
            'options': {'queue': 'default'}
        },
        'seo-generate-sitemap-cache': {
            'task': 'workers.tasks.seo.generate_sitemap_cache',
            'schedule': crontab(minute=0, hour='*/5'),  # cada 5 h
            'options': {'queue': 'default'}
        },
        'carousel-daily': {
            'task': 'workers.tasks.carousel_task.generate_carousel',
            'schedule': crontab(hour=0, minute=0),  # 00:00 ART (medianoche)
            'kwargs': {'max_fires': None, 'force_refresh': False},
            'options': {'queue': 'gee'}
        },
        'closure-reports-daily': {
            'task': 'workers.tasks.closure_report_task.generate_closure_reports',
            'schedule': crontab(hour=8, minute=0),  # 08:00 ART
            'kwargs': {'max_fires': None},
            'options': {'queue': 'reports'}
        },
        'cleanup-expired-assets': {
            'task': 'workers.tasks.cleanup_assets_task.cleanup_expired_assets',
            'schedule': crontab(hour=4, minute=0),  # 04:00 ART
            'options': {'queue': 'analysis'}
        },
        'close-extinct-episodes-daily': {
            'task': 'workers.tasks.episode_closer_task.close_extinct_episodes',
            'schedule': crontab(hour=5, minute=0),  # 05:00 ART
            'options': {'queue': 'analysis'},
        },
        # GEE: recovery mensual — día 2 de cada mes 02:00 UTC (gee_spec §3.3)
        'recovery-monthly': {
            'task': 'workers.tasks.recovery.batch_recovery_monthly',
            'schedule': crontab(hour=23, minute=0, day_of_month=1),  # 23:00 ART día 1 = 02:00 UTC día 2
            'options': {'queue': 'gee'},
        },
        # GEE: recovery recientes — lunes 03:00 UTC
        'recovery-weekly-recent': {
            'task': 'workers.tasks.recovery.batch_recovery_recent',
            'schedule': crontab(hour=0, minute=0, day_of_week=1),  # Lunes 00:00 ART = 03:00 UTC
            'options': {'queue': 'gee'},
        },
        # UC-F12: Monthly VAE recovery (legacy name, now uses batch_recovery_monthly above)
        'vae-recovery-monthly': {
            'task': 'workers.tasks.recovery.batch_recovery_analysis',
            'schedule': crontab(hour=5, minute=0, day_of_month=1),
            'kwargs': {'max_events': 50},
            'options': {'queue': 'gee'},
        },
        # UC-F12: Monthly VAE destruction detection
        'vae-destruction-monthly': {
            'task': 'workers.tasks.destruction.batch_destruction_detection',
            'schedule': crontab(hour=6, minute=0, day_of_month=1),
            'kwargs': {'max_events': 50},
            'options': {'queue': 'gee'},
        },
        # UC-F12: Weekly VAE episode recovery analysis for carousel
        'vae-episodes-weekly': {
            'task': 'workers.tasks.recovery.batch_episode_recovery_analysis',
            'schedule': crontab(hour=2, minute=0, day_of_week=1),
            'kwargs': {'max_episodes': 20, 'carousel_only': True},
            'options': {'queue': 'gee'},
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
