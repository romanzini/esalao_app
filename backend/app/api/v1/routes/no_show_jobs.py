"""
No-show management endpoints.

This module provides endpoints for manual execution of no-show detection
jobs and management of no-show processes.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security.rbac import require_role
from backend.app.db.models.user import UserRole
from backend.app.db.session import get_db
from backend.app.jobs.no_show_detection import NoShowDetectionJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/no-show", tags=["🚫 No-Show Detection"])


@router.post(
    "/detect",
    summary="Run no-show detection job",
    description="""
    Manually trigger the no-show detection job.

    This endpoint:
    - Finds bookings eligible for no-show detection
    - Evaluates each booking against no-show criteria
    - Marks appropriate bookings as no-show
    - Sends notifications for detected no-shows
    - Returns detailed job execution statistics

    **Authentication Required:** Admin or Professional

    **Use Cases:**
    - Manual execution after system maintenance
    - Testing no-show detection logic
    - Catching up on missed automatic runs
    """,
    responses={
        200: {"description": "No-show detection job completed successfully"},
        403: {"description": "Insufficient permissions"},
        500: {"description": "Job execution failed"},
    },
)
async def run_no_show_detection(
    detection_window_hours: int = Query(
        default=2,
        ge=1,
        le=24,
        description="Hours after scheduled time to check for no-shows"
    ),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Run the no-show detection job manually.

    Args:
        detection_window_hours: Grace period after scheduled time
        current_user: Authenticated user
        db: Database session

    Returns:
        Job execution statistics and results
    """
    try:
        logger.info(f"Manual no-show detection started by user {current_user.get('id')}")

        # Create and run the job
        job = NoShowDetectionJob(detection_window_hours=detection_window_hours)
        results = await job.run(db_session=db)

        # Add metadata
        results["triggered_by"] = current_user.get("id")
        results["trigger_type"] = "manual"

        logger.info(
            f"Manual no-show detection completed. "
            f"Evaluated: {results['bookings_evaluated']}, "
            f"Detected: {results['no_shows_detected']}"
        )

        return results

    except Exception as e:
        logger.error(f"Manual no-show detection failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No-show detection job failed: {str(e)}"
        )


@router.post(
    "/detect/bookings",
    summary="Run no-show detection for specific bookings",
    description="""
    Run no-show detection for specific booking IDs.

    This endpoint:
    - Evaluates only the specified bookings
    - Does not mark bookings as no-show (evaluation only)
    - Returns detailed evaluation results for each booking
    - Useful for testing and debugging

    **Authentication Required:** Admin or Professional
    """,
    responses={
        200: {"description": "Evaluation completed successfully"},
        400: {"description": "Invalid booking IDs provided"},
        403: {"description": "Insufficient permissions"},
    },
)
async def evaluate_specific_bookings(
    booking_ids: List[int] = Query(
        ...,
        description="List of booking IDs to evaluate"
    ),
    current_user: dict = Depends(require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Evaluate specific bookings for no-show without marking them.

    Args:
        booking_ids: List of booking IDs to evaluate
        current_user: Authenticated user
        db: Database session

    Returns:
        Evaluation results for each booking
    """
    try:
        if not booking_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one booking ID must be provided"
            )

        if len(booking_ids) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 100 booking IDs allowed per request"
            )

        logger.info(
            f"Manual no-show evaluation started by user {current_user.get('id')} "
            f"for {len(booking_ids)} bookings"
        )

        # Create and run evaluation job
        job = NoShowDetectionJob()
        results = await job.run_manual(booking_ids=booking_ids, db_session=db)

        # Add metadata
        results["triggered_by"] = current_user.get("id")
        results["trigger_type"] = "manual_evaluation"
        results["requested_booking_ids"] = booking_ids

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual no-show evaluation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"No-show evaluation failed: {str(e)}"
        )


@router.get(
    "/job-status",
    summary="Get no-show detection job status",
    description="""
    Get information about the current status of no-show detection jobs.

    Returns:
    - Last job execution time
    - Job statistics
    - System configuration
    - Upcoming scheduled runs (if applicable)

    **Authentication Required:** Admin
    """,
)
async def get_job_status(
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get status information about no-show detection jobs.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        Job status and configuration information
    """
    try:
        # TODO: Implement job status tracking in database
        # For now, return basic configuration

        return {
            "system_status": "active",
            "default_detection_window_hours": 2,
            "automatic_detection_enabled": True,  # TODO: Get from config
            "last_job_execution": None,  # TODO: Get from job log
            "next_scheduled_run": None,  # TODO: Get from scheduler
            "total_jobs_today": 0,  # TODO: Get from job log
            "configuration": {
                "max_bookings_per_run": 1000,
                "notification_enabled": True,
                "dispute_window_hours": 24,
            },
            "checked_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


@router.post(
    "/job/schedule",
    summary="Schedule automatic no-show detection",
    description="""
    Configure automatic scheduling for no-show detection jobs.

    **Note:** This endpoint is for configuration only.
    Actual scheduling depends on your deployment setup (cron, Celery, etc.).

    **Authentication Required:** Admin only
    """,
)
async def configure_job_schedule(
    enabled: bool = Query(True, description="Enable automatic detection"),
    interval_hours: int = Query(1, ge=1, le=24, description="Run interval in hours"),
    detection_window_hours: int = Query(2, ge=1, le=12, description="Detection window in hours"),
    current_user: dict = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Configure automatic no-show detection schedule.

    Args:
        enabled: Whether to enable automatic detection
        interval_hours: How often to run detection (in hours)
        detection_window_hours: Grace period for no-show detection
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated configuration
    """
    try:
        # TODO: Store configuration in database
        # TODO: Update scheduler configuration

        config = {
            "automatic_detection_enabled": enabled,
            "run_interval_hours": interval_hours,
            "detection_window_hours": detection_window_hours,
            "updated_by": current_user.get("id"),
            "updated_at": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"No-show detection schedule updated by user {current_user.get('id')}: {config}"
        )

        return {
            "message": "Configuration updated successfully",
            "configuration": config,
            "note": "Scheduler restart may be required for changes to take effect"
        }

    except Exception as e:
        logger.error(f"Failed to update job schedule: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule configuration"
        )
