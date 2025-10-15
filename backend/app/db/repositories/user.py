"""User repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.user import User, UserRole


class UserRepository:
    """Repository for User model database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session

    async def create(
        self,
        email: str,
        password_hash: str,
        full_name: str,
        phone: str | None = None,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        """
        Create a new user.

        Args:
            email: User email address
            password_hash: Hashed password
            full_name: User full name
            phone: Optional phone number
            role: User role (default: CLIENT)

        Returns:
            Created User instance
        """
        user = User(
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            phone=phone,
            role=role,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User instance or None if not found
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User instance or None if not found
        """
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, user_id: int) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID
        """
        user = await self.get_by_id(user_id)
        if user:
            from datetime import datetime, UTC

            user.last_login = datetime.now(UTC)
            await self.session.commit()

    async def exists_by_email(self, email: str) -> bool:
        """
        Check if user exists by email.

        Args:
            email: User email address

        Returns:
            True if user exists, False otherwise
        """
        user = await self.get_by_email(email)
        return user is not None
