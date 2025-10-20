"""Repository for loyalty system data access."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_, or_, desc, asc, case, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.app.db.models.loyalty import (
    LoyaltyAccount, PointTransaction, LoyaltyReward,
    PointTransactionType, LoyaltyTier, PointEarnReason, PointRedemptionType
)
from backend.app.db.models.user import User
from backend.app.db.models.booking import Booking


class LoyaltyRepository:
    """Repository for loyalty system operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Loyalty Account Operations
    async def create_loyalty_account(self, user_id: int, **kwargs) -> LoyaltyAccount:
        """Create a new loyalty account for a user."""
        account_data = {
            "user_id": user_id,
            "current_points": 0,
            "lifetime_points": 0,
            "current_tier": LoyaltyTier.BRONZE,
            "tier_points": 0,
            "join_date": datetime.now(timezone.utc),
            **kwargs
        }

        account = LoyaltyAccount(**account_data)
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def get_loyalty_account_by_user_id(self, user_id: int) -> Optional[LoyaltyAccount]:
        """Get loyalty account by user ID."""
        result = await self.session.execute(
            select(LoyaltyAccount)
            .options(selectinload(LoyaltyAccount.user))
            .where(LoyaltyAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_loyalty_account_by_id(self, account_id: int) -> Optional[LoyaltyAccount]:
        """Get loyalty account by ID."""
        result = await self.session.execute(
            select(LoyaltyAccount)
            .options(selectinload(LoyaltyAccount.user))
            .where(LoyaltyAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    async def update_loyalty_account(self, account_id: int, **kwargs) -> Optional[LoyaltyAccount]:
        """Update loyalty account."""
        kwargs["updated_at"] = datetime.now(timezone.utc)

        await self.session.execute(
            update(LoyaltyAccount)
            .where(LoyaltyAccount.id == account_id)
            .values(**kwargs)
        )
        await self.session.commit()

        return await self.get_loyalty_account_by_id(account_id)

    async def get_accounts_by_tier(self, tier: LoyaltyTier, limit: int = 100) -> List[LoyaltyAccount]:
        """Get accounts by loyalty tier."""
        result = await self.session.execute(
            select(LoyaltyAccount)
            .options(selectinload(LoyaltyAccount.user))
            .where(and_(
                LoyaltyAccount.current_tier == tier,
                LoyaltyAccount.is_active == True
            ))
            .order_by(desc(LoyaltyAccount.tier_points))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_top_loyal_customers(self, limit: int = 50) -> List[LoyaltyAccount]:
        """Get top customers by lifetime points."""
        result = await self.session.execute(
            select(LoyaltyAccount)
            .options(selectinload(LoyaltyAccount.user))
            .where(LoyaltyAccount.is_active == True)
            .order_by(desc(LoyaltyAccount.lifetime_points))
            .limit(limit)
        )
        return list(result.scalars().all())

    # Point Transaction Operations
    async def create_point_transaction(self, **kwargs) -> PointTransaction:
        """Create a new point transaction."""
        transaction_data = {
            "transaction_date": datetime.now(timezone.utc),
            **kwargs
        }

        transaction = PointTransaction(**transaction_data)
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def get_transaction_history(
        self,
        loyalty_account_id: int,
        transaction_type: Optional[PointTransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PointTransaction]:
        """Get transaction history for an account."""
        query = select(PointTransaction).where(
            PointTransaction.loyalty_account_id == loyalty_account_id
        )

        if transaction_type:
            query = query.where(PointTransaction.transaction_type == transaction_type)

        if start_date:
            query = query.where(PointTransaction.transaction_date >= start_date)

        if end_date:
            query = query.where(PointTransaction.transaction_date <= end_date)

        query = query.order_by(desc(PointTransaction.transaction_date)).limit(limit).offset(offset)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expiring_points(
        self,
        loyalty_account_id: int,
        days_ahead: int = 30
    ) -> List[PointTransaction]:
        """Get points that will expire within specified days."""
        expiry_threshold = datetime.now(timezone.utc) + timedelta(days=days_ahead)

        result = await self.session.execute(
            select(PointTransaction)
            .where(and_(
                PointTransaction.loyalty_account_id == loyalty_account_id,
                PointTransaction.transaction_type == PointTransactionType.EARNED,
                PointTransaction.expiry_date.is_not(None),
                PointTransaction.expiry_date <= expiry_threshold,
                PointTransaction.is_expired == False
            ))
            .order_by(asc(PointTransaction.expiry_date))
        )
        return list(result.scalars().all())

    async def expire_points(self, loyalty_account_id: int) -> int:
        """Expire points that have passed their expiry date."""
        now = datetime.now(timezone.utc)

        # Get expired points
        result = await self.session.execute(
            select(PointTransaction)
            .where(and_(
                PointTransaction.loyalty_account_id == loyalty_account_id,
                PointTransaction.transaction_type == PointTransactionType.EARNED,
                PointTransaction.expiry_date <= now,
                PointTransaction.is_expired == False
            ))
        )

        expired_transactions = list(result.scalars().all())
        total_expired_points = 0

        for transaction in expired_transactions:
            # Mark as expired
            transaction.is_expired = True

            # Create expiration transaction
            expiration_transaction = PointTransaction(
                loyalty_account_id=loyalty_account_id,
                transaction_type=PointTransactionType.EXPIRED,
                points_amount=-transaction.points_amount,
                balance_after=0,  # Will be updated by service
                description=f"Points expired from transaction {transaction.id}",
                reference_id=str(transaction.id)
            )
            self.session.add(expiration_transaction)
            total_expired_points += transaction.points_amount

        await self.session.commit()
        return total_expired_points

    async def get_points_summary(
        self,
        loyalty_account_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get points summary for an account."""
        query = select(
            func.sum(case(
                (PointTransaction.transaction_type == PointTransactionType.EARNED, PointTransaction.points_amount),
                else_=0
            )).label("total_earned"),
            func.sum(case(
                (PointTransaction.transaction_type == PointTransactionType.REDEEMED, -PointTransaction.points_amount),
                else_=0
            )).label("total_redeemed"),
            func.sum(case(
                (PointTransaction.transaction_type == PointTransactionType.EXPIRED, -PointTransaction.points_amount),
                else_=0
            )).label("total_expired"),
            func.count().label("total_transactions")
        ).where(PointTransaction.loyalty_account_id == loyalty_account_id)

        if start_date:
            query = query.where(PointTransaction.transaction_date >= start_date)

        if end_date:
            query = query.where(PointTransaction.transaction_date <= end_date)

        result = await self.session.execute(query)
        row = result.first()

        return {
            "total_earned": int(row.total_earned or 0),
            "total_redeemed": int(row.total_redeemed or 0),
            "total_expired": int(row.total_expired or 0),
            "total_transactions": int(row.total_transactions or 0),
            "net_points": int((row.total_earned or 0) - (row.total_redeemed or 0) - (row.total_expired or 0))
        }

    # Loyalty Reward Operations
    async def create_loyalty_reward(self, **kwargs) -> LoyaltyReward:
        """Create a new loyalty reward."""
        reward = LoyaltyReward(**kwargs)
        self.session.add(reward)
        await self.session.commit()
        await self.session.refresh(reward)
        return reward

    async def get_loyalty_reward_by_id(self, reward_id: int) -> Optional[LoyaltyReward]:
        """Get loyalty reward by ID."""
        result = await self.session.execute(
            select(LoyaltyReward)
            .options(selectinload(LoyaltyReward.service))
            .where(LoyaltyReward.id == reward_id)
        )
        return result.scalar_one_or_none()

    async def get_available_rewards(
        self,
        user_tier: Optional[LoyaltyTier] = None,
        redemption_type: Optional[PointRedemptionType] = None,
        max_cost: Optional[int] = None
    ) -> List[LoyaltyReward]:
        """Get available rewards based on criteria."""
        now = datetime.now(timezone.utc)

        query = select(LoyaltyReward).where(and_(
            LoyaltyReward.is_active == True,
            or_(
                LoyaltyReward.available_from.is_(None),
                LoyaltyReward.available_from <= now
            ),
            or_(
                LoyaltyReward.available_until.is_(None),
                LoyaltyReward.available_until >= now
            ),
            or_(
                LoyaltyReward.total_available.is_(None),
                LoyaltyReward.total_redeemed < LoyaltyReward.total_available
            )
        ))

        if redemption_type:
            query = query.where(LoyaltyReward.redemption_type == redemption_type)

        if max_cost:
            query = query.where(LoyaltyReward.point_cost <= max_cost)

        # Handle tier filtering
        if user_tier:
            tier_hierarchy = {
                LoyaltyTier.BRONZE: 0,
                LoyaltyTier.SILVER: 1,
                LoyaltyTier.GOLD: 2,
                LoyaltyTier.PLATINUM: 3,
                LoyaltyTier.DIAMOND: 4,
            }
            user_tier_value = tier_hierarchy.get(user_tier, 0)

            # Include rewards with no tier requirement or tier <= user tier
            query = query.where(or_(
                LoyaltyReward.minimum_tier.is_(None),
                case(
                    (LoyaltyReward.minimum_tier == LoyaltyTier.BRONZE, 0),
                    (LoyaltyReward.minimum_tier == LoyaltyTier.SILVER, 1),
                    (LoyaltyReward.minimum_tier == LoyaltyTier.GOLD, 2),
                    (LoyaltyReward.minimum_tier == LoyaltyTier.PLATINUM, 3),
                    (LoyaltyReward.minimum_tier == LoyaltyTier.DIAMOND, 4),
                    else_=0
                ) <= user_tier_value
            ))

        query = query.order_by(asc(LoyaltyReward.point_cost))

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_loyalty_reward(self, reward_id: int, **kwargs) -> Optional[LoyaltyReward]:
        """Update loyalty reward."""
        kwargs["updated_at"] = datetime.now(timezone.utc)

        await self.session.execute(
            update(LoyaltyReward)
            .where(LoyaltyReward.id == reward_id)
            .values(**kwargs)
        )
        await self.session.commit()

        return await self.get_loyalty_reward_by_id(reward_id)

    async def increment_reward_redemption_count(self, reward_id: int) -> bool:
        """Increment the redemption count for a reward."""
        result = await self.session.execute(
            update(LoyaltyReward)
            .where(LoyaltyReward.id == reward_id)
            .values(
                total_redeemed=LoyaltyReward.total_redeemed + 1,
                updated_at=datetime.now(timezone.utc)
            )
        )
        await self.session.commit()
        return result.rowcount > 0

    # Analytics and Reporting
    async def get_tier_distribution(self) -> Dict[str, int]:
        """Get distribution of users across loyalty tiers."""
        result = await self.session.execute(
            select(
                LoyaltyAccount.current_tier,
                func.count().label("count")
            )
            .where(LoyaltyAccount.is_active == True)
            .group_by(LoyaltyAccount.current_tier)
        )

        distribution = {}
        for row in result:
            distribution[row.current_tier.value] = row.count

        return distribution

    async def get_points_statistics(self) -> Dict[str, Any]:
        """Get overall points statistics."""
        result = await self.session.execute(
            select(
                func.sum(LoyaltyAccount.current_points).label("total_points_outstanding"),
                func.sum(LoyaltyAccount.lifetime_points).label("total_points_issued"),
                func.avg(LoyaltyAccount.current_points).label("avg_points_per_user"),
                func.count().label("total_active_accounts")
            )
            .where(LoyaltyAccount.is_active == True)
        )

        row = result.first()

        return {
            "total_points_outstanding": int(row.total_points_outstanding or 0),
            "total_points_issued": int(row.total_points_issued or 0),
            "average_points_per_user": float(row.avg_points_per_user or 0),
            "total_active_accounts": int(row.total_active_accounts or 0)
        }

    async def get_redemption_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get redemption statistics for the last N days."""
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            select(
                PointTransaction.redemption_type,
                func.count().label("redemption_count"),
                func.sum(-PointTransaction.points_amount).label("total_points_redeemed"),
                func.sum(PointTransaction.discount_applied).label("total_discount_value")
            )
            .where(and_(
                PointTransaction.transaction_type == PointTransactionType.REDEEMED,
                PointTransaction.transaction_date >= start_date
            ))
            .group_by(PointTransaction.redemption_type)
        )

        redemptions = {}
        for row in result:
            if row.redemption_type:
                redemptions[row.redemption_type.value] = {
                    "count": row.redemption_count,
                    "points_redeemed": int(row.total_points_redeemed or 0),
                    "discount_value": float(row.total_discount_value or 0)
                }

        return redemptions

    async def get_user_redemption_count(self, user_id: int, reward_id: int) -> int:
        """Get number of times a user has redeemed a specific reward."""
        account = await self.get_loyalty_account_by_user_id(user_id)
        if not account:
            return 0

        result = await self.session.execute(
            select(func.count())
            .select_from(PointTransaction)
            .where(and_(
                PointTransaction.loyalty_account_id == account.id,
                PointTransaction.transaction_type == PointTransactionType.REDEEMED,
                PointTransaction.reference_id == str(reward_id)
            ))
        )

        return result.scalar() or 0
