"""
Payment logging service for comprehensive audit trails.
"""

import json
import traceback
from datetime import datetime
from typing import Optional, Dict, Any, Union
from sqlalchemy.orm import Session

from backend.app.db.models.payment_log import PaymentLog, PaymentLogLevel, PaymentLogType
from backend.app.db.models.payment import Payment, Refund


class PaymentLogger:
    """
    Centralized payment logging service.

    Provides methods to log payment-related events with
    proper sanitization and context tracking.
    """

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        log_type: str,
        message: str,
        level: str = PaymentLogLevel.INFO,
        payment_id: Optional[int] = None,
        refund_id: Optional[int] = None,
        booking_id: Optional[int] = None,
        user_id: Optional[int] = None,
        provider: Optional[str] = None,
        provider_transaction_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        retry_count: int = 0,
        is_sensitive: bool = False,
    ) -> PaymentLog:
        """
        Create a comprehensive payment log entry.

        Args:
            log_type: Type of log entry (see PaymentLogType constants)
            message: Human-readable log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            payment_id: Associated payment ID
            refund_id: Associated refund ID
            booking_id: Associated booking ID
            user_id: Associated user ID
            provider: Payment provider name
            provider_transaction_id: Provider's transaction identifier
            request_data: Sanitized request data
            response_data: Sanitized response data
            error_code: Error code if applicable
            error_message: Error message if applicable
            correlation_id: Request correlation ID for tracing
            session_id: User session ID
            ip_address: Client IP address
            user_agent: Client user agent
            processing_time_ms: Processing time in milliseconds
            retry_count: Number of retries for this operation
            is_sensitive: Flag for sensitive data logs

        Returns:
            Created PaymentLog instance
        """
        # Sanitize sensitive data in request/response
        sanitized_request = self._sanitize_data(request_data) if request_data else None
        sanitized_response = self._sanitize_data(response_data) if response_data else None

        log_entry = PaymentLog(
            payment_id=payment_id,
            refund_id=refund_id,
            booking_id=booking_id,
            user_id=user_id,
            log_type=log_type,
            level=level,
            message=message,
            provider=provider,
            provider_transaction_id=provider_transaction_id,
            request_data=json.dumps(sanitized_request) if sanitized_request else None,
            response_data=json.dumps(sanitized_response) if sanitized_response else None,
            error_code=error_code,
            error_message=error_message,
            correlation_id=correlation_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            processing_time_ms=processing_time_ms,
            retry_count=retry_count,
            is_sensitive=is_sensitive,
            timestamp=datetime.utcnow(),
        )

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)

        return log_entry

    def log_payment_created(
        self,
        payment: Payment,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PaymentLog:
        """Log payment creation event."""
        return self.log(
            log_type=PaymentLogType.PAYMENT_CREATED,
            message=f"Payment created: {payment.external_id}",
            payment_id=payment.id,
            booking_id=payment.booking_id,
            user_id=payment.user_id,
            provider=payment.provider,
            provider_transaction_id=payment.provider_transaction_id,
            correlation_id=correlation_id,
            request_data=context,
        )

    def log_payment_updated(
        self,
        payment: Payment,
        old_status: str,
        new_status: str,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PaymentLog:
        """Log payment status update."""
        return self.log(
            log_type=PaymentLogType.PAYMENT_UPDATED,
            message=f"Payment status changed: {old_status} -> {new_status}",
            payment_id=payment.id,
            booking_id=payment.booking_id,
            user_id=payment.user_id,
            provider=payment.provider,
            provider_transaction_id=payment.provider_transaction_id,
            correlation_id=correlation_id,
            request_data=context,
        )

    def log_provider_call(
        self,
        provider: str,
        operation: str,
        payment_id: Optional[int] = None,
        request_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> PaymentLog:
        """Log payment provider API call."""
        return self.log(
            log_type=PaymentLogType.PROVIDER_CALL,
            message=f"Provider call: {provider}.{operation}",
            payment_id=payment_id,
            provider=provider,
            correlation_id=correlation_id,
            request_data=request_data,
            processing_time_ms=processing_time_ms,
        )

    def log_provider_response(
        self,
        provider: str,
        operation: str,
        payment_id: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        provider_transaction_id: Optional[str] = None,
    ) -> PaymentLog:
        """Log payment provider API response."""
        return self.log(
            log_type=PaymentLogType.PROVIDER_RESPONSE,
            message=f"Provider response: {provider}.{operation}",
            payment_id=payment_id,
            provider=provider,
            provider_transaction_id=provider_transaction_id,
            correlation_id=correlation_id,
            response_data=response_data,
            processing_time_ms=processing_time_ms,
        )

    def log_provider_error(
        self,
        provider: str,
        operation: str,
        error: Exception,
        payment_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        retry_count: int = 0,
    ) -> PaymentLog:
        """Log payment provider error."""
        return self.log(
            log_type=PaymentLogType.PROVIDER_ERROR,
            message=f"Provider error: {provider}.{operation} - {str(error)}",
            level=PaymentLogLevel.ERROR,
            payment_id=payment_id,
            provider=provider,
            correlation_id=correlation_id,
            error_code=type(error).__name__,
            error_message=str(error),
            retry_count=retry_count,
        )

    def log_webhook_received(
        self,
        provider: str,
        event_type: str,
        webhook_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> PaymentLog:
        """Log webhook event receipt."""
        return self.log(
            log_type=PaymentLogType.WEBHOOK_RECEIVED,
            message=f"Webhook received: {provider}.{event_type}",
            provider=provider,
            correlation_id=correlation_id,
            ip_address=ip_address,
            request_data=webhook_data,
        )

    def log_webhook_processed(
        self,
        provider: str,
        event_type: str,
        payment_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
    ) -> PaymentLog:
        """Log successful webhook processing."""
        return self.log(
            log_type=PaymentLogType.WEBHOOK_PROCESSED,
            message=f"Webhook processed: {provider}.{event_type}",
            payment_id=payment_id,
            provider=provider,
            correlation_id=correlation_id,
            processing_time_ms=processing_time_ms,
        )

    def log_refund_created(
        self,
        refund: Refund,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PaymentLog:
        """Log refund creation."""
        return self.log(
            log_type=PaymentLogType.REFUND_CREATED,
            message=f"Refund created: {refund.external_id}",
            payment_id=refund.payment_id,
            refund_id=refund.id,
            correlation_id=correlation_id,
            request_data=context,
        )

    def log_security_violation(
        self,
        violation_type: str,
        details: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> PaymentLog:
        """Log security violations."""
        return self.log(
            log_type=PaymentLogType.SECURITY_VIOLATION,
            message=f"Security violation: {violation_type} - {details}",
            level=PaymentLogLevel.WARNING,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            is_sensitive=True,
        )

    def log_exception(
        self,
        exception: Exception,
        context: Optional[str] = None,
        payment_id: Optional[int] = None,
        correlation_id: Optional[str] = None,
    ) -> PaymentLog:
        """Log unexpected exceptions."""
        message = f"Exception: {type(exception).__name__}"
        if context:
            message = f"{context} - {message}"

        return self.log(
            log_type=PaymentLogType.SYSTEM_ERROR,
            message=message,
            level=PaymentLogLevel.ERROR,
            payment_id=payment_id,
            correlation_id=correlation_id,
            error_code=type(exception).__name__,
            error_message=str(exception),
            response_data={"traceback": traceback.format_exc()},
        )

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from log data.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary with sensitive fields masked
        """
        if not isinstance(data, dict):
            return data

        sanitized = data.copy()

        # List of sensitive field patterns to mask
        sensitive_patterns = [
            'password', 'token', 'secret', 'key', 'authorization',
            'card_number', 'cvv', 'cvc', 'card_holder_name',
            'account_number', 'routing_number', 'ssn', 'cpf',
            'credit_card', 'debit_card', 'bank_account',
        ]

        def mask_sensitive_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    key_lower = key.lower()
                    if any(pattern in key_lower for pattern in sensitive_patterns):
                        # Mask sensitive data
                        if isinstance(value, str) and len(value) > 4:
                            result[key] = f"***{value[-4:]}"
                        else:
                            result[key] = "***"
                    else:
                        result[key] = mask_sensitive_recursive(value)
                return result
            elif isinstance(obj, list):
                return [mask_sensitive_recursive(item) for item in obj]
            else:
                return obj

        return mask_sensitive_recursive(sanitized)


def get_payment_logger(db: Session) -> PaymentLogger:
    """
    Factory function to create a PaymentLogger instance.

    Args:
        db: Database session

    Returns:
        PaymentLogger instance
    """
    return PaymentLogger(db)
