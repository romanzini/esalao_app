"""
Celery configuration for payment processing background tasks.
"""

import os
from celery import Celery
from backend.app.core.config import settings

# Create Celery app instance
celery_app = Celery(
    "esalao_payments",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.app.core.celery.tasks.payment_tasks",
        "backend.app.core.celery.tasks.notification_tasks",
        "backend.app.core.celery.tasks.reconciliation_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # General settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "payment.*": {"queue": "payments"},
        "notification.*": {"queue": "notifications"},
        "reconciliation.*": {"queue": "reconciliation"},
    },

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,

    # Performance settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,

    # Monitoring
    task_send_sent_event=True,
    task_track_started=True,

    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,

    # Task time limits
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes

    # Queue priorities
    task_default_priority=5,
    worker_hijack_root_logger=False,

    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

# Configure queue priorities
celery_app.conf.task_routes.update({
    "payment.process_webhook": {"queue": "payments", "priority": 8},
    "payment.sync_payment_status": {"queue": "payments", "priority": 6},
    "payment.process_refund": {"queue": "payments", "priority": 7},
    "notification.send_payment_confirmation": {"queue": "notifications", "priority": 5},
    "notification.send_payment_failed": {"queue": "notifications", "priority": 8},
    "reconciliation.daily_reconciliation": {"queue": "reconciliation", "priority": 3},
    "reconciliation.sync_provider_payments": {"queue": "reconciliation", "priority": 4},
})

# Custom task base class for payment tasks
class PaymentTask(celery_app.Task):
    """Base task class with payment-specific error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure with logging."""
        from backend.app.domain.payments.logging_service import get_payment_logger
        from backend.app.db.session import get_sync_db

        with get_sync_db() as db:
            logger = get_payment_logger(db)
            logger.log_exception(
                exception=exc,
                context=f"Celery task failure: {self.name}",
                correlation_id=task_id,
            )

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry with logging."""
        from backend.app.domain.payments.logging_service import get_payment_logger
        from backend.app.db.session import get_sync_db

        with get_sync_db() as db:
            logger = get_payment_logger(db)
            logger.log(
                log_type="task_retry",
                message=f"Task retry: {self.name} - {str(exc)}",
                correlation_id=task_id,
                retry_count=self.request.retries,
                error_message=str(exc),
            )


# Set default task base class
celery_app.Task = PaymentTask

# Health check task
@celery_app.task(name="health_check")
def health_check():
    """Simple health check task for monitoring."""
    return {"status": "healthy", "timestamp": ""}


if __name__ == "__main__":
    celery_app.start()
