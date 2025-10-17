"""Scheduling endpoints for slot availability and booking management."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.domain.scheduling.schemas import SlotResponse
from backend.app.domain.scheduling.services.slot_service import SlotService

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


@router.get(
    "/slots",
    response_model=SlotResponse,
    summary="Get available time slots",
    description="""
    Calculate and return available time slots for a professional on a specific date.

    This endpoint:
    - Retrieves the professional's availability schedule
    - Checks existing bookings to avoid conflicts
    - Returns a list of available time slots based on service duration

    **Query Parameters:**
    - `professional_id`: The ID of the professional
    - `date`: The date to check availability (ISO format: YYYY-MM-DD)
    - `service_id`: The ID of the service to book
    - `slot_interval_minutes`: Optional interval between slots (default: 30 minutes)

    **Example Request:**
    ```
    GET /v1/scheduling/slots?professional_id=1&date=2025-10-20&service_id=1
    ```

    **Example Response:**
    ```json
    {
      "professional_id": 1,
      "date": "2025-10-20",
      "service_id": 1,
      "service_duration_minutes": 60,
      "slots": [
        {
          "start_time": "2025-10-20T09:00:00",
          "end_time": "2025-10-20T10:00:00",
          "available": true
        },
        {
          "start_time": "2025-10-20T10:00:00",
          "end_time": "2025-10-20T11:00:00",
          "available": true
        }
      ],
      "total_slots": 2
    }
    ```
    """,
    responses={
        200: {
            "description": "Successfully retrieved available slots",
            "content": {
                "application/json": {
                    "example": {
                        "professional_id": 1,
                        "date": "2025-10-20",
                        "service_id": 1,
                        "service_duration_minutes": 60,
                        "slots": [
                            {
                                "start_time": "2025-10-20T09:00:00",
                                "end_time": "2025-10-20T10:00:00",
                                "available": True,
                            }
                        ],
                        "total_slots": 1,
                    }
                }
            },
        },
        404: {
            "description": "Service not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Service with ID 999 not found"}
                }
            },
        },
        422: {
            "description": "Validation error - invalid parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["query", "professional_id"],
                                "msg": "ensure this value is greater than 0",
                                "type": "value_error.number.not_gt",
                            }
                        ]
                    }
                }
            },
        },
    },
)
async def get_available_slots(
    professional_id: int = Query(
        ...,
        gt=0,
        description="ID of the professional",
        examples=[1],
    ),
    date: date = Query(
        ...,
        description="Date to check availability (ISO format: YYYY-MM-DD)",
        examples=["2025-10-20"],
    ),
    service_id: int = Query(
        ...,
        gt=0,
        description="ID of the service to book",
        examples=[1],
    ),
    slot_interval_minutes: int = Query(
        30,
        gt=0,
        le=120,
        description="Interval between slot start times in minutes (default: 30)",
        examples=[30],
    ),
    session: AsyncSession = Depends(get_db),
) -> SlotResponse:
    """
    Get available time slots for a professional on a specific date.

    Args:
        professional_id: ID of the professional
        date: Date to check availability
        service_id: ID of the service
        slot_interval_minutes: Interval between slots (default: 30 minutes)
        session: Database session

    Returns:
        SlotResponse with available time slots

    Raises:
        HTTPException: 404 if service not found
    """
    slot_service = SlotService(session)

    try:
        slots_response = await slot_service.calculate_available_slots(
            professional_id=professional_id,
            target_date=date,
            service_id=service_id,
            slot_interval_minutes=slot_interval_minutes,
        )

        return slots_response

    except ValueError as e:
        # Service not found or other validation error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
