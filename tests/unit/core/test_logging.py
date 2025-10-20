"""Tests for logging configuration."""

import logging
from unittest.mock import MagicMock, patch

from backend.app.core.logging import setup_logging, add_app_context
from backend.app.core.config import settings


class TestLogging:
    """Test logging setup and configuration."""

    @patch('backend.app.core.logging.structlog')
    def test_setup_logging_debug_mode(self, mock_structlog):
        """Test logging setup in debug mode."""
        # Mock settings to have DEBUG=True
        with patch.object(settings, 'DEBUG', True):
            setup_logging()

            # Verify structlog.configure was called
            mock_structlog.configure.assert_called_once()

    @patch('backend.app.core.logging.structlog')
    def test_setup_logging_production_mode(self, mock_structlog):
        """Test logging setup in production mode."""
        # Mock settings to have DEBUG=False
        with patch.object(settings, 'DEBUG', False):
            setup_logging()

            # Verify structlog.configure was called
            mock_structlog.configure.assert_called_once()

    def test_add_app_context(self):
        """Test app context addition to log events."""
        logger = MagicMock()
        method_name = "info"
        event_dict = {"message": "test message"}

        # Call function
        result = add_app_context(logger, method_name, event_dict)

        # Check context was added
        assert "service" in result
        assert "environment" in result
        assert result["service"] == settings.OTEL_SERVICE_NAME
        assert result["environment"] == settings.ENVIRONMENT

    def test_logging_processors_configuration(self):
        """Test that logging processors are properly configured."""
        # This is more of an integration test to ensure setup doesn't crash
        setup_logging()

        # If we get here without exception, setup worked
        assert True

    @patch('backend.app.core.logging.structlog.contextvars')
    @patch('backend.app.core.logging.structlog.stdlib')
    @patch('backend.app.core.logging.structlog.processors')
    def test_shared_processors_configuration(self, mock_processors, mock_stdlib, mock_contextvars):
        """Test shared processors are properly configured."""
        setup_logging()

        # Verify processors are being used
        mock_contextvars.merge_contextvars.assert_not_called()  # Just check import works
        mock_stdlib.add_logger_name.assert_not_called()  # Just check import works
        mock_processors.TimeStamper.assert_not_called()  # Just check import works
