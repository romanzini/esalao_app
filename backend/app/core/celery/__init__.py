"""
Celery application for background task processing.
"""

from backend.app.core.celery.app import celery_app

__all__ = ["celery_app"]
