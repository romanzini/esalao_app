"""API v1 package."""

from fastapi import APIRouter

from backend.app.api.v1.routes import auth, bookings, professionals, scheduling, services, payments, webhooks, refunds, payment_metrics, waitlist, loyalty, notifications, cancellation_policies, no_show_jobs, audit, reports, platform_reports, optimized_reports

api_router = APIRouter(prefix="/v1")

# Include route modules
api_router.include_router(auth.router)
api_router.include_router(scheduling.router)
api_router.include_router(bookings.router)
api_router.include_router(professionals.router)
api_router.include_router(services.router)
api_router.include_router(payments.router)
api_router.include_router(webhooks.router)
api_router.include_router(refunds.router)
api_router.include_router(payment_metrics.router)
api_router.include_router(waitlist.router)
api_router.include_router(loyalty.router)
api_router.include_router(notifications.router)
api_router.include_router(cancellation_policies.router)
api_router.include_router(no_show_jobs.router)
api_router.include_router(audit.router)
api_router.include_router(reports.router)
api_router.include_router(platform_reports.router)
api_router.include_router(optimized_reports.router)

__all__ = ["api_router"]
