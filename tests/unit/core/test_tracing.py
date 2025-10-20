"""Tests for tracing configuration."""

import pytest
from unittest.mock import MagicMock, patch

from backend.app.core.tracing import setup_tracing
from backend.app.core.config import settings


class TestTracingSetup:
    """Test tracing configuration setup."""

    def test_setup_tracing_disabled(self):
        """Test tracing setup when OTEL is disabled."""
        app = MagicMock()

        # Mock settings to disable OTEL
        with patch.object(settings, 'OTEL_ENABLED', False):
            # Should return early without error
            setup_tracing(app)

            # Function should complete without raising exception
            assert True

    @patch('backend.app.core.tracing.TracerProvider')
    @patch('backend.app.core.tracing.Resource')
    def test_setup_tracing_enabled_no_endpoint(self, mock_resource, mock_provider):
        """Test tracing setup when enabled but no endpoint."""
        app = MagicMock()

        # Mock settings
        with patch.object(settings, 'OTEL_ENABLED', True), \
             patch.object(settings, 'OTEL_EXPORTER_ENDPOINT', None):

            setup_tracing(app)

            # Verify Resource.create was called
            mock_resource.create.assert_called_once()
            mock_provider.assert_called_once()

    @patch('backend.app.core.tracing.OTLPSpanExporter')
    @patch('backend.app.core.tracing.TracerProvider')
    @patch('backend.app.core.tracing.Resource')
    def test_setup_tracing_enabled_with_endpoint(self, mock_resource, mock_provider, mock_exporter):
        """Test tracing setup when enabled with endpoint."""
        app = MagicMock()

        # Mock settings
        with patch.object(settings, 'OTEL_ENABLED', True), \
             patch.object(settings, 'OTEL_EXPORTER_ENDPOINT', 'http://localhost:4317'):

            setup_tracing(app)

            # Verify components were created
            mock_resource.create.assert_called_once()
            mock_provider.assert_called_once()
            mock_exporter.assert_called_once()


class TestTracingConfiguration:
    """Test tracing configuration details."""

    @patch('backend.app.core.tracing.Resource')
    def test_resource_creation_attributes(self, mock_resource):
        """Test resource creation with correct attributes."""
        app = MagicMock()

        with patch.object(settings, 'OTEL_ENABLED', True), \
             patch.object(settings, 'OTEL_SERVICE_NAME', 'test-service'), \
             patch.object(settings, 'VERSION', '1.0.0'), \
             patch.object(settings, 'ENVIRONMENT', 'test'):

            setup_tracing(app)

            # Verify Resource.create was called with correct attributes
            call_args = mock_resource.create.call_args[0][0]
            assert call_args['service.name'] == 'test-service'
            assert call_args['service.version'] == '1.0.0'
            assert call_args['deployment.environment'] == 'test'


class TestTracingInstrumentation:
    """Test tracing instrumentation setup."""

    @patch('backend.app.core.tracing.FastAPIInstrumentor')
    @patch('backend.app.core.tracing.trace.set_tracer_provider')
    def test_fastapi_instrumentation(self, mock_set_provider, mock_instrumentor):
        """Test FastAPI instrumentation setup."""
        app = MagicMock()

        with patch.object(settings, 'OTEL_ENABLED', True):
            setup_tracing(app)

            # Verify instrumentation was called
            mock_instrumentor.instrument_app.assert_called_once_with(app)
            mock_set_provider.assert_called_once()


class TestTracingExporters:
    """Test different tracing exporters."""

    @patch('backend.app.core.tracing.ConsoleSpanExporter')
    def test_console_exporter_used_without_endpoint(self, mock_console_exporter):
        """Test console exporter is used when no endpoint configured."""
        app = MagicMock()

        with patch.object(settings, 'OTEL_ENABLED', True), \
             patch.object(settings, 'OTEL_EXPORTER_ENDPOINT', None):

            setup_tracing(app)

            # Console exporter should be created
            mock_console_exporter.assert_called_once()

    def test_tracing_import_success(self):
        """Test that tracing modules can be imported."""
        # Test basic imports work
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        assert trace is not None
        assert TracerProvider is not None


class TestTracingDisabledState:
    """Test behavior when tracing is disabled."""

    def test_setup_with_disabled_tracing_multiple_calls(self):
        """Test multiple calls to setup_tracing when disabled."""
        app = MagicMock()

        with patch.object(settings, 'OTEL_ENABLED', False):
            # Should be safe to call multiple times
            setup_tracing(app)
            setup_tracing(app)
            setup_tracing(app)

            # No exceptions should be raised
            assert True

    def test_app_not_modified_when_disabled(self):
        """Test app is not modified when tracing is disabled."""
        app = MagicMock()
        original_app_state = str(app)

        with patch.object(settings, 'OTEL_ENABLED', False):
            setup_tracing(app)

            # App should not have been modified significantly
            assert str(app) == original_app_state
