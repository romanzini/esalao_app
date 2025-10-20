"""Waitlist management service."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from backend.app.db.models.booking import Booking, BookingStatus
from backend.app.db.models.waitlist import Waitlist, WaitlistPriority, WaitlistStatus
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.repositories.waitlist import WaitlistRepository
from backend.app.domain.scheduling.services.slot_service import SlotService

logger = logging.getLogger(__name__)


class WaitlistService:
    """Service for managing booking waitlists."""

    def __init__(
        self,
        waitlist_repository: WaitlistRepository,
        booking_repository: BookingRepository,
        user_repository: UserRepository,
        slot_service: SlotService,
    ):
        """Initialize waitlist service."""
        self.waitlist_repository = waitlist_repository
        self.booking_repository = booking_repository
        self.user_repository = user_repository
        self.slot_service = slot_service

    async def join_waitlist(
        self,
        client_id: int,
        professional_id: int,
        service_id: int,
        unit_id: int,
        preferred_datetime: datetime,
        flexibility_hours: int = 24,
        priority: WaitlistPriority = WaitlistPriority.NORMAL,
        notes: Optional[str] = None,
        notify_email: bool = True,
        notify_sms: bool = False,
        notify_push: bool = True,
    ) -> Waitlist:
        """
        Add client to waitlist for a specific slot/service.

        Args:
            client_id: ID of the client
            professional_id: ID of the professional
            service_id: ID of the service
            unit_id: ID of the unit
            preferred_datetime: Preferred appointment time
            flexibility_hours: Hours of flexibility around preferred time
            priority: Priority level in the queue
            notes: Additional notes or special requests
            notify_email: Send email notifications
            notify_sms: Send SMS notifications
            notify_push: Send push notifications

        Returns:
            Created waitlist entry

        Raises:
            ValueError: If validation fails
        """
        # Validate client exists
        client = await self.user_repository.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client not found: {client_id}")

        # Check if client is already on waitlist for this professional/service/time
        existing_entries = await self.waitlist_repository.list_by_client_id(
            client_id, active_only=True
        )

        for entry in existing_entries:
            if (
                entry.professional_id == professional_id
                and entry.service_id == service_id
                and abs((entry.preferred_datetime - preferred_datetime).total_seconds()) < 3600  # Within 1 hour
            ):
                raise ValueError(
                    "Client already on waitlist for this professional/service/time"
                )

        # Validate preferred time is in the future
        if preferred_datetime <= datetime.utcnow():
            raise ValueError("Preferred time must be in the future")

        # Create waitlist entry
        waitlist_entry = await self.waitlist_repository.create(
            client_id=client_id,
            professional_id=professional_id,
            service_id=service_id,
            unit_id=unit_id,
            preferred_datetime=preferred_datetime,
            flexibility_hours=flexibility_hours,
            priority=priority,
            notes=notes,
            notify_email=notify_email,
            notify_sms=notify_sms,
            notify_push=notify_push,
        )

        logger.info(
            f"Client {client_id} joined waitlist for professional {professional_id}, "
            f"service {service_id} at position {waitlist_entry.position}"
        )

        # TODO: Send notification to client about joining waitlist
        # await self._notify_waitlist_joined(waitlist_entry)

        return waitlist_entry

    async def leave_waitlist(
        self,
        waitlist_id: int,
        client_id: int,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Remove client from waitlist.

        Args:
            waitlist_id: ID of waitlist entry
            client_id: ID of the client (for validation)
            reason: Optional reason for leaving

        Returns:
            True if removed, False if not found

        Raises:
            ValueError: If validation fails
        """
        # Get waitlist entry
        entry = await self.waitlist_repository.get_by_id(waitlist_id)
        if not entry:
            raise ValueError(f"Waitlist entry not found: {waitlist_id}")

        # Validate client owns this entry
        if entry.client_id != client_id:
            raise ValueError("Client does not own this waitlist entry")

        # Can only leave if active or offered
        if entry.status not in [WaitlistStatus.ACTIVE, WaitlistStatus.OFFERED]:
            raise ValueError(f"Cannot leave waitlist with status: {entry.status}")

        # Cancel the entry
        success = await self.waitlist_repository.cancel_entry(
            waitlist_id, notes=reason
        )

        if success:
            logger.info(
                f"Client {client_id} left waitlist {waitlist_id}. Reason: {reason}"
            )
            # TODO: Send notification about leaving waitlist

        return success

    async def offer_slot_to_waitlist(
        self,
        professional_id: int,
        service_id: int,
        slot_start: datetime,
        slot_end: datetime,
        offer_duration_hours: int = 2,
    ) -> List[Dict]:
        """
        Offer an available slot to eligible waitlist entries.

        Args:
            professional_id: Professional ID
            service_id: Service ID
            slot_start: Start time of available slot
            slot_end: End time of available slot
            offer_duration_hours: How long client has to respond

        Returns:
            List of offers made with details

        Raises:
            ValueError: If validation fails
        """
        # Find eligible waitlist entries
        eligible_entries = await self.waitlist_repository.list_for_slot_offering(
            professional_id, service_id, slot_start, slot_end
        )

        if not eligible_entries:
            logger.info(
                f"No eligible waitlist entries for slot {slot_start} - {slot_end} "
                f"(professional {professional_id}, service {service_id})"
            )
            return []

        offers_made = []
        offer_expires_at = datetime.utcnow() + timedelta(hours=offer_duration_hours)

        # Offer to the first eligible entry (highest priority/lowest position)
        entry = eligible_entries[0]

        success = await self.waitlist_repository.offer_slot(
            entry.id, slot_start, slot_end, offer_expires_at
        )

        if success:
            offer_details = {
                "waitlist_id": entry.id,
                "client_id": entry.client_id,
                "slot_start": slot_start,
                "slot_end": slot_end,
                "offer_expires_at": offer_expires_at,
                "position": entry.position,
                "priority": entry.priority.value,
            }
            offers_made.append(offer_details)

            logger.info(
                f"Offered slot {slot_start} - {slot_end} to waitlist entry {entry.id} "
                f"(client {entry.client_id}, position {entry.position})"
            )

            # TODO: Send notification to client about slot offer
            # await self._notify_slot_offered(entry, slot_start, slot_end, offer_expires_at)

        return offers_made

    async def respond_to_offer(
        self,
        waitlist_id: int,
        client_id: int,
        accepted: bool,
        response_notes: Optional[str] = None,
    ) -> Optional[Booking]:
        """
        Process client's response to a slot offer.

        Args:
            waitlist_id: ID of waitlist entry
            client_id: ID of the client (for validation)
            accepted: Whether client accepted the offer
            response_notes: Optional response notes

        Returns:
            Created booking if accepted, None if declined

        Raises:
            ValueError: If validation fails
        """
        # Get waitlist entry
        entry = await self.waitlist_repository.get_by_id(waitlist_id, load_relationships=True)
        if not entry:
            raise ValueError(f"Waitlist entry not found: {waitlist_id}")

        # Validate client owns this entry
        if entry.client_id != client_id:
            raise ValueError("Client does not own this waitlist entry")

        # Validate entry has pending offer
        if not entry.has_pending_offer:
            raise ValueError("No pending offer for this waitlist entry")

        # Check if offer has expired
        if entry.is_offer_expired:
            # Auto-expire the offer
            await self.waitlist_repository.update_status(
                waitlist_id, WaitlistStatus.EXPIRED,
                responded_at=datetime.utcnow(),
                response_notes="Offer expired before response"
            )
            raise ValueError("Offer has expired")

        booking = None

        if accepted:
            # Create booking for the offered slot
            try:
                booking = await self.booking_repository.create(
                    client_id=client_id,
                    professional_id=entry.professional_id,
                    service_id=entry.service_id,
                    scheduled_at=entry.offered_slot_start,
                    duration_minutes=int((entry.offered_slot_end - entry.offered_slot_start).total_seconds() / 60),
                    service_price=float(entry.service.price) if entry.service else 0.0,
                    status=BookingStatus.CONFIRMED,
                    notes=f"Created from waitlist {waitlist_id}. {response_notes or ''}".strip(),
                )

                logger.info(
                    f"Created booking {booking.id} from waitlist {waitlist_id} "
                    f"for client {client_id}"
                )

                # Record acceptance with booking reference
                await self.waitlist_repository.respond_to_offer(
                    waitlist_id, accepted=True,
                    response_notes=response_notes,
                    booking_id=booking.id
                )

                # TODO: Send confirmation notification
                # await self._notify_offer_accepted(entry, booking)

            except Exception as e:
                logger.error(f"Failed to create booking from waitlist {waitlist_id}: {e}")
                # Record failed acceptance
                await self.waitlist_repository.respond_to_offer(
                    waitlist_id, accepted=False,
                    response_notes=f"Booking creation failed: {str(e)}"
                )
                raise ValueError(f"Failed to create booking: {str(e)}")

        else:
            # Record decline
            await self.waitlist_repository.respond_to_offer(
                waitlist_id, accepted=False, response_notes=response_notes
            )

            logger.info(
                f"Client {client_id} declined waitlist offer {waitlist_id}. "
                f"Reason: {response_notes}"
            )

            # Offer the slot to the next person in line
            await self._offer_to_next_in_line(entry)

            # TODO: Send decline notification
            # await self._notify_offer_declined(entry)

        return booking

    async def check_and_offer_cancelled_slot(
        self,
        cancelled_booking: Booking,
        offer_duration_hours: int = 2,
    ) -> List[Dict]:
        """
        Check if a cancelled/no-show booking can be offered to waitlist.

        Args:
            cancelled_booking: The cancelled or no-show booking
            offer_duration_hours: How long client has to respond

        Returns:
            List of offers made

        Raises:
            ValueError: If validation fails
        """
        if cancelled_booking.status not in [
            BookingStatus.CANCELLED,
            BookingStatus.NO_SHOW,
        ]:
            raise ValueError("Booking is not cancelled or no-show")

        # Calculate slot times
        slot_start = cancelled_booking.scheduled_at
        slot_end = slot_start + timedelta(minutes=cancelled_booking.duration_minutes)

        # Only offer if slot is still in the future
        if slot_start <= datetime.utcnow():
            logger.info(
                f"Cancelled slot {slot_start} is in the past, not offering to waitlist"
            )
            return []

        return await self.offer_slot_to_waitlist(
            professional_id=cancelled_booking.professional_id,
            service_id=cancelled_booking.service_id,
            slot_start=slot_start,
            slot_end=slot_end,
            offer_duration_hours=offer_duration_hours,
        )

    async def expire_old_offers(self, current_time: Optional[datetime] = None) -> int:
        """
        Expire offers that have passed their deadline and offer to next in line.

        Args:
            current_time: Current time (defaults to now)

        Returns:
            Number of expired offers
        """
        if current_time is None:
            current_time = datetime.utcnow()

        # Get entries with expired offers before updating
        expired_entries = []

        # Find entries that should be expired
        entries_with_offers = await self.waitlist_repository.list_by_professional_id(
            professional_id=-1, active_only=False  # Get all professionals
        )

        for entry in entries_with_offers:
            if (
                entry.status == WaitlistStatus.OFFERED
                and entry.offer_expires_at
                and entry.offer_expires_at <= current_time
            ):
                expired_entries.append(entry)

        # Expire the offers
        count = await self.waitlist_repository.expire_old_offers(current_time)

        # For each expired offer, try to offer to next in line
        for entry in expired_entries:
            if entry.offered_slot_start and entry.offered_slot_end:
                await self._offer_to_next_in_line(entry)

        if count > 0:
            logger.info(f"Expired {count} old waitlist offers")

        return count

    async def get_client_waitlist_status(
        self, client_id: int, active_only: bool = True
    ) -> List[Dict]:
        """
        Get waitlist status for a client.

        Args:
            client_id: Client ID
            active_only: Only return active entries

        Returns:
            List of waitlist entries with position and status
        """
        entries = await self.waitlist_repository.list_by_client_id(
            client_id, active_only
        )

        status_list = []
        for entry in entries:
            # Get current queue position
            position = await self.waitlist_repository.get_queue_position(entry.id)

            status_info = {
                "waitlist_id": entry.id,
                "professional_id": entry.professional_id,
                "professional_name": entry.professional.name if entry.professional else "Unknown",
                "service_id": entry.service_id,
                "service_name": entry.service.name if entry.service else "Unknown",
                "preferred_datetime": entry.preferred_datetime,
                "flexibility_hours": entry.flexibility_hours,
                "status": entry.status.value,
                "current_position": position,
                "joined_at": entry.joined_at,
                "notes": entry.notes,
            }

            # Add offer details if applicable
            if entry.has_pending_offer:
                status_info.update({
                    "offered_slot_start": entry.offered_slot_start,
                    "offered_slot_end": entry.offered_slot_end,
                    "offer_expires_at": entry.offer_expires_at,
                    "offered_at": entry.offered_at,
                })

            status_list.append(status_info)

        return status_list

    async def get_professional_waitlist(
        self, professional_id: int, active_only: bool = True
    ) -> List[Dict]:
        """
        Get waitlist entries for a professional.

        Args:
            professional_id: Professional ID
            active_only: Only return active entries

        Returns:
            List of waitlist entries with client details
        """
        entries = await self.waitlist_repository.list_by_professional_id(
            professional_id, active_only
        )

        waitlist_info = []
        for entry in entries:
            entry_info = {
                "waitlist_id": entry.id,
                "client_id": entry.client_id,
                "client_name": entry.client.name if entry.client else "Unknown",
                "service_id": entry.service_id,
                "service_name": entry.service.name if entry.service else "Unknown",
                "preferred_datetime": entry.preferred_datetime,
                "flexibility_hours": entry.flexibility_hours,
                "status": entry.status.value,
                "priority": entry.priority.value,
                "position": entry.position,
                "joined_at": entry.joined_at,
                "notes": entry.notes,
            }

            # Add offer details if applicable
            if entry.has_pending_offer:
                entry_info.update({
                    "offered_slot_start": entry.offered_slot_start,
                    "offered_slot_end": entry.offered_slot_end,
                    "offer_expires_at": entry.offer_expires_at,
                })

            waitlist_info.append(entry_info)

        return waitlist_info

    async def get_waitlist_statistics(
        self,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
        unit_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        Get waitlist statistics.

        Args:
            professional_id: Filter by professional
            service_id: Filter by service
            unit_id: Filter by unit
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            Dictionary with waitlist statistics
        """
        return await self.waitlist_repository.get_statistics(
            professional_id=professional_id,
            service_id=service_id,
            unit_id=unit_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def _offer_to_next_in_line(self, expired_entry: Waitlist) -> List[Dict]:
        """
        Offer expired slot to the next person in line.

        Args:
            expired_entry: The waitlist entry that had an expired offer

        Returns:
            List of new offers made
        """
        if not expired_entry.offered_slot_start or not expired_entry.offered_slot_end:
            return []

        # Check if the slot is still available (not in the past)
        if expired_entry.offered_slot_start <= datetime.utcnow():
            return []

        return await self.offer_slot_to_waitlist(
            professional_id=expired_entry.professional_id,
            service_id=expired_entry.service_id,
            slot_start=expired_entry.offered_slot_start,
            slot_end=expired_entry.offered_slot_end,
            offer_duration_hours=2,  # Default 2 hour offer window
        )
