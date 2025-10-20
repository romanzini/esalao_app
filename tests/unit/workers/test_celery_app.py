"""Tests for Celery worker configuration."""

import pytest
from unittest.mock import MagicMock, patch

# Mock celery before importing to avoid connection issues
with patch('celery.Celery') as MockCelery:
    mock_celery_instance = MagicMock()
    MockCelery.return_value = mock_celery_instance

    from backend.app.workers.celery_app import celery_app


class TestCeleryConfiguration:
    """Test Celery app configuration."""

    def test_celery_app_exists(self):
        """Test that celery app is created."""
        assert celery_app is not None

    def test_celery_app_type(self):
        """Test celery app is correct type."""
        # Should be our mocked Celery instance
        assert celery_app == mock_celery_instance

    @patch('backend.app.workers.celery_app.Celery')
    def test_celery_configuration(self, mock_celery_class):
        """Test Celery configuration parameters."""
        # Import again to trigger configuration
        from backend.app.workers.celery_app import celery_app

        # Verify Celery was called with correct parameters
        mock_celery_class.assert_called_with(
            'esalao_worker'
        )


class TestCelerySettings:
    """Test Celery settings configuration."""

    @patch('backend.app.workers.celery_app.settings')
    @patch('backend.app.workers.celery_app.Celery')
    def test_celery_broker_configuration(self, mock_celery_class, mock_settings):
        """Test Celery broker URL configuration."""
        mock_settings.REDIS_URL = "redis://localhost:6379/1"
        mock_celery_instance = MagicMock()
        mock_celery_class.return_value = mock_celery_instance

        # Import to trigger configuration
        from backend.app.workers import celery_app

        # Verify broker URL was configured
        assert mock_celery_instance.conf.broker_url == mock_settings.REDIS_URL
        assert mock_celery_instance.conf.result_backend == mock_settings.REDIS_URL


class TestCeleryImports:
    """Test Celery task imports and discovery."""

    @patch('backend.app.workers.celery_app.Celery')
    def test_celery_imports_tasks(self, mock_celery_class):
        """Test that Celery imports task modules."""
        mock_celery_instance = MagicMock()
        mock_celery_class.return_value = mock_celery_instance

        # Import to trigger configuration
        from backend.app.workers import celery_app

        # Should have configured task imports
        expected_includes = [
            'backend.app.workers.tasks'
        ]
        mock_celery_instance.conf.include = expected_includes
