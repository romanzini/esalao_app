"""Tests for metrics collection."""

import pytest
from unittest.mock import MagicMock, patch
from starlette.requests import Request
from starlette.responses import Response

from backend.app.core.metrics import (
    PrometheusMiddleware,
    http_requests_total,
    http_request_duration_seconds,
    registry
)


class TestPrometheusMetrics:
    """Test Prometheus metrics collection."""

    def test_registry_creation(self):
        """Test that registry is created."""
        assert registry is not None

    def test_metrics_counters_exist(self):
        """Test that metric counters are defined."""
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None

    def test_prometheus_middleware_init(self):
        """Test PrometheusMiddleware initialization."""
        app = MagicMock()
        middleware = PrometheusMiddleware(app)

        assert middleware.app == app

    @pytest.mark.asyncio
    async def test_middleware_dispatch(self):
        """Test middleware dispatch functionality."""
        app = MagicMock()
        middleware = PrometheusMiddleware(app)

        # Mock request
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url.path = "/test"

        # Mock call_next
        async def call_next(request):
            response = MagicMock(spec=Response)
            response.status_code = 200
            return response

        # Call dispatch
        response = await middleware.dispatch(request, call_next)

        # Verify response
        assert response.status_code == 200


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""

    def test_metrics_generation(self):
        """Test metrics can be generated."""
        from prometheus_client import generate_latest

        # Generate metrics
        metrics_data = generate_latest(registry)

        # Verify it's bytes
        assert isinstance(metrics_data, bytes)
        assert len(metrics_data) > 0


class TestMetricsLabels:
    """Test metrics labeling."""

    def test_http_requests_total_labels(self):
        """Test HTTP requests total has correct labels."""
        # Get metric description
        assert 'method' in http_requests_total._labelnames
        assert 'endpoint' in http_requests_total._labelnames
        assert 'status_code' in http_requests_total._labelnames

    def test_http_duration_labels(self):
        """Test HTTP duration has correct labels."""
        assert 'method' in http_request_duration_seconds._labelnames
        assert 'endpoint' in http_request_duration_seconds._labelnames


class TestMetricsCollection:
    """Test actual metrics collection."""

    def test_counter_increment(self):
        """Test counter can be incremented."""
        # Get initial value
        before = http_requests_total.labels(
            method='GET',
            endpoint='/test',
            status_code='200'
        )._value._value

        # Increment counter
        http_requests_total.labels(
            method='GET',
            endpoint='/test',
            status_code='200'
        ).inc()

        # Check increment
        after = http_requests_total.labels(
            method='GET',
            endpoint='/test',
            status_code='200'
        )._value._value

        assert after > before

    def test_histogram_observe(self):
        """Test histogram can observe values."""
        # Observe a value
        http_request_duration_seconds.labels(
            method='POST',
            endpoint='/api/test'
        ).observe(0.5)

        # Just verify no exception occurred
        assert True
