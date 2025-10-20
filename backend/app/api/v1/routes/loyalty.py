"""API routes for loyalty system."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer

from backend.app.api.v1.schemas.loyalty import (
    LoyaltyAccountCreateRequest, LoyaltyAccountResponse, PointAwardRequest,
    PointRedemptionRequest, RewardRedemptionRequest, TierUpgradeRequest,
    AccountSuspensionRequest, RewardCreateRequest, PointTransactionResponse,
    LoyaltyRewardResponse, UserRewardResponse, LoyaltySummaryResponse,
    RedemptionResponse, LoyaltyStatisticsResponse
)
from backend.app.db.models.loyalty import PointTransactionType, LoyaltyTier, PointRedemptionType
from backend.app.services.loyalty import LoyaltyService
from backend.app.db.repositories.loyalty import LoyaltyRepository
from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.user import UserRepository
from backend.app.db.session import get_db_session
from backend.app.core.security.rbac import require_role, get_current_user
from backend.app.db.models.user import UserRole
from backend.app.core.exceptions import NotFoundError, ValidationError

router = APIRouter(prefix="/loyalty", tags=["loyalty"])
security = HTTPBearer()


def get_loyalty_service(session=Depends(get_db_session)) -> LoyaltyService:
    """Get loyalty service with dependencies."""
    loyalty_repo = LoyaltyRepository(session)
    booking_repo = BookingRepository(session)
    user_repo = UserRepository(session)
    return LoyaltyService(loyalty_repo, booking_repo, user_repo)


@router.post("/account", response_model=LoyaltyAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_loyalty_account(
    request: LoyaltyAccountCreateRequest,
    current_user=Depends(require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """
    Create loyalty account for a user.

    Only admins and professionals can create accounts for users.
    """
    try:
        account = await loyalty_service.create_loyalty_account(request.user_id)

        # Get full account details
        summary = await loyalty_service.get_user_loyalty_summary(request.user_id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created account"
            )

        return LoyaltyAccountResponse(**summary)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create loyalty account"
        )


@router.get("/account", response_model=LoyaltySummaryResponse)
async def get_my_loyalty_account(
    current_user=Depends(get_current_user),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get current user's loyalty account summary."""
    try:
        summary = await loyalty_service.get_user_loyalty_summary(current_user.id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loyalty account not found"
            )

        return LoyaltySummaryResponse(**summary)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve loyalty account"
        )


