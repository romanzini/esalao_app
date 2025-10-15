"""Celery tasks."""

import structlog

from backend.app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="tasks.example_task")
def example_task(param: str) -> dict:
    """Example Celery task."""
    logger.info("example_task_started", param=param)

    # Task logic here
    result = {"status": "completed", "param": param}

    logger.info("example_task_completed", result=result)
    return result
