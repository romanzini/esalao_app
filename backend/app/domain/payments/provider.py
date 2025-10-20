"""
Payment Provider Interface

This module defines the abstract interface for payment providers.
All payment gateways (Stripe, PagarMe, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class PaymentMethod(Enum):
    """Supported payment methods"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PIX = "pix"
    BANK_SLIP = "bank_slip"


class PaymentStatus(Enum):
    """Payment status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class PaymentRequest:
    """Payment request data"""
    amount: Decimal
    currency: str = "BRL"
    payment_method: PaymentMethod = PaymentMethod.PIX
    customer_id: str = ""
    customer_email: str = ""
    customer_name: str = ""
    description: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PaymentResponse:
    """Payment response data"""
    provider_payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    created_at: datetime
    updated_at: datetime
    provider_data: Dict[str, Any] = None
    payment_url: Optional[str] = None  # For PIX QR code or checkout URL

    def __post_init__(self):
        if self.provider_data is None:
            self.provider_data = {}


@dataclass
class RefundRequest:
    """Refund request data"""
    provider_payment_id: str
    amount: Optional[Decimal] = None  # None for full refund
    reason: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class RefundResponse:
    """Refund response data"""
    provider_refund_id: str
    provider_payment_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    created_at: datetime
    provider_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.provider_data is None:
            self.provider_data = {}


@dataclass
class WebhookEvent:
    """Webhook event data"""
    provider_event_id: str
    event_type: str
    provider_payment_id: str
    status: PaymentStatus
    timestamp: datetime
    provider_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.provider_data is None:
            self.provider_data = {}


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.

    All payment gateways must implement these methods to ensure
    consistent behavior across different providers.
    """

    @abstractmethod
    async def create_payment(self, request: PaymentRequest) -> PaymentResponse:
        """
        Create a new payment with the provider.

        Args:
            request: Payment request data

        Returns:
            PaymentResponse with provider payment ID and status

        Raises:
            PaymentProviderError: If payment creation fails
        """
        pass

    @abstractmethod
    async def get_payment_status(self, provider_payment_id: str) -> PaymentResponse:
        """
        Get current payment status from provider.

        Args:
            provider_payment_id: Provider's payment identifier

        Returns:
            PaymentResponse with current status

        Raises:
            PaymentProviderError: If status check fails
        """
        pass

    @abstractmethod
    async def cancel_payment(self, provider_payment_id: str) -> PaymentResponse:
        """
        Cancel a pending payment.

        Args:
            provider_payment_id: Provider's payment identifier

        Returns:
            PaymentResponse with canceled status

        Raises:
            PaymentProviderError: If cancellation fails
        """
        pass

    @abstractmethod
    async def create_refund(self, request: RefundRequest) -> RefundResponse:
        """
        Create a refund for an existing payment.

        Args:
            request: Refund request data

        Returns:
            RefundResponse with refund details

        Raises:
            PaymentProviderError: If refund creation fails
        """
        pass

    @abstractmethod
    async def get_refund_status(self, provider_refund_id: str) -> RefundResponse:
        """
        Get current refund status from provider.

        Args:
            provider_refund_id: Provider's refund identifier

        Returns:
            RefundResponse with current status

        Raises:
            PaymentProviderError: If status check fails
        """
        pass

    @abstractmethod
    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """
        Validate webhook signature for security.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature from headers

        Returns:
            True if signature is valid, False otherwise
        """
        pass

    @abstractmethod
    def parse_webhook(self, payload: Dict[str, Any]) -> WebhookEvent:
        """
        Parse webhook payload into standardized event.

        Args:
            payload: Webhook payload data

        Returns:
            WebhookEvent with standardized data

        Raises:
            PaymentProviderError: If parsing fails
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'stripe', 'pagarme')"""
        pass

    @property
    @abstractmethod
    def supported_methods(self) -> list[PaymentMethod]:
        """Return list of supported payment methods"""
        pass


class PaymentProviderError(Exception):
    """Exception raised by payment providers"""

    def __init__(
        self,
        message: str,
        provider_error_code: Optional[str] = None,
        provider_error_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.provider_error_code = provider_error_code
        self.provider_error_data = provider_error_data or {}


class PaymentProviderUnavailableError(PaymentProviderError):
    """Exception for when payment provider is temporarily unavailable"""
    pass


class PaymentProviderConfigurationError(PaymentProviderError):
    """Exception for payment provider configuration issues"""
    pass
