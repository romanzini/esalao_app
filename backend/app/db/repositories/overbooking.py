"""Overbooking configuration repository."""

from datetime import datetime, time
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.overbooking import OverbookingConfig, OverbookingScope, OverbookingTimeframe


class OverbookingRepository:
    """Repository for overbooking configuration operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(self, config_data: dict) -> OverbookingConfig:
        """Create a new overbooking configuration."""
        config = OverbookingConfig(**config_data)
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def get_by_id(self, config_id: int) -> Optional[OverbookingConfig]:
        """Get configuration by ID."""
        query = select(OverbookingConfig).where(OverbookingConfig.id == config_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, config_id: int, update_data: dict) -> Optional[OverbookingConfig]:
        """Update configuration."""
        config = await self.get_by_id(config_id)
        if not config:
            return None

        for key, value in update_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def delete(self, config_id: int) -> bool:
        """Delete configuration."""
        config = await self.get_by_id(config_id)
        if not config:
            return False

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def list_all(self, include_inactive: bool = False) -> List[OverbookingConfig]:
        """List all configurations."""
        conditions = []
        if not include_inactive:
            conditions.append(OverbookingConfig.is_active == True)

        if conditions:
            query = select(OverbookingConfig).where(and_(*conditions))
        else:
            query = select(OverbookingConfig)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_effective_config(
        self,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
        check_time: Optional[time] = None,
        check_datetime: Optional[datetime] = None
    ) -> Optional[OverbookingConfig]:
        """
        Get the most specific effective overbooking configuration.

        Priority order: service -> professional -> salon -> global

        Args:
            salon_id: Salon ID to check
            professional_id: Professional ID to check
            service_id: Service ID to check
            check_time: Time to check for time-based restrictions
            check_datetime: Datetime to check for effective period

        Returns:
            Most specific effective configuration or None
        """
        now = check_datetime or datetime.utcnow()

        # Build base conditions
        base_conditions = [
            OverbookingConfig.is_active == True,
            or_(
                OverbookingConfig.effective_from.is_(None),
                OverbookingConfig.effective_from <= now
            ),
            or_(
                OverbookingConfig.effective_until.is_(None),
                OverbookingConfig.effective_until >= now
            )
        ]

        # Try to find config in priority order

        # 1. Service-specific
        if service_id:
            query = select(OverbookingConfig).where(
                and_(
                    *base_conditions,
                    OverbookingConfig.scope == OverbookingScope.SERVICE,
                    OverbookingConfig.service_id == service_id
                )
            )
            result = await self.session.execute(query)
            config = result.scalar_one_or_none()
            if config and self._config_applies_to_time(config, check_time):
                return config

        # 2. Professional-specific
        if professional_id:
            query = select(OverbookingConfig).where(
                and_(
                    *base_conditions,
                    OverbookingConfig.scope == OverbookingScope.PROFESSIONAL,
                    OverbookingConfig.professional_id == professional_id
                )
            )
            result = await self.session.execute(query)
            config = result.scalar_one_or_none()
            if config and self._config_applies_to_time(config, check_time):
                return config

        # 3. Salon-specific
        if salon_id:
            query = select(OverbookingConfig).where(
                and_(
                    *base_conditions,
                    OverbookingConfig.scope == OverbookingScope.SALON,
                    OverbookingConfig.salon_id == salon_id
                )
            )
            result = await self.session.execute(query)
            config = result.scalar_one_or_none()
            if config and self._config_applies_to_time(config, check_time):
                return config

        # 4. Global default
        query = select(OverbookingConfig).where(
            and_(
                *base_conditions,
                OverbookingConfig.scope == OverbookingScope.GLOBAL
            )
        )
        result = await self.session.execute(query)
        config = result.scalar_one_or_none()
        if config and self._config_applies_to_time(config, check_time):
            return config

        return None

    async def list_by_scope(
        self,
        scope: OverbookingScope,
        scope_id: Optional[int] = None,
        include_inactive: bool = False
    ) -> List[OverbookingConfig]:
        """
        List configurations by scope.

        Args:
            scope: Configuration scope
            scope_id: ID for scoped entities (salon_id, professional_id, service_id)
            include_inactive: Whether to include inactive configurations

        Returns:
            List of configurations
        """
        conditions = [OverbookingConfig.scope == scope]

        if not include_inactive:
            conditions.append(OverbookingConfig.is_active == True)

        if scope_id:
            if scope == OverbookingScope.SALON:
                conditions.append(OverbookingConfig.salon_id == scope_id)
            elif scope == OverbookingScope.PROFESSIONAL:
                conditions.append(OverbookingConfig.professional_id == scope_id)
            elif scope == OverbookingScope.SERVICE:
                conditions.append(OverbookingConfig.service_id == scope_id)

        query = select(OverbookingConfig).where(and_(*conditions))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_global_default(self) -> Optional[OverbookingConfig]:
        """Get the global default overbooking configuration."""
        query = select(OverbookingConfig).where(
            and_(
                OverbookingConfig.scope == OverbookingScope.GLOBAL,
                OverbookingConfig.is_active == True
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_default_global_config(self) -> OverbookingConfig:
        """Create default global overbooking configuration."""
        config = OverbookingConfig(
            name="Default Global Overbooking",
            description="Default platform-wide overbooking configuration",
            scope=OverbookingScope.GLOBAL,
            max_overbooking_percentage=15.0,  # 15% default
            timeframe=OverbookingTimeframe.HOURLY,
            min_historical_bookings=20,
            historical_period_days=30,
            min_no_show_rate=8.0,  # 8% minimum no-show rate
            max_no_show_rate=40.0,  # 40% maximum no-show rate
            is_active=True
        )

        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def check_conflicts(
        self,
        scope: OverbookingScope,
        salon_id: Optional[int] = None,
        professional_id: Optional[int] = None,
        service_id: Optional[int] = None,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        Check if there are conflicting configurations.

        Args:
            scope: Configuration scope
            salon_id: Salon ID
            professional_id: Professional ID
            service_id: Service ID
            exclude_id: Configuration ID to exclude from check

        Returns:
            True if conflicts exist
        """
        conditions = [
            OverbookingConfig.scope == scope,
            OverbookingConfig.is_active == True
        ]

        if exclude_id:
            conditions.append(OverbookingConfig.id != exclude_id)

        if scope == OverbookingScope.SALON and salon_id:
            conditions.append(OverbookingConfig.salon_id == salon_id)
        elif scope == OverbookingScope.PROFESSIONAL and professional_id:
            conditions.append(OverbookingConfig.professional_id == professional_id)
        elif scope == OverbookingScope.SERVICE and service_id:
            conditions.append(OverbookingConfig.service_id == service_id)

        query = select(OverbookingConfig).where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    def _config_applies_to_time(self, config: OverbookingConfig, check_time: Optional[time]) -> bool:
        """Check if configuration applies to specific time."""
        if not check_time:
            return True

        return config.applies_to_time(check_time)
