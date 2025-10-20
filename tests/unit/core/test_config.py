"""Tests for configuration module."""

import os
from unittest.mock import patch

from backend.app.core.config import Settings


class TestSettings:
    """Test Settings configuration class."""

    def test_settings_creation(self):
        """Test basic settings creation."""
        settings = Settings()

        # Check default values are set
        assert hasattr(settings, 'PROJECT_NAME')
        assert hasattr(settings, 'DEBUG')
        assert settings.PROJECT_NAME == "eSalão Platform"

    @patch.dict('os.environ', {'PROJECT_NAME': 'Test App'})
    def test_settings_from_env(self):
        """Test settings load from environment variables."""
        settings = Settings()
        assert settings.PROJECT_NAME == "Test App"

    @patch.dict('os.environ', {'DEBUG': 'true'})
    def test_debug_setting_true(self):
        """Test debug setting from environment."""
        settings = Settings()
        assert settings.DEBUG is True

    @patch.dict('os.environ', {'DEBUG': 'false'})
    def test_debug_setting_false(self):
        """Test debug setting false from environment."""
        settings = Settings()
        assert settings.DEBUG is False

    def test_database_url_format(self):
        """Test database URL is properly formatted."""
        settings = Settings()

        # Should have database URL
        assert hasattr(settings, 'DATABASE_URL')

        # Should be properly formatted
        if settings.DATABASE_URL:
            assert 'postgresql' in str(settings.DATABASE_URL)

    def test_redis_url_format(self):
        """Test Redis URL format."""
        settings = Settings()

        # Should have Redis URL
        assert hasattr(settings, 'REDIS_URL')

        # Should be properly formatted
        if settings.REDIS_URL:
            assert 'redis://' in str(settings.REDIS_URL)

    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_production_environment(self):
        """Test production environment setting."""
        settings = Settings()
        assert settings.ENVIRONMENT == "production"

    @patch.dict('os.environ', {'ENVIRONMENT': 'development'})
    def test_development_environment(self):
        """Test development environment setting."""
        settings = Settings()
        assert settings.ENVIRONMENT == "development"

    def test_jwt_settings_exist(self):
        """Test JWT configuration exists."""
        settings = Settings()

        assert hasattr(settings, 'JWT_SECRET_KEY')
        assert hasattr(settings, 'JWT_ALGORITHM')
        assert hasattr(settings, 'JWT_ACCESS_TOKEN_EXPIRE_MINUTES')

    def test_cors_settings_exist(self):
        """Test CORS configuration exists."""
        settings = Settings()

        assert hasattr(settings, 'BACKEND_CORS_ORIGINS')

        # Should have default CORS origins
        assert isinstance(settings.BACKEND_CORS_ORIGINS, list)

    def test_rate_limit_settings(self):
        """Test rate limiting configuration."""
        settings = Settings()

        assert hasattr(settings, 'RATE_LIMIT_ENABLED')
        assert hasattr(settings, 'RATE_LIMIT_PER_MINUTE')

    def test_settings_repr(self):
        """Test settings string representation."""
        settings = Settings()
        settings_str = str(settings)

        # Should contain project name
        assert 'project_name' in settings_str.lower() or settings.PROJECT_NAME in settings_str
