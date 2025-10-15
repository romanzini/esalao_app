"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure async test backend."""
    return "asyncio"
