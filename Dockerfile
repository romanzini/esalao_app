# Multi-stage Dockerfile for eSalão Platform

# Stage 1: Base Python image with system dependencies
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        postgresql-client \
        && rm -rf /var/lib/apt/lists/*

# Stage 2: Builder - install dependencies
FROM base as builder

# Install setuptools for editable installs
RUN pip install --no-cache-dir setuptools wheel

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Stage 3: Runtime image
FROM base as runtime

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user BEFORE copying application code
RUN useradd -m -u 1000 appuser

# Copy application code
COPY --chown=appuser:appuser backend/ ./backend/
COPY --chown=appuser:appuser alembic/ ./alembic/
COPY --chown=appuser:appuser alembic.ini ./

# Switch to non-root user
USER appuser

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
