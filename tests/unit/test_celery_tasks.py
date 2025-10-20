"""
Unit tests for Celery tasks.
"""

import pytest
from unittest.mock import Mock
from backend.app.core.celery.tasks.payment_tasks import (
    process_payment_webhook,
    sync_payment_status,
    process_refund,
    cleanup_expired_payments,
)


class TestPaymentTasks:
    """Test payment-related Celery tasks."""

    def test_task_names(self):
        """Test that tasks have correct names."""
        assert process_payment_webhook.name == "payment.process_webhook"
        assert sync_payment_status.name == "payment.sync_payment_status"
        assert process_refund.name == "payment.process_refund"
        assert cleanup_expired_payments.name == "payment.cleanup_expired_payments"

    def test_task_signatures(self):
        """Test that tasks have expected signatures."""
        # Test that tasks can be called (but not executed)
        assert callable(process_payment_webhook)
        assert callable(sync_payment_status)
        assert callable(process_refund)
        assert callable(cleanup_expired_payments)


class TestNotificationTasks:
    """Test notification-related Celery tasks."""

    def test_notification_task_structure(self):
        """Test notification task structure."""
        # Simple test to verify task module structure
        try:
            from backend.app.core.celery.tasks.notification_tasks import send_notification_task
            assert callable(send_notification_task)
        except ImportError:
            pytest.skip("Notification tasks not implemented yet")


class TestTaskRegistry:
    """Test Celery task registry."""

    def test_task_registry_exists(self):
        """Test that task registry is accessible."""
        from backend.app.core.celery.app import celery_app

        # Check that celery app is configured
        assert celery_app is not None
        assert hasattr(celery_app, 'tasks')
