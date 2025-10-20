"""
Payment provider factory for creating provider instances.
"""

from typing import Dict, Type
from backend.app.domain.payments.provider import PaymentProvider
from backend.app.domain.payments.providers.mock import MockPaymentProvider
from backend.app.domain.payments.providers.stripe import StripePaymentProvider


# Registry of available payment providers
PROVIDER_REGISTRY: Dict[str, Type[PaymentProvider]] = {
    "mock": MockPaymentProvider,
    "stripe": StripePaymentProvider,
}


def get_payment_provider(provider_name: str) -> PaymentProvider:
    """
    Factory function to create payment provider instances.

    Args:
        provider_name: Name of the payment provider

    Returns:
        PaymentProvider instance

    Raises:
        ValueError: If provider is not found
    """
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown payment provider: {provider_name}")

    provider_class = PROVIDER_REGISTRY[provider_name]
    return provider_class()


def list_available_providers() -> Dict[str, str]:
    """
    Get list of available payment providers.

    Returns:
        Dictionary mapping provider names to descriptions
    """
    return {
        "mock": "Mock provider for testing and development",
        "stripe": "Stripe payment processor",
    }


def register_provider(name: str, provider_class: Type[PaymentProvider]) -> None:
    """
    Register a new payment provider.

    Args:
        name: Provider name
        provider_class: Provider class
    """
    PROVIDER_REGISTRY[name] = provider_class
