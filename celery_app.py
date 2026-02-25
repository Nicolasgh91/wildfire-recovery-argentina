"""
Celery Configuration — Proxy to canonical workers.celery_app
============================================================

This file exists for backward compatibility with scripts and local
development that invoke ``celery -A celery_app``.

The single source of truth is ``workers/celery_app.py``.
"""

from workers.celery_app import celery_app  # noqa: F401
