"""Service repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.models.service import Service


class ServiceRepository:
    """Repository for Service model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        salon_id: int,
        name: str,
        description: str | None,
        duration_minutes: int,
        price: float,
        category: str | None = None,
    ) -> Service:
        """
        Create a new service.

        Args:
            salon_id: ID of the salon
            name: Service name
            description: Optional service description
            duration_minutes: Duration in minutes
            price: Service price
            category: Optional category

        Returns:
            Created Service instance
        """
        service = Service(
            salon_id=salon_id,
            name=name,
            description=description,
            duration_minutes=duration_minutes,
            price=price,
            category=category,
        )

        self.session.add(service)
        await self.session.commit()
        await self.session.refresh(service)

        return service

    async def get_by_id(self, service_id: int, load_salon: bool = False) -> Service | None:
        """
        Get service by ID.

        Args:
            service_id: Service ID
            load_salon: Whether to eagerly load salon relationship

        Returns:
            Service instance or None if not found
        """
        stmt = select(Service).where(Service.id == service_id)

        if load_salon:
            stmt = stmt.options(selectinload(Service.salon))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_salon_id(self, salon_id: int) -> list[Service]:
        """
        List all services in a salon.

        Args:
            salon_id: Salon ID

        Returns:
            List of Service instances
        """
        stmt = (
            select(Service)
            .where(Service.salon_id == salon_id)
            .order_by(Service.category, Service.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_category(self, salon_id: int, category: str) -> list[Service]:
        """
        List services by category within a salon.

        Args:
            salon_id: Salon ID
            category: Service category

        Returns:
            List of Service instances
        """
        stmt = (
            select(Service)
            .where(Service.salon_id == salon_id, Service.category == category)
            .order_by(Service.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_price_range(
        self,
        salon_id: int,
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> list[Service]:
        """
        List services by price range within a salon.

        Args:
            salon_id: Salon ID
            min_price: Minimum price (inclusive)
            max_price: Maximum price (inclusive)

        Returns:
            List of Service instances
        """
        stmt = select(Service).where(Service.salon_id == salon_id)

        if min_price is not None:
            stmt = stmt.where(Service.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Service.price <= max_price)

        stmt = stmt.order_by(Service.price)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(
        self,
        service_id: int,
        **fields,
    ) -> Service | None:
        """
        Update service fields.

        Args:
            service_id: Service ID
            **fields: Fields to update

        Returns:
            Updated Service instance or None if not found
        """
        service = await self.get_by_id(service_id)
        if not service:
            return None

        for key, value in fields.items():
            if hasattr(service, key):
                setattr(service, key, value)

        await self.session.commit()
        await self.session.refresh(service)

        return service

    async def delete(self, service_id: int) -> bool:
        """
        Delete a service.

        Args:
            service_id: Service ID

        Returns:
            True if deleted, False if not found
        """
        service = await self.get_by_id(service_id)
        if not service:
            return False

        await self.session.delete(service)
        await self.session.commit()

        return True

    async def exists_by_id(self, service_id: int) -> bool:
        """
        Check if service exists by ID.

        Args:
            service_id: Service ID

        Returns:
            True if exists, False otherwise
        """
        stmt = select(Service.id).where(Service.id == service_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