@router.get("/account/{user_id}", response_model=LoyaltySummaryResponse)
async def get_user_loyalty_account(
    user_id: int,
    current_user=Depends(require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get loyalty account summary for specific user (admin/professional only)."""
    try:
        summary = await loyalty_service.get_user_loyalty_summary(user_id)
        if not summary:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Loyalty account not found"
            )

        return LoyaltySummaryResponse(**summary)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve loyalty account"
        )


@router.post("/points/award", response_model=PointTransactionResponse)
async def award_custom_points(
    request: PointAwardRequest,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Award custom points to a user (admin only)."""
    try:
        transaction = await loyalty_service.award_custom_points(
            user_id=request.user_id,
            points=request.points,
            reason=request.reason,
            processed_by_user_id=current_user.id
        )

        return PointTransactionResponse.from_orm(transaction)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to award points"
        )


@router.post("/points/redeem", response_model=RedemptionResponse)
async def redeem_points_for_discount(
    request: PointRedemptionRequest,
    current_user=Depends(get_current_user),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Redeem points for booking discount."""
    try:
        result = await loyalty_service.redeem_points_for_discount(
            user_id=current_user.id,
            points_to_redeem=request.points_to_redeem,
            booking_id=request.booking_id
        )

        return RedemptionResponse(**result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to redeem points"
        )


@router.post("/rewards/{reward_id}/redeem", response_model=RedemptionResponse)
async def redeem_reward(
    reward_id: int,
    current_user=Depends(get_current_user),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Redeem a specific loyalty reward."""
    try:
        result = await loyalty_service.redeem_reward(
            user_id=current_user.id,
            reward_id=reward_id
        )

        return RedemptionResponse(**result)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to redeem reward"
        )


@router.get("/rewards", response_model=List[UserRewardResponse])
async def get_available_rewards(
    current_user=Depends(get_current_user),
    redemption_type: Optional[PointRedemptionType] = Query(None, description="Filter by redemption type"),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get rewards available for current user."""
    try:
        rewards = await loyalty_service.get_available_rewards_for_user(current_user.id)

        # Filter by redemption type if specified
        if redemption_type:
            rewards = [r for r in rewards if r["redemption_type"] == redemption_type.value]

        return [UserRewardResponse(**reward) for reward in rewards]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rewards"
        )


@router.get("/rewards/admin", response_model=List[LoyaltyRewardResponse])
async def get_all_rewards(
    current_user=Depends(require_role([UserRole.ADMIN])),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    redemption_type: Optional[PointRedemptionType] = Query(None, description="Filter by redemption type"),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get all loyalty rewards (admin only)."""
    try:
        # This would require adding a method to get all rewards in the service
        # For now, return empty list as placeholder
        return []

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rewards"
        )


@router.post("/rewards", response_model=LoyaltyRewardResponse, status_code=status.HTTP_201_CREATED)
async def create_loyalty_reward(
    request: RewardCreateRequest,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Create new loyalty reward (admin only)."""
    try:
        # This would require adding a method to create rewards in the service
        # For now, return HTTP 501 Not Implemented
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Reward creation not yet implemented"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reward"
        )


@router.get("/transactions", response_model=List[PointTransactionResponse])
async def get_transaction_history(
    current_user=Depends(get_current_user),
    transaction_type: Optional[PointTransactionType] = Query(None, description="Filter by transaction type"),
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip"),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get current user's point transaction history."""
    try:
        transactions = await loyalty_service.get_transaction_history(
            user_id=current_user.id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )

        return [PointTransactionResponse(**t) for t in transactions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction history"
        )


@router.get("/transactions/{user_id}", response_model=List[PointTransactionResponse])
async def get_user_transaction_history(
    user_id: int,
    current_user=Depends(require_role([UserRole.ADMIN, UserRole.PROFESSIONAL])),
    transaction_type: Optional[PointTransactionType] = Query(None, description="Filter by transaction type"),
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip"),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get transaction history for specific user (admin/professional only)."""
    try:
        transactions = await loyalty_service.get_transaction_history(
            user_id=user_id,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )

        return [PointTransactionResponse(**t) for t in transactions]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction history"
        )


@router.post("/account/{user_id}/suspend")
async def suspend_loyalty_account(
    user_id: int,
    request: AccountSuspensionRequest,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Suspend loyalty account (admin only)."""
    try:
        success = await loyalty_service.suspend_account(
            user_id=user_id,
            until_date=request.suspended_until
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to suspend account"
            )

        return {"message": "Account suspended successfully"}

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to suspend account"
        )


@router.post("/account/{user_id}/reactivate")
async def reactivate_loyalty_account(
    user_id: int,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Reactivate suspended loyalty account (admin only)."""
    try:
        success = await loyalty_service.reactivate_account(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to reactivate account"
            )

        return {"message": "Account reactivated successfully"}

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate account"
        )


@router.post("/tier/upgrade", response_model=dict)
async def upgrade_user_tier(
    request: TierUpgradeRequest,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Manually upgrade user tier (admin only)."""
    try:
        success = await loyalty_service.upgrade_user_tier(
            user_id=request.user_id,
            new_tier=request.new_tier
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to upgrade tier"
            )

        return {"message": f"User tier upgraded to {request.new_tier.value}"}

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upgrade tier"
        )


@router.post("/points/expire/{user_id}")
async def expire_user_points(
    user_id: int,
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Expire points for specific user (admin only)."""
    try:
        expired_points = await loyalty_service.expire_user_points(user_id)

        return {
            "message": f"Expired {expired_points} points for user {user_id}",
            "expired_points": expired_points
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to expire points"
        )


@router.get("/statistics", response_model=LoyaltyStatisticsResponse)
async def get_loyalty_statistics(
    current_user=Depends(require_role([UserRole.ADMIN])),
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Get system-wide loyalty statistics (admin only)."""
    try:
        # This would require implementing statistics methods in the service
        # For now, return empty statistics
        return LoyaltyStatisticsResponse(
            tier_distribution={},
            points_statistics={},
            redemption_statistics={}
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


# Webhook endpoints for automatic point awarding
@router.post("/webhooks/booking-completed")
async def booking_completed_webhook(
    booking_id: int,
    # This would typically use API key authentication for webhook security
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Webhook to award points when booking is completed."""
    try:
        transaction = await loyalty_service.award_booking_points(booking_id)

        if transaction:
            return {
                "message": "Points awarded successfully",
                "transaction_id": transaction.id,
                "points_awarded": transaction.points_amount
            }
        else:
            return {"message": "No points awarded (booking not eligible)"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process booking completion"
        )


@router.post("/webhooks/review-submitted")
async def review_submitted_webhook(
    user_id: int,
    booking_id: int,
    # This would typically use API key authentication for webhook security
    loyalty_service: LoyaltyService = Depends(get_loyalty_service)
):
    """Webhook to award points when review is submitted."""
    try:
        transaction = await loyalty_service.award_review_points(user_id, booking_id)

        return {
            "message": "Review points awarded successfully",
            "transaction_id": transaction.id,
            "points_awarded": transaction.points_amount
        }

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process review submission"
        )
