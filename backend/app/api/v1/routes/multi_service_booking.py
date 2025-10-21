"""Multi-service booking routes configuration."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints.multi_service_booking import router as multi_service_booking_router

router = APIRouter()
router.include_router(
    multi_service_booking_router,
    prefix="/multi-service-bookings",
    tags=["multi-service-bookings"]
)
