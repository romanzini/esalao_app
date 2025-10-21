"""API v1 routes package."""

from backend.app.api.v1.routes import auth, scheduling, payments, bookings, professionals, services, webhooks, refunds, waitlist, loyalty, notifications, cancellation_policies, no_show_jobs, multi_service_booking

__all__ = ["auth", "scheduling", "payments", "bookings", "professionals", "services", "webhooks", "refunds", "waitlist", "loyalty", "notifications", "cancellation_policies", "no_show_jobs", "multi_service_booking"]
