"""Salon repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.salon import Salon


class SalonRepository:
    """Repository for Salon model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        owner_id: int,
        name: str,
        description: str | None,
        address: str,
        city: str,
        state: str,
        zip_code: str,
        phone: str,
        email: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Salon:
        """
        Create a new salon.

        Args:
            owner_id: ID of the salon owner (User)
            name: Salon name
            description: Optional salon description
            address: Street address
            city: City name
            state: State code
            zip_code: ZIP/postal code
            phone: Contact phone
            email: Optional contact email
            latitude: Optional GPS latitude
            longitude: Optional GPS longitude

        Returns:
            Created Salon instance
        """
        salon = Salon(
            owner_id=owner_id,
            name=name,
            description=description,
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            phone=phone,
            email=email,
            latitude=latitude,
            longitude=longitude,
        )

        self.session.add(salon)
        await self.session.commit()
        await self.session.refresh(salon)

        return salon

    async def get_by_id(self, salon_id: int, load_relationships: bool = False) -> Salon | None:
        """
        Get salon by ID.

        Args:
            salon_id: Salon ID
            load_relationships: Whether to eagerly load professionals and services

        Returns:
            Salon instance or None if not found
        """
        stmt = select(Salon).where(Salon.id == salon_id)

        if load_relationships:
            stmt = stmt.options(
                selectinload(Salon.professionals),
                selectinload(Salon.services),
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_owner_id(self, owner_id: int) -> list[Salon]:
        """
        Get all salons owned by a user.

        Args:
            owner_id: Owner user ID

        Returns:
            List of Salon instances
        """
        stmt = select(Salon).where(Salon.owner_id == owner_id).order_by(Salon.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_city(self, city: str, state: str | None = None) -> list[Salon]:
        """
        List salons by city and optionally state.

        Args:
            city: City name
            state: Optional state code

        Returns:
            List of Salon instances
        """
        stmt = select(Salon).where(Salon.city.ilike(f"%{city}%"))

        if state:
            stmt = stmt.where(Salon.state == state)

        stmt = stmt.order_by(Salon.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        salon_id: int,
        **fields,
    ) -> Salon | None:
        """
        Update salon fields.

        Args:
            salon_id: Salon ID
            **fields: Fields to update

        Returns:
            Updated Salon instance or None if not found
        """
        salon = await self.get_by_id(salon_id)
        if not salon:
            return None

        for key, value in fields.items():
            if hasattr(salon, key):
                setattr(salon, key, value)

        await self.session.commit()
        await self.session.refresh(salon)

        return salon

    async def delete(self, salon_id: int) -> bool:
        """
        Delete a salon.

        Args:
            salon_id: Salon ID

        Returns:
            True if deleted, False if not found
        """
        salon = await self.get_by_id(salon_id)
        if not salon:
            return False

        await self.session.delete(salon)
        await self.session.commit()

        return True

    async def exists_by_id(self, salon_id: int) -> bool:
        """
        Check if salon exists by ID.

        Args:
            salon_id: Salon ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Salon.id).where(Salon.id == salon_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
