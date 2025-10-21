"""
Review routes.

This module provides FastAPI routes for review management including
creating reviews, moderation, rating statistics, and review analytics.
"""

from fastapi import APIRouter

from backend.app.api.v1.endpoints.review import router as review_router


router = APIRouter()

# Include review endpoints with prefix
router.include_router(
    review_router,
    responses={
        404: {"description": "Not found"},
        422: {"description": "Validation error"}
    }
)
