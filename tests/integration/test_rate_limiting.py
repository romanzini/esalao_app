"""Test rate limiting on authentication endpoints."""

import asyncio

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    """Test that login endpoint has rate limiting (5/min)."""

    # Wait a bit to ensure clean state
    await asyncio.sleep(0.5)

    credentials = {
        "email": "nonexistent_ratelimit@test.com",
        "password": "wrongpass",
    }

    responses = []
    for _ in range(6):
        response = await client.post("/v1/auth/login", json=credentials)
        responses.append(response.status_code)
        await asyncio.sleep(0.05)  # Small delay between requests

    # At least one should be rate limited (429)
    assert 429 in responses, f"Expected at least one 429 in responses, got {responses}"


@pytest.mark.asyncio
async def test_rate_limit_behavior(client: AsyncClient):
    """
    Test that rate limiting returns proper 429 status code.

    This test validates the rate limiting mechanism works correctly
    by making rapid requests to an auth endpoint.
    """
    # Wait to clear previous test's rate limit
    await asyncio.sleep(1.5)

    # Make 7 rapid requests to login endpoint (limit is 5/min)
    responses = []
    for _ in range(7):
        response = await client.post(
            "/v1/auth/login",
            json={"email": "spam@test.com", "password": "pass"},
        )
        responses.append(response.status_code)
        await asyncio.sleep(0.05)

    # Should have at least one rate limit response
    assert 429 in responses, f"Expected 429 in responses, got {responses}"

    # Count how many were rate limited
    rate_limited = responses.count(429)
    assert rate_limited >= 1, f"Expected at least 1 rate limited request, got {rate_limited}"


