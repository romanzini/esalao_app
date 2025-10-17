# eSalão Platform

Beauty Salon Marketplace Platform - Backend API

## Overview

eSalão is a comprehensive marketplace platform connecting beauty salons with customers, providing scheduling, payments, loyalty programs, and analytics.

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL 15 with SQLAlchemy 2
- **Cache/Queue**: Redis
- **Task Queue**: Celery
- **Observability**: OpenTelemetry, Prometheus, Sentry
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/romanzini/esalao_app.git
cd esalao_app
```

2. Copy environment variables:
```bash
cp .env.example .env
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
docker-compose exec api alembic upgrade head
```

5. Access the API:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Local Development (without Docker)

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .[dev]
```

3. Start PostgreSQL and Redis locally or via Docker:
```bash
docker-compose up -d db redis
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the API:
```bash
uvicorn backend.app.main:app --reload
```

## Project Structure

```
esalao_app/
├── backend/
│   └── app/
│       ├── api/            # API routes and endpoints
│       ├── core/           # Core configurations (config, security, logging)
│       ├── db/             # Database models and repositories
│       ├── domain/         # Domain logic (auth, scheduling, payments)
│       └── workers/        # Celery tasks
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
├── alembic/               # Database migrations
├── docker-compose.yml     # Docker services
├── Dockerfile             # Application container
└── pyproject.toml         # Project metadata and dependencies
```

## Phase 1 Status

**Version**: v1.0.0-phase1-partial  
**Last Updated**: 2025-01-22

### Test Coverage
- **Bookings**: 12/12 (100%) ✅
- **Rate Limiting**: 2/2 (100%) ✅
- **Scheduling**: 5/5 (100%) ✅
- **Integration Tests**: 48/89 (54%)
- **Overall Coverage**: 51.60%

### Recent Achievements
- ✅ Model relationships fixed (eager loading functional)
- ✅ RBAC fixtures complete (CLIENT, PROFESSIONAL, ADMIN roles)
- ✅ Deprecation warnings eliminated (0 warnings)
- ✅ Rate limiting implemented (3/min register, 5/min login - SEC-002)
- ✅ Technical review completed (83.25/100 - B+ rating)

### Pending Tasks
- ⏳ Performance baseline testing (PER-001)
- ⏳ Integration test fixtures (18 errors to resolve)
- ⏳ Coverage improvement (51.60% → 80% target)
- ⏳ Auth flow validation (23 failed tests)

See `TECHNICAL_REVIEW_REPORT.md` for detailed gap analysis.

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=backend/app --cov-report=html
```

Run specific test types:
```bash
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest tests/e2e/          # E2E tests only
```

## Code Quality

Format code:
```bash
black backend/ tests/
```

Lint code:
```bash
ruff check backend/ tests/
```

Type check:
```bash
mypy backend/
```

Run all checks:
```bash
pre-commit run --all-files
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback one migration:
```bash
alembic downgrade -1
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Observability

- **Metrics**: http://localhost:8000/metrics (Prometheus format)
- **Health Check**: http://localhost:8000/health
- **Logs**: Structured JSON logs to stdout

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key (change in production!)
- `ENVIRONMENT`: development/staging/production
- `DEBUG`: Enable debug mode
- `OTEL_ENABLED`: Enable OpenTelemetry tracing
- `SENTRY_DSN`: Sentry error tracking DSN

## Contributing

1. Create a feature branch from `main`
2. Make your changes following code quality standards
3. Write tests for new functionality
4. Ensure all tests pass and coverage is maintained
5. Submit a pull request

## License

[Add license information]

## Support

For issues and questions, please use the GitHub issue tracker.
