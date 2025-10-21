# Phase 3 schemas documentation

# Cancellation Policy schemas
from .cancellation_policies import (
    CancellationTierSchema,
    CancellationPolicyCreateSchema,
    CancellationPolicyResponseSchema,
    CancellationFeeCalculationSchema,
    CancellationFeeResponseSchema,
    PolicyApplicationLogSchema,
    CancellationPolicyListSchema,
)

# Audit Event schemas
from .audit import (
    AuditEventSchema,
    AuditEventFilterSchema,
    AuditEventListResponseSchema,
    AuditEventStatsSchema,
    AuditEventDetailSchema,
    AuditTrailSchema,
    AuditSearchRequestSchema,
    AuditReportRequestSchema,
    AuditReportResponseSchema,
)

# Reporting schemas
from .reports import (
    BookingMetricsSchema,
    ProfessionalMetricsSchema,
    ServiceMetricsSchema,
    DashboardMetricsSchema,
    RevenueBreakdownSchema,
    TrendDataPointSchema,
    TrendAnalysisSchema,
    ReportFilterSchema,
    ComparativeAnalysisSchema,
    PerformanceRankingSchema,
    PlatformOverviewSchema,
    SalonComparisonSchema,
)

# No-show Detection schemas
from .no_show import (
    NoShowJobConfigSchema,
    NoShowJobExecutionSchema,
    NoShowJobResultSchema,
    NoShowJobHistorySchema,
    NoShowDetectionCriteriaSchema,
    NoShowDetectionResultSchema,
    NoShowStatisticsSchema,
    NoShowPreventionInsightSchema,
    NoShowNotificationSchema,
    NoShowBulkActionSchema,
    NoShowBulkActionResultSchema,
)

# Export Phase 3 schemas
__all__ = [
    # Cancellation Policy schemas
    "CancellationTierSchema",
    "CancellationPolicyCreateSchema",
    "CancellationPolicyResponseSchema",
    "CancellationFeeCalculationSchema",
    "CancellationFeeResponseSchema",
    "PolicyApplicationLogSchema",
    "CancellationPolicyListSchema",
    # Audit schemas
    "AuditEventSchema",
    "AuditEventFilterSchema",
    "AuditEventListResponseSchema",
    "AuditEventStatsSchema",
    "AuditEventDetailSchema",
    "AuditTrailSchema",
    "AuditSearchRequestSchema",
    "AuditReportRequestSchema",
    "AuditReportResponseSchema",
    # Reporting schemas
    "BookingMetricsSchema",
    "ProfessionalMetricsSchema",
    "ServiceMetricsSchema",
    "DashboardMetricsSchema",
    "RevenueBreakdownSchema",
    "TrendDataPointSchema",
    "TrendAnalysisSchema",
    "ReportFilterSchema",
    "ComparativeAnalysisSchema",
    "PerformanceRankingSchema",
    "PlatformOverviewSchema",
    "SalonComparisonSchema",
    # No-show schemas
    "NoShowJobConfigSchema",
    "NoShowJobExecutionSchema",
    "NoShowJobResultSchema",
    "NoShowJobHistorySchema",
    "NoShowDetectionCriteriaSchema",
    "NoShowDetectionResultSchema",
    "NoShowStatisticsSchema",
    "NoShowPreventionInsightSchema",
    "NoShowNotificationSchema",
    "NoShowBulkActionSchema",
    "NoShowBulkActionResultSchema",
]
