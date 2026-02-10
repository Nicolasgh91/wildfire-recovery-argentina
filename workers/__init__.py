"""
ForestGuard Workers Package
Celery tasks para procesamiento asincrónico
"""

from .celery_app import celery_app

__all__ = ['celery_app']