"""
Core exceptions for the esalao application.

This module defines custom exception classes used throughout the application
for consistent error handling and user feedback.
"""

from typing import Any, Dict, Optional


class ESalaoException(Exception):
    """Base exception class for all esalao application errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(ESalaoException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "VALIDATION_ERROR")
        self.field = field


class NotFoundError(ESalaoException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id


class AuthenticationError(ESalaoException):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "AUTHENTICATION_ERROR")


class AuthorizationError(ESalaoException):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Access denied",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "AUTHORIZATION_ERROR")
        self.required_permission = required_permission


class BusinessLogicError(ESalaoException):
    """Raised when business logic constraints are violated."""

    def __init__(
        self,
        message: str = "Business logic violation",
        rule: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "BUSINESS_LOGIC_ERROR")
        self.rule = rule


class PaymentError(ESalaoException):
    """Raised when payment processing fails."""

    def __init__(
        self,
        message: str = "Payment processing failed",
        payment_provider: Optional[str] = None,
        transaction_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "PAYMENT_ERROR")
        self.payment_provider = payment_provider
        self.transaction_id = transaction_id


class ExternalServiceError(ESalaoException):
    """Raised when external service integration fails."""

    def __init__(
        self,
        message: str = "External service error",
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "EXTERNAL_SERVICE_ERROR")
        self.service_name = service_name
        self.status_code = status_code


class DatabaseError(ESalaoException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "DATABASE_ERROR")
        self.operation = operation


class ConfigurationError(ESalaoException):
    """Raised when application configuration is invalid."""

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "CONFIGURATION_ERROR")
        self.config_key = config_key


class RateLimitError(ESalaoException):
    """Raised when rate limits are exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit_type: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "RATE_LIMIT_ERROR")
        self.limit_type = limit_type
        self.retry_after = retry_after


class ConflictError(ESalaoException):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str = "Resource conflict",
        conflicting_resource: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details, "CONFLICT_ERROR")
        self.conflicting_resource = conflicting_resource


# Convenience functions for common error scenarios

def user_not_found(user_id: str) -> NotFoundError:
    """Create a NotFoundError for a missing user."""
    return NotFoundError(
        f"User with ID {user_id} not found",
        resource_type="User",
        resource_id=user_id
    )


def booking_not_found(booking_id: str) -> NotFoundError:
    """Create a NotFoundError for a missing booking."""
    return NotFoundError(
        f"Booking with ID {booking_id} not found",
        resource_type="Booking",
        resource_id=booking_id
    )


def service_not_found(service_id: str) -> NotFoundError:
    """Create a NotFoundError for a missing service."""
    return NotFoundError(
        f"Service with ID {service_id} not found",
        resource_type="Service",
        resource_id=service_id
    )


def professional_not_found(professional_id: str) -> NotFoundError:
    """Create a NotFoundError for a missing professional."""
    return NotFoundError(
        f"Professional with ID {professional_id} not found",
        resource_type="Professional",
        resource_id=professional_id
    )


def insufficient_permissions(required_permission: str) -> AuthorizationError:
    """Create an AuthorizationError for insufficient permissions."""
    return AuthorizationError(
        f"Access denied. Required permission: {required_permission}",
        required_permission=required_permission
    )


def invalid_field(field_name: str, reason: str) -> ValidationError:
    """Create a ValidationError for an invalid field."""
    return ValidationError(
        f"Invalid {field_name}: {reason}",
        field=field_name
    )


def business_rule_violation(rule_name: str, explanation: str) -> BusinessLogicError:
    """Create a BusinessLogicError for a violated business rule."""
    return BusinessLogicError(
        f"Business rule '{rule_name}' violated: {explanation}",
        rule=rule_name
    )
