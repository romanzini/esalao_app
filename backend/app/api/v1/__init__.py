"""API v1 package."""

from fastapi import APIRouter

from backend.app.api.v1.routes import auth

api_router = APIRouter(prefix="/v1")

# Include route modules
api_router.include_router(auth.router)

__all__ = ["api_router"]
