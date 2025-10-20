"""Waitlist repository for database operations."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.waitlist import Waitlist, WaitlistPriority, WaitlistStatus


class WaitlistRepository:
    """Repository for Waitlist model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
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
        Create a new waitlist entry.

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
            Created Waitlist instance
        """
        # Get next position in queue for this professional/service
        position = await self._get_next_position(professional_id, service_id)

        waitlist = Waitlist(
            client_id=client_id,
            professional_id=professional_id,
            service_id=service_id,
            unit_id=unit_id,
            preferred_datetime=preferred_datetime,
            flexibility_hours=flexibility_hours,
            priority=priority,
            position=position,
            notes=notes,
            notify_email=notify_email,
            notify_sms=notify_sms,
            notify_push=notify_push,
        )

        self.session.add(waitlist)
        await self.session.commit()
        await self.session.refresh(waitlist)

        return waitlist

    async def get_by_id(self, waitlist_id: int, load_relationships: bool = False) -> Optional[Waitlist]:
        """
        Get waitlist entry by ID.

        Args:
            waitlist_id: Waitlist ID
            load_relationships: Whether to load related objects

        Returns:
            Waitlist instance or None if not found
        """
        stmt = select(Waitlist).where(Waitlist.id == waitlist_id)

        if load_relationships:
            stmt = stmt.options(
                selectinload(Waitlist.client),
                selectinload(Waitlist.professional),
                selectinload(Waitlist.service),
                selectinload(Waitlist.unit),
                selectinload(Waitlist.booking),
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_client_id(self, client_id: int, active_only: bool = True) -> List[Waitlist]:
        """
        Get all waitlist entries for a client.

        Args:
            client_id: Client ID
            active_only: Only return active entries

        Returns:
            List of waitlist entries
        """
        stmt = select(Waitlist).where(Waitlist.client_id == client_id)

        if active_only:
            stmt = stmt.where(
                Waitlist.status.in_([WaitlistStatus.ACTIVE, WaitlistStatus.OFFERED])
            )

        stmt = stmt.options(
            selectinload(Waitlist.professional),
            selectinload(Waitlist.service),
            selectinload(Waitlist.unit),
        ).order_by(Waitlist.joined_at.desc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_professional_id(
        self,
        professional_id: int,
        active_only: bool = True
    ) -> List[Waitlist]:
        """
        Get all waitlist entries for a professional.

        Args:
            professional_id: Professional ID
            active_only: Only return active entries

        Returns:
            List of waitlist entries ordered by priority and position
        """
        stmt = select(Waitlist).where(Waitlist.professional_id == professional_id)

        if active_only:
            stmt = stmt.where(
                Waitlist.status.in_([WaitlistStatus.ACTIVE, WaitlistStatus.OFFERED])
            )

        stmt = stmt.options(
            selectinload(Waitlist.client),
            selectinload(Waitlist.service),
            selectinload(Waitlist.unit),
        ).order_by(
            Waitlist.priority.desc(),  # Higher priority first
            Waitlist.position.asc(),   # Lower position number first
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_for_slot_offering(
        self,
        professional_id: int,
        service_id: int,
        slot_start: datetime,
        slot_end: datetime,
    ) -> List[Waitlist]:
        """
        Get waitlist entries that could be offered a specific slot.

        Args:
            professional_id: Professional ID
            service_id: Service ID
            slot_start: Start time of available slot
            slot_end: End time of available slot

        Returns:
            List of eligible waitlist entries ordered by priority and position
        """
        # Calculate time window conditions
        slot_datetime = slot_start

        stmt = select(Waitlist).where(
            and_(
                Waitlist.professional_id == professional_id,
                Waitlist.service_id == service_id,
                Waitlist.status == WaitlistStatus.ACTIVE,
                # Check if slot falls within client's acceptable time window
                or_(
                    # Exact match
                    Waitlist.preferred_datetime == slot_datetime,
                    # Within flexibility window
                    and_(
                        Waitlist.preferred_datetime >= slot_start - func.make_interval(hours=Waitlist.flexibility_hours / 2),
                        Waitlist.preferred_datetime <= slot_end + func.make_interval(hours=Waitlist.flexibility_hours / 2),
                    )
                )
            )
        ).options(
            selectinload(Waitlist.client),
            selectinload(Waitlist.service),
        ).order_by(
            Waitlist.priority.desc(),  # Higher priority first
            Waitlist.position.asc(),   # Lower position number first
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        waitlist_id: int,
        status: WaitlistStatus,
        **additional_fields
    ) -> bool:
        """
        Update waitlist status and additional fields.

        Args:
            waitlist_id: Waitlist ID
            status: New status
            **additional_fields: Additional fields to update

        Returns:
            True if updated, False if not found
        """
        update_data = {"status": status, **additional_fields}

        stmt = update(Waitlist).where(
            Waitlist.id == waitlist_id
        ).values(**update_data)

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0

    async def offer_slot(
        self,
        waitlist_id: int,
        slot_start: datetime,
        slot_end: datetime,
        offer_expires_at: datetime,
    ) -> bool:
        """
        Mark waitlist entry as offered with slot details.

        Args:
            waitlist_id: Waitlist ID
            slot_start: Start time of offered slot
            slot_end: End time of offered slot
            offer_expires_at: When the offer expires

        Returns:
            True if updated, False if not found
        """
        return await self.update_status(
            waitlist_id,
            WaitlistStatus.OFFERED,
            offered_at=datetime.utcnow(),
            offered_slot_start=slot_start,
            offered_slot_end=slot_end,
            offer_expires_at=offer_expires_at,
        )

    async def respond_to_offer(
        self,
        waitlist_id: int,
        accepted: bool,
        response_notes: Optional[str] = None,
        booking_id: Optional[int] = None,
    ) -> bool:
        """
        Record client's response to slot offer.

        Args:
            waitlist_id: Waitlist ID
            accepted: Whether client accepted the offer
            response_notes: Optional response notes
            booking_id: ID of created booking if accepted

        Returns:
            True if updated, False if not found
        """
        status = WaitlistStatus.ACCEPTED if accepted else WaitlistStatus.DECLINED

        update_data = {
            "responded_at": datetime.utcnow(),
            "response_notes": response_notes,
        }

        if booking_id:
            update_data["booking_id"] = booking_id

        return await self.update_status(waitlist_id, status, **update_data)

    async def cancel_entry(
        self,
        waitlist_id: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Cancel a waitlist entry and reposition remaining entries.

        Args:
            waitlist_id: Waitlist ID
            notes: Optional cancellation notes

        Returns:
            True if cancelled, False if not found
        """
        # Get the entry to cancel
        entry = await self.get_by_id(waitlist_id)
        if not entry:
            return False

        # Update status
        await self.update_status(
            waitlist_id,
            WaitlistStatus.CANCELLED,
            response_notes=notes,
            responded_at=datetime.utcnow(),
        )

        # Reposition remaining entries in the same queue
        await self._reposition_queue(
            entry.professional_id,
            entry.service_id,
            removed_position=entry.position
        )

        return True

    async def expire_old_offers(self, current_time: Optional[datetime] = None) -> int:
        """
        Expire offers that have passed their deadline.

        Args:
            current_time: Current time (defaults to now)

        Returns:
            Number of expired offers
        """
        if current_time is None:
            current_time = datetime.utcnow()

        stmt = update(Waitlist).where(
            and_(
                Waitlist.status == WaitlistStatus.OFFERED,
                Waitlist.offer_expires_at <= current_time,
            )
        ).values(
            status=WaitlistStatus.EXPIRED,
            responded_at=current_time,
            response_notes="Offer expired automatically",
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def get_queue_position(self, waitlist_id: int) -> Optional[int]:
        """
        Get current queue position for a waitlist entry.

        Args:
            waitlist_id: Waitlist ID

        Returns:
            Current position in queue or None if not found
        """
        entry = await self.get_by_id(waitlist_id)
        if not entry or not entry.is_active:
            return None

        # Count entries ahead in the same professional/service queue
        stmt = select(func.count(Waitlist.id)).where(
            and_(
                Waitlist.professional_id == entry.professional_id,
                Waitlist.service_id == entry.service_id,
                Waitlist.status == WaitlistStatus.ACTIVE,
                or_(
                    Waitlist.priority > entry.priority,
                    and_(
                        Waitlist.priority == entry.priority,
                        Waitlist.position < entry.position,
                    )
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one() + 1  # +1 because position is 1-based

    async def get_statistics(
        self,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
        unit_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
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
        # Build base conditions
        conditions = []

        if professional_id:
            conditions.append(Waitlist.professional_id == professional_id)
        if service_id:
            conditions.append(Waitlist.service_id == service_id)
        if unit_id:
            conditions.append(Waitlist.unit_id == unit_id)
        if start_date:
            conditions.append(Waitlist.joined_at >= start_date)
        if end_date:
            conditions.append(Waitlist.joined_at <= end_date)

        # Get total counts by status
        base_stmt = select(Waitlist)
        if conditions:
            base_stmt = base_stmt.where(and_(*conditions))

        # Count by status
        status_counts = {}
        for status in WaitlistStatus:
            stmt = select(func.count(Waitlist.id)).select_from(
                base_stmt.where(Waitlist.status == status).subquery()
            )
            result = await self.session.execute(stmt)
            status_counts[status.value] = result.scalar_one()

        # Average wait time for completed entries
        completed_stmt = base_stmt.where(
            Waitlist.status.in_([
                WaitlistStatus.ACCEPTED,
                WaitlistStatus.DECLINED,
                WaitlistStatus.EXPIRED,
            ])
        )

        avg_wait_stmt = select(
            func.avg(
                func.extract('epoch', Waitlist.responded_at - Waitlist.joined_at) / 3600
            )
        ).select_from(completed_stmt.subquery())

        result = await self.session.execute(avg_wait_stmt)
        avg_wait_hours = result.scalar_one() or 0

        return {
            "total_entries": sum(status_counts.values()),
            "status_breakdown": status_counts,
            "active_entries": status_counts.get("active", 0),
            "pending_offers": status_counts.get("offered", 0),
            "conversion_rate": (
                status_counts.get("accepted", 0) / max(1, sum(status_counts.values()) - status_counts.get("active", 0)) * 100
            ),
            "average_wait_hours": round(avg_wait_hours, 2),
        }

    async def delete(self, waitlist_id: int) -> bool:
        """
        Delete waitlist entry.

        Args:
            waitlist_id: Waitlist ID

        Returns:
            True if deleted, False if not found
        """
        stmt = delete(Waitlist).where(Waitlist.id == waitlist_id)
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0

    async def _get_next_position(self, professional_id: int, service_id: int) -> int:
        """Get next position in queue for professional/service combination."""
        stmt = select(func.coalesce(func.max(Waitlist.position), 0) + 1).where(
            and_(
                Waitlist.professional_id == professional_id,
                Waitlist.service_id == service_id,
                Waitlist.status == WaitlistStatus.ACTIVE,
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def _reposition_queue(
        self,
        professional_id: int,
        service_id: int,
        removed_position: int
    ) -> None:
        """Reposition queue entries after a removal."""
        # Move all entries with position > removed_position up by 1
        stmt = update(Waitlist).where(
            and_(
                Waitlist.professional_id == professional_id,
                Waitlist.service_id == service_id,
                Waitlist.status == WaitlistStatus.ACTIVE,
                Waitlist.position > removed_position,
            )
        ).values(position=Waitlist.position - 1)

        await self.session.execute(stmt)
        await self.session.commit()
