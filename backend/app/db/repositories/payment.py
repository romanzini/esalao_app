"""Payment repository module."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal

from backend.app.db.models.payment import Payment


class PaymentRepository:
    """Repository for payment operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment_data: dict) -> Payment:
        """Create a new payment record."""
        payment = Payment(**payment_data)
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_booking_id(self, booking_id: int) -> List[Payment]:
        """Get all payments for a booking."""
        result = await self.session.execute(
            select(Payment).where(Payment.booking_id == booking_id)
        )
        return list(result.scalars().all())

    async def update(self, payment_id: int, payment_data: dict) -> Optional[Payment]:
        """Update payment record."""
        payment = await self.get_by_id(payment_id)
        if payment:
            for key, value in payment_data.items():
                setattr(payment, key, value)
            await self.session.commit()
            await self.session.refresh(payment)
        return payment

    async def delete(self, payment_id: int) -> bool:
        """Delete payment record."""
        payment = await self.get_by_id(payment_id)
        if payment:
            await self.session.delete(payment)
            await self.session.commit()
            return True
        return False
