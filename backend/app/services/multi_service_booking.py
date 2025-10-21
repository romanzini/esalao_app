"""Multi-service booking business logic service."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.multi_service_booking import MultiServiceBooking, MultiServiceBookingStatus
from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.service import Service
from backend.app.db.repositories.multi_service_booking import MultiServiceBookingRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.service import ServiceRepository
from backend.app.domain.scheduling.services.slot_service import SlotService

logger = logging.getLogger(__name__)


class MultiServiceBookingService:
    """Service for managing multi-service booking operations."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session."""
        self.session = session
        self.multi_booking_repo = MultiServiceBookingRepository(session)
        self.booking_repo = BookingRepository(session)
        self.service_repo = ServiceRepository(session)
        self.slot_service = SlotService(session)

    async def check_package_availability(
        self,
        services_data: List[Dict],
        max_gap_minutes: int = 30
    ) -> Dict:
        """
        Check availability for a package of services.

        Args:
            services_data: List of service requests with service_id, professional_id, scheduled_at
            max_gap_minutes: Maximum allowed gap between services

        Returns:
            Dictionary with availability information
        """
        try:
            conflicts = []
            suggested_times = []
            total_price = 0.0
            total_duration = 0

            # Validate each service individually
            for i, service_data in enumerate(services_data):
                service_id = service_data.get("service_id")
                professional_id = service_data.get("professional_id")
                scheduled_at = service_data.get("scheduled_at")

                # Get service details
                service = await self.service_repo.get_by_id(service_id)
                if not service:
                    conflicts.append(f"Service {service_id} not found")
                    continue

                # Check slot availability
                is_available = await self.slot_service.is_slot_available(
                    professional_id=professional_id,
                    start_time=scheduled_at,
                    duration_minutes=service.duration_minutes
                )

                if not is_available:
                    conflicts.append(f"Service {i+1} slot not available at {scheduled_at}")

                    # Try to find alternative
                    alternatives = await self.slot_service.find_available_slots(
                        professional_id=professional_id,
                        date=scheduled_at.date(),
                        duration_minutes=service.duration_minutes,
                        limit=3
                    )

                    if alternatives:
                        suggested_time = alternatives[0]["start_time"]
                    else:
                        suggested_time = scheduled_at
                else:
                    suggested_time = scheduled_at

                suggested_times.append({
                    "service_id": service_id,
                    "professional_id": professional_id,
                    "service_name": service.name,
                    "suggested_time": suggested_time,
                    "duration_minutes": service.duration_minutes,
                    "price": float(service.price)
                })

                total_price += float(service.price)
                total_duration += service.duration_minutes

            # Check gaps between services
            if len(suggested_times) > 1:
                for i in range(1, len(suggested_times)):
                    prev_service = suggested_times[i-1]
                    curr_service = suggested_times[i]

                    prev_end = prev_service["suggested_time"] + timedelta(minutes=prev_service["duration_minutes"])
                    curr_start = curr_service["suggested_time"]

                    gap_minutes = (curr_start - prev_end).total_seconds() / 60

                    if gap_minutes < 0:
                        conflicts.append(f"Services {i} and {i+1} overlap")
                    elif gap_minutes > max_gap_minutes:
                        conflicts.append(f"Gap between services {i} and {i+1} is {gap_minutes:.0f} minutes (max: {max_gap_minutes})")

            return {
                "is_available": len(conflicts) == 0,
                "suggested_times": suggested_times,
                "total_duration_minutes": total_duration,
                "total_price": total_price,
                "conflicts": conflicts,
                "package_start": suggested_times[0]["suggested_time"] if suggested_times else None,
                "package_end": (
                    suggested_times[-1]["suggested_time"] +
                    timedelta(minutes=suggested_times[-1]["duration_minutes"])
                ) if suggested_times else None
            }

        except Exception as e:
            logger.error(f"Error checking package availability: {str(e)}")
            raise

    async def create_multi_service_booking(
        self,
        client_id: int,
        package_name: str,
        services_data: List[Dict],
        package_notes: Optional[str] = None
    ) -> MultiServiceBooking:
        """
        Create a multi-service booking with individual service bookings.

        Args:
            client_id: ID of the client
            package_name: Name for the service package
            services_data: List of service data
            package_notes: Optional notes for the package

        Returns:
            Created MultiServiceBooking instance
        """
        try:
            # First, check availability
            availability = await self.check_package_availability(services_data)

            if not availability["is_available"]:
                raise ValueError(f"Package not available: {', '.join(availability['conflicts'])}")

            # Get the primary professional (most common one or first one)
            professional_ids = [s["professional_id"] for s in services_data]
            primary_professional_id = max(set(professional_ids), key=professional_ids.count)

            # Calculate package timing and pricing
            starts_at = availability["package_start"]
            ends_at = availability["package_end"]
            total_price = availability["total_price"]
            total_duration = availability["total_duration_minutes"]

            # Create the multi-service booking
            multi_booking = await self.multi_booking_repo.create(
                client_id=client_id,
                primary_professional_id=primary_professional_id,
                package_name=package_name,
                total_price=total_price,
                total_duration_minutes=total_duration,
                starts_at=starts_at,
                ends_at=ends_at,
                notes=package_notes,
                status=MultiServiceBookingStatus.PENDING
            )

            # Create individual bookings
            individual_bookings = []
            for service_data in availability["suggested_times"]:
                service = await self.service_repo.get_by_id(service_data["service_id"])

                # Create individual booking
                booking = await self.booking_repo.create(
                    client_id=client_id,
                    professional_id=service_data["professional_id"],
                    service_id=service_data["service_id"],
                    scheduled_at=service_data["suggested_time"],
                    duration_minutes=service_data["duration_minutes"],
                    service_price=service_data["price"],
                    status=BookingStatus.PENDING,
                    notes=service_data.get("notes")
                )

                # Link to multi-service booking
                await self.multi_booking_repo.add_individual_booking(multi_booking.id, booking)
                individual_bookings.append(booking)

            # Update the services count
            multi_booking.total_services_count = len(individual_bookings)
            await self.session.flush()

            logger.info(f"Created multi-service booking {multi_booking.id} with {len(individual_bookings)} services")
            return multi_booking

        except Exception as e:
            logger.error(f"Error creating multi-service booking: {str(e)}")
            await self.session.rollback()
            raise

    async def confirm_multi_service_booking(self, multi_booking_id: int) -> MultiServiceBooking:
        """
        Confirm a multi-service booking and all its individual bookings.

        Args:
            multi_booking_id: ID of the multi-service booking

        Returns:
            Updated MultiServiceBooking instance
        """
        try:
            multi_booking = await self.multi_booking_repo.get_by_id(multi_booking_id)
            if not multi_booking:
                raise ValueError("Multi-service booking not found")

            if multi_booking.status != MultiServiceBookingStatus.PENDING:
                raise ValueError(f"Cannot confirm booking in status: {multi_booking.status}")

            # Confirm all individual bookings
            for booking in multi_booking.individual_bookings:
                if booking.status == BookingStatus.PENDING:
                    booking.status = BookingStatus.CONFIRMED
                    booking.updated_at = datetime.utcnow()

            # Update multi-service booking status
            await self.multi_booking_repo.update_status(
                multi_booking_id,
                MultiServiceBookingStatus.CONFIRMED
            )

            await self.session.flush()
            logger.info(f"Confirmed multi-service booking {multi_booking_id}")

            return await self.multi_booking_repo.get_by_id(multi_booking_id)

        except Exception as e:
            logger.error(f"Error confirming multi-service booking {multi_booking_id}: {str(e)}")
            raise

    async def cancel_multi_service_booking(
        self,
        multi_booking_id: int,
        cancellation_reason: str,
        cancelled_by_id: int,
        partial_cancel: bool = False
    ) -> MultiServiceBooking:
        """
        Cancel a multi-service booking.

        Args:
            multi_booking_id: ID of the multi-service booking
            cancellation_reason: Reason for cancellation
            cancelled_by_id: ID of user who cancelled
            partial_cancel: Whether to allow partial cancellation

        Returns:
            Updated MultiServiceBooking instance
        """
        try:
            multi_booking = await self.multi_booking_repo.get_by_id(multi_booking_id)
            if not multi_booking:
                raise ValueError("Multi-service booking not found")

            if not multi_booking.can_be_cancelled:
                raise ValueError(f"Cannot cancel booking in status: {multi_booking.status}")

            cancelled_count = 0
            total_count = len(multi_booking.individual_bookings)

            # Cancel individual bookings that can be cancelled
            for booking in multi_booking.individual_bookings:
                if booking.status in (BookingStatus.PENDING, BookingStatus.CONFIRMED):
                    booking.status = BookingStatus.CANCELLED
                    booking.cancellation_reason = cancellation_reason
                    booking.cancelled_at = datetime.utcnow()
                    booking.cancelled_by_id = cancelled_by_id
                    booking.updated_at = datetime.utcnow()
                    cancelled_count += 1
                elif booking.status == BookingStatus.CANCELLED:
                    cancelled_count += 1

            # Determine new status
            if cancelled_count == total_count:
                new_status = MultiServiceBookingStatus.CANCELLED
            elif cancelled_count > 0 and partial_cancel:
                new_status = MultiServiceBookingStatus.PARTIALLY_CANCELLED
            else:
                raise ValueError("Cannot partially cancel booking without partial_cancel=True")

            # Update multi-service booking
            await self.multi_booking_repo.update_status(
                multi_booking_id,
                new_status,
                cancellation_reason,
                cancelled_by_id
            )

            await self.session.flush()
            logger.info(f"Cancelled multi-service booking {multi_booking_id} (status: {new_status})")

            return await self.multi_booking_repo.get_by_id(multi_booking_id)

        except Exception as e:
            logger.error(f"Error cancelling multi-service booking {multi_booking_id}: {str(e)}")
            raise

    async def update_individual_booking_status(
        self,
        booking_id: int,
        new_status: BookingStatus
    ) -> Tuple[Booking, MultiServiceBooking]:
        """
        Update individual booking status and recalculate package status.

        Args:
            booking_id: ID of the individual booking
            new_status: New status for the booking

        Returns:
            Tuple of (updated booking, updated multi-service booking)
        """
        try:
            # Get the individual booking
            booking = await self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise ValueError("Booking not found")

            if not booking.multi_service_booking_id:
                raise ValueError("Booking is not part of a multi-service package")

            # Update individual booking
            booking.status = new_status
            booking.updated_at = datetime.utcnow()

            if new_status == BookingStatus.COMPLETED:
                booking.completed_at = datetime.utcnow()

            await self.session.flush()

            # Recalculate and update multi-service booking status
            await self.multi_booking_repo.calculate_and_update_status(booking.multi_service_booking_id)

            # Get updated multi-service booking
            multi_booking = await self.multi_booking_repo.get_by_id(booking.multi_service_booking_id)

            logger.info(f"Updated booking {booking_id} status to {new_status}, package status: {multi_booking.status}")

            return booking, multi_booking

        except Exception as e:
            logger.error(f"Error updating individual booking {booking_id} status: {str(e)}")
            raise

    async def get_package_suggestions(
        self,
        client_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        duration_preference: Optional[str] = None  # "short", "medium", "long"
    ) -> List[Dict]:
        """
        Get popular package combinations and suggestions.

        Args:
            client_id: Optional client ID for personalized suggestions
            professional_id: Optional professional ID to filter by
            duration_preference: Preferred package duration

        Returns:
            List of suggested packages
        """
        try:
            # This would typically analyze historical data
            # For now, return some common combinations

            suggestions = [
                {
                    "name": "Complete Hair Package",
                    "description": "Haircut, wash, and styling",
                    "estimated_duration": 120,
                    "estimated_price": 150.0,
                    "popularity_score": 95,
                    "services": ["Haircut", "Hair Wash", "Hair Styling"]
                },
                {
                    "name": "Nail Care Package",
                    "description": "Manicure and pedicure combo",
                    "estimated_duration": 90,
                    "estimated_price": 80.0,
                    "popularity_score": 87,
                    "services": ["Manicure", "Pedicure"]
                },
                {
                    "name": "Relaxation Package",
                    "description": "Massage and facial treatment",
                    "estimated_duration": 150,
                    "estimated_price": 200.0,
                    "popularity_score": 78,
                    "services": ["Swedish Massage", "Facial Treatment"]
                }
            ]

            # Filter by duration preference
            if duration_preference:
                if duration_preference == "short":
                    suggestions = [s for s in suggestions if s["estimated_duration"] <= 90]
                elif duration_preference == "medium":
                    suggestions = [s for s in suggestions if 90 < s["estimated_duration"] <= 150]
                elif duration_preference == "long":
                    suggestions = [s for s in suggestions if s["estimated_duration"] > 150]

            return sorted(suggestions, key=lambda x: x["popularity_score"], reverse=True)

        except Exception as e:
            logger.error(f"Error getting package suggestions: {str(e)}")
            raise

    async def calculate_package_discount(
        self,
        services_data: List[Dict],
        discount_percentage: float = 10.0
    ) -> Dict:
        """
        Calculate potential discount for booking multiple services.

        Args:
            services_data: List of service data
            discount_percentage: Discount percentage to apply

        Returns:
            Dictionary with pricing information
        """
        try:
            total_individual_price = 0.0
            service_details = []

            for service_data in services_data:
                service = await self.service_repo.get_by_id(service_data["service_id"])
                if service:
                    total_individual_price += float(service.price)
                    service_details.append({
                        "service_id": service.id,
                        "name": service.name,
                        "individual_price": float(service.price)
                    })

            discount_amount = total_individual_price * (discount_percentage / 100)
            package_price = total_individual_price - discount_amount

            return {
                "total_individual_price": total_individual_price,
                "discount_percentage": discount_percentage,
                "discount_amount": discount_amount,
                "package_price": package_price,
                "savings": discount_amount,
                "service_details": service_details
            }

        except Exception as e:
            logger.error(f"Error calculating package discount: {str(e)}")
            raise
