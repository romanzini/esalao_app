"""Professional repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.professional import Professional


class ProfessionalRepository:
    """Repository for Professional model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        user_id: int,
        salon_id: int,
        specialties: str | None = None,
        bio: str | None = None,
        commission_rate: float = 0.0,
    ) -> Professional:
        """
        Create a new professional.

        Args:
            user_id: ID of the user account
            salon_id: ID of the salon
            specialties: Optional specialties description
            bio: Optional biography
            commission_rate: Commission rate (0.0-1.0)

        Returns:
            Created Professional instance
        """
        professional = Professional(
            user_id=user_id,
            salon_id=salon_id,
            specialties=specialties,
            bio=bio,
            commission_rate=commission_rate,
        )

        self.session.add(professional)
        await self.session.commit()
        await self.session.refresh(professional)

        return professional

    async def get_by_id(self, professional_id: int, load_relationships: bool = False) -> Professional | None:
        """
        Get professional by ID.

        Args:
            professional_id: Professional ID
            load_relationships: Whether to eagerly load user, salon, availabilities

        Returns:
            Professional instance or None if not found
        """
        stmt = select(Professional).where(Professional.id == professional_id)

        if load_relationships:
            stmt = stmt.options(
                selectinload(Professional.user),
                selectinload(Professional.salon),
                selectinload(Professional.availabilities),
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: int) -> Professional | None:
        """
        Get professional by user ID.

        Args:
            user_id: User ID

        Returns:
            Professional instance or None if not found
        """
        stmt = select(Professional).where(Professional.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_salon_id(self, salon_id: int) -> list[Professional]:
        """
        List all professionals in a salon.

        Args:
            salon_id: Salon ID

        Returns:
            List of Professional instances
        """
        stmt = (
            select(Professional)
            .where(Professional.salon_id == salon_id)
            .options(selectinload(Professional.user))
            .order_by(Professional.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        professional_id: int,
        **fields,
    ) -> Professional | None:
        """
        Update professional fields.

        Args:
            professional_id: Professional ID
            **fields: Fields to update

        Returns:
            Updated Professional instance or None if not found
        """
        professional = await self.get_by_id(professional_id)
        if not professional:
            return None

        for key, value in fields.items():
            if hasattr(professional, key):
                setattr(professional, key, value)

        await self.session.commit()
        await self.session.refresh(professional)

        return professional

    async def delete(self, professional_id: int) -> bool:
        """
        Delete a professional.

        Args:
            professional_id: Professional ID

        Returns:
            True if deleted, False if not found
        """
        professional = await self.get_by_id(professional_id)
        if not professional:
            return False

        await self.session.delete(professional)
        await self.session.commit()

        return True

    async def exists_by_id(self, professional_id: int) -> bool:
        """
        Check if professional exists by ID.

        Args:
            professional_id: Professional ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Professional.id).where(Professional.id == professional_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_user_id(self, user_id: int) -> bool:
        """
        Check if professional exists by user ID.

        Args:
            user_id: User ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Professional.id).where(Professional.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
