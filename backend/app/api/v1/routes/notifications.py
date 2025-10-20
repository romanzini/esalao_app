"""
Notification routes.

This module provides FastAPI routes for notification management including
user preferences, template management, sending notifications, and delivery tracking.
"""

from fastapi import APIRouter

from backend.app.api.v1.endpoints.notifications import router as notifications_router


router = APIRouter()

# Include notification endpoints with prefix
router.include_router(
    notifications_router,
    prefix="/notifications",
    tags=["notifications"],
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"}
    }
)
