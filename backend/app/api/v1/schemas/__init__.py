"""
API schemas package.

This package contains all Pydantic models used for request/response schemas
in the API endpoints.
"""

from .auth import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    TokenResponse,
    PasswordResetRequest,
    PasswordChangeRequest,
)

from .booking import (
    BookingCreate,
    BookingResponse,
    BookingUpdate,
    BookingList,
    BookingSearchRequest,
    BookingSearchResponse,
    AvailableSlot,
    AvailableSlotsResponse,
    BookingCancellationRequest,
    BookingCancellationResponse,
    RescheduleRequest,
    RescheduleResponse,
)

from .professional import (
    ProfessionalCreate,
    ProfessionalResponse,
    ProfessionalUpdate,
    ProfessionalList,
    ProfessionalSearchRequest,
    ProfessionalSearchResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    AvailabilityUpdate,
    AvailabilityList,
)

from .service import (
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
    ServiceList,
    ServiceSearchRequest,
    ServiceSearchResponse,
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
    ServiceCategoryList,
)

from .waitlist import (
    WaitlistEntryCreate,
    WaitlistEntryResponse,
    WaitlistEntryUpdate,
    WaitlistEntryList,
    WaitlistPositionResponse,
    SlotAvailabilityNotification,
)

from .loyalty import (
    LoyaltyTierCreate,
    LoyaltyTierResponse,
    LoyaltyTierUpdate,
    LoyaltyTierList,
    LoyaltyRuleCreate,
    LoyaltyRuleResponse,
    LoyaltyRuleUpdate,
    LoyaltyRuleList,
    PointsTransactionResponse,
    PointsTransactionList,
    PointsBalanceResponse,
    PointsRedemptionRequest,
    PointsRedemptionResponse,
    TierBenefitCreate,
    TierBenefitResponse,
    TierBenefitUpdate,
    TierBenefitList,
)

from .notifications import (
    # Request schemas
    PreferenceUpdateRequest,
    BulkPreferenceUpdateRequest,
    NotificationTemplateRequest,
    SendNotificationRequest,

    # Response schemas
    PreferenceResponse,
    NotificationTemplateResponse,
    NotificationQueueResponse,
    NotificationLogResponse,
    SendNotificationResponse,
    NotificationStatisticsResponse,

    # List response schemas
    PreferenceListResponse,
    TemplateListResponse,
    NotificationHistoryResponse,

    # Enums
    NotificationChannelEnum,
    NotificationEventTypeEnum,
    NotificationPriorityEnum,
    NotificationStatusEnum,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "UserCreate",
    "UserResponse",
    "TokenResponse",
    "PasswordResetRequest",
    "PasswordChangeRequest",

    # Bookings
    "BookingCreate",
    "BookingResponse",
    "BookingUpdate",
    "BookingList",
    "BookingSearchRequest",
    "BookingSearchResponse",
    "AvailableSlot",
    "AvailableSlotsResponse",
    "BookingCancellationRequest",
    "BookingCancellationResponse",
    "RescheduleRequest",
    "RescheduleResponse",

    # Professionals
    "ProfessionalCreate",
    "ProfessionalResponse",
    "ProfessionalUpdate",
    "ProfessionalList",
    "ProfessionalSearchRequest",
    "ProfessionalSearchResponse",
    "AvailabilityCreate",
    "AvailabilityResponse",
    "AvailabilityUpdate",
    "AvailabilityList",

    # Services
    "ServiceCreate",
    "ServiceResponse",
    "ServiceUpdate",
    "ServiceList",
    "ServiceSearchRequest",
    "ServiceSearchResponse",
    "ServiceCategoryCreate",
    "ServiceCategoryResponse",
    "ServiceCategoryUpdate",
    "ServiceCategoryList",

    # Waitlist
    "WaitlistEntryCreate",
    "WaitlistEntryResponse",
    "WaitlistEntryUpdate",
    "WaitlistEntryList",
    "WaitlistPositionResponse",
    "SlotAvailabilityNotification",

    # Loyalty
    "LoyaltyTierCreate",
    "LoyaltyTierResponse",
    "LoyaltyTierUpdate",
    "LoyaltyTierList",
    "LoyaltyRuleCreate",
    "LoyaltyRuleResponse",
    "LoyaltyRuleUpdate",
    "LoyaltyRuleList",
    "PointsTransactionResponse",
    "PointsTransactionList",
    "PointsBalanceResponse",
    "PointsRedemptionRequest",
    "PointsRedemptionResponse",
    "TierBenefitCreate",
    "TierBenefitResponse",
    "TierBenefitUpdate",
    "TierBenefitList",

    # Notifications
    "PreferenceUpdateRequest",
    "BulkPreferenceUpdateRequest",
    "NotificationTemplateRequest",
    "SendNotificationRequest",
    "PreferenceResponse",
    "NotificationTemplateResponse",
    "NotificationQueueResponse",
    "NotificationLogResponse",
    "SendNotificationResponse",
    "NotificationStatisticsResponse",
    "PreferenceListResponse",
    "TemplateListResponse",
    "NotificationHistoryResponse",
    "NotificationChannelEnum",
    "NotificationEventTypeEnum",
    "NotificationPriorityEnum",
    "NotificationStatusEnum",
]
