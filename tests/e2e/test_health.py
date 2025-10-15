"""Health endpoint E2E tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Test that health endpoint returns 200 OK."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_returns_expected_structure():
    """Test that health endpoint returns expected JSON structure."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()

    assert "status" in data
    assert "service" in data
    assert "version" in data

    assert data["status"] == "healthy"
    assert data["service"] == "eSalão Platform"
    assert data["version"] == "0.1.0"
