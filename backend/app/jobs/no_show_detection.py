"""
No-show detection background job.

This module provides automated no-show detection and processing
for bookings that have passed their scheduled time.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.services.no_show import NoShowService
from backend.app.services.booking_notifications import BookingNotificationService

logger = logging.getLogger(__name__)


class NoShowDetectionJob:
    """Background job for automated no-show detection."""

    def __init__(self, detection_window_hours: int = 2):
        """
        Initialize no-show detection job.

        Args:
            detection_window_hours: How many hours after scheduled time to check for no-shows
        """
        self.detection_window_hours = detection_window_hours

    async def run(self, db_session: Optional[AsyncSession] = None) -> Dict:
        """
        Execute the no-show detection job.

        This method:
        1. Finds bookings eligible for no-show detection
        2. Evaluates each booking for no-show criteria
        3. Marks appropriate bookings as no-show
        4. Sends notifications for detected no-shows
        5. Returns summary of actions taken

        Args:
            db_session: Optional database session (for testing)

        Returns:
            Dict with job execution results and statistics
        """
        start_time = datetime.utcnow()

        # Use provided session or get new one
        if db_session:
            session = db_session
            should_close = False
        else:
            session = await get_db().__anext__()
            should_close = True

        try:
            logger.info(f"Starting no-show detection job at {start_time}")

            # Initialize services
            booking_repo = BookingRepository(session)
            user_repo = UserRepository(session)
            no_show_service = NoShowService(booking_repo, user_repo)
            notification_service = BookingNotificationService(session)

            # Get job statistics
            stats = {
                "job_start_time": start_time,
                "bookings_evaluated": 0,
                "no_shows_detected": 0,
                "notifications_sent": 0,
                "errors": [],
                "processing_time_seconds": 0,
            }

            # Find bookings eligible for no-show detection
            eligible_bookings = await self._find_eligible_bookings(
                booking_repo,
                current_time=start_time
            )

            logger.info(f"Found {len(eligible_bookings)} bookings eligible for no-show evaluation")

            # Process each booking
            for booking in eligible_bookings:
                try:
                    stats["bookings_evaluated"] += 1

                    # Evaluate booking for no-show
                    evaluation = await no_show_service.evaluate_booking_for_no_show(
                        booking_id=booking.id,
                        current_time=start_time
                    )

                    # If booking should be marked as no-show
                    if evaluation.should_mark_no_show:
                        logger.info(f"Marking booking {booking.id} as no-show: {evaluation.reason}")

                        # Mark as no-show
                        updated_booking = await no_show_service.mark_booking_no_show(
                            booking_id=booking.id,
                            reason=evaluation.reason,
                            marked_by_id=None,  # System-generated
                            marked_at=start_time,
                            no_show_fee=evaluation.calculated_fee,
                        )

                        stats["no_shows_detected"] += 1

                        # Send no-show notification
                        try:
                            await notification_service.notify_no_show_detected(
                                booking_id=booking.id,
                                reason=evaluation.reason.value,
                                fee_amount=evaluation.calculated_fee,
                                correlation_id=f"auto_no_show_{booking.id}_{start_time.isoformat()}"
                            )
                            stats["notifications_sent"] += 1

                        except Exception as e:
                            error_msg = f"Failed to send no-show notification for booking {booking.id}: {str(e)}"
                            logger.error(error_msg)
                            stats["errors"].append(error_msg)

                    else:
                        logger.debug(f"Booking {booking.id} does not meet no-show criteria")

                except Exception as e:
                    error_msg = f"Error processing booking {booking.id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # Commit changes
            await session.commit()

            # Calculate processing time
            end_time = datetime.utcnow()
            stats["processing_time_seconds"] = (end_time - start_time).total_seconds()
            stats["job_end_time"] = end_time

            logger.info(
                f"No-show detection job completed. "
                f"Evaluated: {stats['bookings_evaluated']}, "
                f"Detected: {stats['no_shows_detected']}, "
                f"Errors: {len(stats['errors'])}, "
                f"Time: {stats['processing_time_seconds']:.2f}s"
            )

            return stats

        except Exception as e:
            await session.rollback()
            error_msg = f"No-show detection job failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        finally:
            if should_close:
                await session.close()

    async def _find_eligible_bookings(
        self,
        booking_repo: BookingRepository,
        current_time: datetime
    ) -> List:
        """
        Find bookings eligible for no-show detection.

        Criteria:
        - Status is CONFIRMED or IN_PROGRESS
        - Scheduled time is in the past (plus grace period)
        - Not already marked as no-show
        - Not cancelled or completed

        Args:
            booking_repo: Booking repository
            current_time: Current timestamp

        Returns:
            List of booking objects eligible for evaluation
        """
        # Calculate cutoff time (scheduled_at + grace period)
        cutoff_time = current_time - timedelta(hours=self.detection_window_hours)

        # Use repository method to find eligible bookings
        try:
            eligible_bookings = await booking_repo.find_eligible_for_no_show_detection(
                cutoff_time=cutoff_time,
                limit=1000  # Process max 1000 bookings per run
            )

            return eligible_bookings

        except AttributeError:
            # If method doesn't exist, fall back to basic query
            logger.warning("find_eligible_for_no_show_detection method not found, using fallback")
            return await self._fallback_find_eligible_bookings(booking_repo, cutoff_time)

    async def _fallback_find_eligible_bookings(
        self,
        booking_repo: BookingRepository,
        cutoff_time: datetime
    ) -> List:
        """
        Fallback method to find eligible bookings using basic repository methods.

        Args:
            booking_repo: Booking repository
            cutoff_time: Cutoff time for eligibility

        Returns:
            List of eligible bookings
        """
        # This is a simplified fallback - in practice you'd need to implement
        # the proper query in the BookingRepository
        try:
            # Get recent bookings and filter manually
            recent_bookings = await booking_repo.get_recent_bookings(
                hours_back=24,  # Look at last 24 hours
                limit=1000
            )

            eligible = []
            for booking in recent_bookings:
                # Check basic eligibility criteria
                if (booking.scheduled_at < cutoff_time and
                    booking.status in ["confirmed", "in_progress"] and
                    not booking.marked_no_show_at and
                    booking.status not in ["cancelled", "completed"]):
                    eligible.append(booking)

            return eligible

        except Exception as e:
            logger.error(f"Fallback booking search failed: {str(e)}")
            return []

    async def run_manual(
        self,
        booking_ids: Optional[List[int]] = None,
        db_session: Optional[AsyncSession] = None
    ) -> Dict:
        """
        Run no-show detection manually for specific bookings.

        Args:
            booking_ids: Optional list of specific booking IDs to check
            db_session: Optional database session

        Returns:
            Dict with execution results
        """
        start_time = datetime.utcnow()

        # Use provided session or get new one
        if db_session:
            session = db_session
            should_close = False
        else:
            session = await get_db().__anext__()
            should_close = True

        try:
            logger.info(f"Starting manual no-show detection at {start_time}")

            # Initialize services
            booking_repo = BookingRepository(session)
            user_repo = UserRepository(session)
            no_show_service = NoShowService(booking_repo, user_repo)

            stats = {
                "job_start_time": start_time,
                "bookings_evaluated": 0,
                "no_shows_detected": 0,
                "errors": [],
                "booking_results": {},
            }

            # Get specific bookings or use detection logic
            if booking_ids:
                bookings = []
                for booking_id in booking_ids:
                    booking = await booking_repo.get_by_id(booking_id)
                    if booking:
                        bookings.append(booking)
                    else:
                        stats["errors"].append(f"Booking {booking_id} not found")
            else:
                # Use regular detection logic
                bookings = await self._find_eligible_bookings(booking_repo, start_time)

            # Process each booking
            for booking in bookings:
                try:
                    stats["bookings_evaluated"] += 1

                    # Run evaluation
                    evaluation = await no_show_service.evaluate_booking_for_no_show(
                        booking_id=booking.id,
                        current_time=start_time
                    )

                    stats["booking_results"][booking.id] = {
                        "should_mark": evaluation.should_mark_no_show,
                        "reason": evaluation.reason.value if evaluation.reason else None,
                        "fee": float(evaluation.calculated_fee),
                    }

                    if evaluation.should_mark_no_show:
                        stats["no_shows_detected"] += 1

                except Exception as e:
                    error_msg = f"Error evaluating booking {booking.id}: {str(e)}"
                    stats["errors"].append(error_msg)
                    stats["booking_results"][booking.id] = {"error": error_msg}

            end_time = datetime.utcnow()
            stats["processing_time_seconds"] = (end_time - start_time).total_seconds()
            stats["job_end_time"] = end_time

            return stats

        finally:
            if should_close:
                await session.close()


class NoShowDetectionScheduler:
    """Scheduler for automated no-show detection jobs."""

    @staticmethod
    async def schedule_hourly_detection():
        """Schedule no-show detection to run every hour."""
        # This would integrate with your chosen scheduler (Celery, APScheduler, etc.)
        # For now, this is just a placeholder
        job = NoShowDetectionJob(detection_window_hours=1)
        return await job.run()

    @staticmethod
    async def schedule_daily_cleanup():
        """Schedule daily cleanup of old no-show records."""
        # Placeholder for cleanup job
        pass
