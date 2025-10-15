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

COPY pyproject.toml ./
RUN pip install --user --no-cache-dir -e .[dev]

# Stage 3: Runtime image
FROM base as runtime

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
