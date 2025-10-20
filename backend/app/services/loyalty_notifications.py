"""
Loyalty notification integration service.

This service integrates the notification system with loyalty events,
automatically sending notifications when points are earned, rewards
are available, tiers are upgraded, or points expire.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.repositories.user import UserRepository
from backend.app.services.notifications import NotificationService
from backend.app.db.models.notifications import NotificationEventType, NotificationPriority


logger = logging.getLogger(__name__)


class LoyaltyNotificationService:
    """Service for handling loyalty program notifications."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the loyalty notification service.

        Args:
            session: Database session
        """
        self.session = session
        self.notification_service = NotificationService(session)
        self.user_repo = UserRepository(session)

    async def notify_points_earned(
        self,
        user_id: int,
        points_earned: int,
        transaction_type: str,
        transaction_id: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send points earned notification.

        Args:
            user_id: ID of the user who earned points
            points_earned: Number of points earned
            transaction_type: Type of transaction (booking, referral, etc.)
            transaction_id: ID of the related transaction
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get user's current total points from loyalty service
            # loyalty_service = LoyaltyService(self.session)
            # current_total = await loyalty_service.get_user_points(user_id)
            current_total = 0  # Placeholder

            # Prepare context data
            context = await self._prepare_points_context(
                user=user,
                points_earned=points_earned,
                current_total=current_total,
                transaction_type=transaction_type,
                transaction_id=transaction_id
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.LOYALTY_POINTS_EARNED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"points_earned_{user_id}_{points_earned}"
            )

            logger.info(f"Points earned notification sent to user {user_id} for {points_earned} points")

            return {
                "user_id": user_id,
                "points_earned": points_earned,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send points earned notification for user {user_id}: {str(e)}")
            raise

    async def notify_tier_upgrade(
        self,
        user_id: int,
        old_tier: str,
        new_tier: str,
        new_benefits: List[str],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send tier upgrade notification.

        Args:
            user_id: ID of the user who got upgraded
            old_tier: Previous loyalty tier
            new_tier: New loyalty tier
            new_benefits: List of new benefits unlocked
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Prepare context data
            context = await self._prepare_tier_context(
                user=user,
                old_tier=old_tier,
                new_tier=new_tier,
                new_benefits=new_benefits
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.LOYALTY_TIER_UPGRADE.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"tier_upgrade_{user_id}_{new_tier}"
            )

            logger.info(f"Tier upgrade notification sent to user {user_id}: {old_tier} -> {new_tier}")

            return {
                "user_id": user_id,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send tier upgrade notification for user {user_id}: {str(e)}")
            raise

    async def notify_reward_available(
        self,
        user_id: int,
        reward_name: str,
        reward_points_cost: int,
        reward_description: Optional[str] = None,
        expiry_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send reward available notification.

        Args:
            user_id: ID of the user who can claim the reward
            reward_name: Name of the available reward
            reward_points_cost: Points required to claim the reward
            reward_description: Description of the reward
            expiry_date: When the reward expires
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get user's current points from loyalty service
            # loyalty_service = LoyaltyService(self.session)
            # current_points = await loyalty_service.get_user_points(user_id)
            current_points = reward_points_cost + 100  # Placeholder - assume user has enough

            # Only send if user has enough points
            if current_points < reward_points_cost:
                return {"user_id": user_id, "notifications_queued": 0}

            # Prepare context data
            context = await self._prepare_reward_context(
                user=user,
                reward_name=reward_name,
                reward_points_cost=reward_points_cost,
                reward_description=reward_description,
                current_points=current_points,
                expiry_date=expiry_date
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.LOYALTY_REWARD_AVAILABLE.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"reward_available_{user_id}_{reward_name.replace(' ', '_')}"
            )

            logger.info(f"Reward available notification sent to user {user_id} for {reward_name}")

            return {
                "user_id": user_id,
                "reward_name": reward_name,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send reward available notification for user {user_id}: {str(e)}")
            raise

    async def notify_points_expiring(
        self,
        user_id: int,
        expiring_points: int,
        expiry_date: datetime,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send points expiring soon notification.

        Args:
            user_id: ID of the user with expiring points
            expiring_points: Number of points expiring
            expiry_date: When the points expire
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get user's total points and available rewards
            # loyalty_service = LoyaltyService(self.session)
            # current_points = await loyalty_service.get_user_points(user_id)
            # available_rewards = await loyalty_service.get_available_rewards(user_id)
            current_points = expiring_points + 200  # Placeholder
            available_rewards = []  # Placeholder

            # Prepare context data
            context = await self._prepare_expiry_context(
                user=user,
                expiring_points=expiring_points,
                current_points=current_points,
                expiry_date=expiry_date,
                available_rewards=available_rewards
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.LOYALTY_POINTS_EXPIRING.value,
                context_data=context,
                priority=NotificationPriority.HIGH.value,
                correlation_id=correlation_id or f"points_expiring_{user_id}_{expiring_points}"
            )

            logger.info(f"Points expiring notification sent to user {user_id} for {expiring_points} points")

            return {
                "user_id": user_id,
                "expiring_points": expiring_points,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send points expiring notification for user {user_id}: {str(e)}")
            raise

    async def notify_reward_claimed(
        self,
        user_id: int,
        reward_name: str,
        points_used: int,
        reward_code: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send reward claimed confirmation notification.

        Args:
            user_id: ID of the user who claimed the reward
            reward_name: Name of the claimed reward
            points_used: Points used to claim the reward
            reward_code: Optional reward code or voucher
            correlation_id: Optional correlation ID for tracking

        Returns:
            Dictionary with notification results
        """
        try:
            # Get user information
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")

            # TODO: Get user's remaining points
            # loyalty_service = LoyaltyService(self.session)
            # remaining_points = await loyalty_service.get_user_points(user_id)
            remaining_points = 0  # Placeholder

            # Prepare context data
            context = await self._prepare_claim_context(
                user=user,
                reward_name=reward_name,
                points_used=points_used,
                remaining_points=remaining_points,
                reward_code=reward_code
            )

            # Send notification
            result = await self.notification_service.send_notification(
                user_id=user_id,
                event_type=NotificationEventType.LOYALTY_REWARD_CLAIMED.value,
                context_data=context,
                priority=NotificationPriority.NORMAL.value,
                correlation_id=correlation_id or f"reward_claimed_{user_id}_{reward_name.replace(' ', '_')}"
            )

            logger.info(f"Reward claimed notification sent to user {user_id} for {reward_name}")

            return {
                "user_id": user_id,
                "reward_name": reward_name,
                "points_used": points_used,
                "notifications_queued": result["notifications_queued"]
            }

        except Exception as e:
            logger.error(f"Failed to send reward claimed notification for user {user_id}: {str(e)}")
            raise

    async def _prepare_points_context(
        self,
        user,
        points_earned: int,
        current_total: int,
        transaction_type: str,
        transaction_id: Optional[int]
    ) -> Dict[str, Any]:
        """Prepare context data for points earned notifications."""
        transaction_descriptions = {
            "booking": "agendamento de serviço",
            "referral": "indicação de amigo",
            "review": "avaliação de serviço",
            "birthday": "aniversário",
            "bonus": "promoção especial"
        }

        context = {
            "user_name": user.full_name,
            "points_earned": str(points_earned),
            "current_total": str(current_total),
            "transaction_description": transaction_descriptions.get(transaction_type, transaction_type),
            "app_url": "https://esalao.app",  # Should come from config
        }

        if transaction_id:
            context["transaction_id"] = str(transaction_id)

        return context

    async def _prepare_tier_context(
        self,
        user,
        old_tier: str,
        new_tier: str,
        new_benefits: List[str]
    ) -> Dict[str, Any]:
        """Prepare context data for tier upgrade notifications."""
        tier_names = {
            "bronze": "Bronze",
            "silver": "Prata",
            "gold": "Ouro",
            "platinum": "Platina",
            "diamond": "Diamante"
        }

        context = {
            "user_name": user.full_name,
            "old_tier_name": tier_names.get(old_tier.lower(), old_tier.title()),
            "new_tier_name": tier_names.get(new_tier.lower(), new_tier.title()),
            "benefits_list": ", ".join(new_benefits) if new_benefits else "Benefícios exclusivos",
            "app_url": "https://esalao.app",  # Should come from config
        }

        return context

    async def _prepare_reward_context(
        self,
        user,
        reward_name: str,
        reward_points_cost: int,
        reward_description: Optional[str],
        current_points: int,
        expiry_date: Optional[datetime]
    ) -> Dict[str, Any]:
        """Prepare context data for reward available notifications."""
        context = {
            "user_name": user.full_name,
            "reward_name": reward_name,
            "reward_points_cost": str(reward_points_cost),
            "current_points": str(current_points),
            "reward_description": reward_description or f"Resgate {reward_name} usando seus pontos",
            "app_url": "https://esalao.app",  # Should come from config
        }

        if expiry_date:
            context["expiry_date"] = expiry_date.strftime("%d/%m/%Y")

        return context

    async def _prepare_expiry_context(
        self,
        user,
        expiring_points: int,
        current_points: int,
        expiry_date: datetime,
        available_rewards: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare context data for points expiring notifications."""
        days_until_expiry = (expiry_date - datetime.now()).days

        context = {
            "user_name": user.full_name,
            "expiring_points": str(expiring_points),
            "current_points": str(current_points),
            "expiry_date": expiry_date.strftime("%d/%m/%Y"),
            "days_until_expiry": str(max(0, days_until_expiry)),
            "has_rewards": "sim" if available_rewards else "não",
            "app_url": "https://esalao.app",  # Should come from config
        }

        return context

    async def _prepare_claim_context(
        self,
        user,
        reward_name: str,
        points_used: int,
        remaining_points: int,
        reward_code: Optional[str]
    ) -> Dict[str, Any]:
        """Prepare context data for reward claimed notifications."""
        context = {
            "user_name": user.full_name,
            "reward_name": reward_name,
            "points_used": str(points_used),
            "remaining_points": str(remaining_points),
            "claim_date": datetime.now().strftime("%d/%m/%Y"),
            "app_url": "https://esalao.app",  # Should come from config
        }

        if reward_code:
            context["reward_code"] = reward_code

        return context
