"""API v1 package."""

from fastapi import APIRouter

from backend.app.api.v1.routes import auth, bookings, professionals, scheduling, services

api_router = APIRouter(prefix="/v1")

# Include route modules
api_router.include_router(auth.router)
api_router.include_router(scheduling.router)
api_router.include_router(bookings.router)
api_router.include_router(professionals.router)
api_router.include_router(services.router)

__all__ = ["api_router"]
