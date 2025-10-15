"""Application configuration using Pydantic settings."""

from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "eSalão Platform"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = Field(default=False)

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: int = Field(default=5432)
    POSTGRES_USER: str = Field(default="esalao_user")
    POSTGRES_PASSWORD: str = Field(default="esalao_pass")
    POSTGRES_DB: str = Field(default="esalao_db")
    DATABASE_URL: PostgresDsn | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> str:
        """Build database URL from components if not explicitly provided."""
        if isinstance(v, str):
            return v

        values = info.data
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_SERVER"),
                port=values.get("POSTGRES_PORT"),
                path=values.get("POSTGRES_DB", ""),
            )
        )

    # Redis
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: str | None = None
    REDIS_URL: RedisDsn | None = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: str | None, info) -> str:
        """Build Redis URL from components if not explicitly provided."""
        if isinstance(v, str):
            return v

        values = info.data
        password_part = f":{values.get('REDIS_PASSWORD')}@" if values.get("REDIS_PASSWORD") else ""

        return str(
            RedisDsn.build(
                scheme="redis",
                host=f"{password_part}{values.get('REDIS_HOST')}",
                port=values.get("REDIS_PORT"),
                path=str(values.get("REDIS_DB", 0)),
            )
        )

    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-secrets-manager"
    )

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Legacy token fields (deprecated, use JWT_* instead)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    ALGORITHM: str = "HS256"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # Observability
    OTEL_ENABLED: bool = Field(default=False)
    OTEL_SERVICE_NAME: str = "esalao-api"
    OTEL_EXPORTER_ENDPOINT: str | None = None

    SENTRY_DSN: str | None = None
    SENTRY_ENABLED: bool = Field(default=False)

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def set_celery_broker(cls, v: str | None, info) -> str:
        """Use Redis URL as Celery broker if not explicitly set."""
        if v:
            return v
        redis_url = info.data.get("REDIS_URL", "redis://localhost:6379/0")
        return str(redis_url) if redis_url else "redis://localhost:6379/0"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def set_celery_backend(cls, v: str | None, info) -> str:
        """Use Redis URL as Celery result backend if not explicitly set."""
        if v:
            return v
        redis_url = info.data.get("REDIS_URL", "redis://localhost:6379/0")
        return str(redis_url) if redis_url else "redis://localhost:6379/0"


settings = Settings()
