"""
Unit tests for notification system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from backend.app.domain.notifications.templates import (
    NotificationTemplate,
    NotificationContext,
    PaymentConfirmationTemplate,
    PaymentFailedTemplate,
    RefundConfirmationTemplate,
    BookingReminderTemplate,
    BookingCancelledTemplate,
    WelcomeTemplate,
    NotificationTemplateRegistry,
)
from backend.app.domain.notifications.service import (
    NotificationChannel,
    NotificationRequest,
    NotificationResponse,
    EmailNotificationChannel,
    SMSNotificationChannel,
    PushNotificationChannel,
    InAppNotificationChannel,
    NotificationService,
)


class TestNotificationTemplate:
    """Test base notification template."""

    def test_template_is_abstract(self):
        """Test that NotificationTemplate cannot be instantiated directly."""
        with pytest.raises(TypeError):
            NotificationTemplate()


class TestNotificationContext:
    """Test notification context."""

    def test_context_creation(self):
        """Test notification context creation."""
        context = NotificationContext(
            user_id="user_123",
            user_name="João Silva",
            user_email="joao@example.com",
            user_phone="+5511999999999",
        )

        assert context.user_id == "user_123"
        assert context.user_name == "João Silva"
        assert context.user_email == "joao@example.com"
        assert context.user_phone == "+5511999999999"
        assert context.custom_data == {}

    def test_context_with_custom_data(self):
        """Test notification context with custom data."""
        custom_data = {"booking_id": "123", "service_name": "Corte de Cabelo"}

        context = NotificationContext(
            user_id="user_123",
            user_name="João Silva",
            user_email="joao@example.com",
            custom_data=custom_data,
        )

        assert context.custom_data == custom_data


class TestPaymentConfirmationTemplate:
    """Test payment confirmation template."""

    def setup_method(self):
        """Set up test fixtures."""
        self.template = PaymentConfirmationTemplate()

    def test_template_name(self):
        """Test template name."""
        assert self.template.get_name() == "payment_confirmation"

    def test_render_email(self):
        """Test rendering email content."""
        context = NotificationContext(
            user_id="user_123",
            user_name="João Silva",
            user_email="joao@example.com",
            custom_data={
                "payment_amount": Decimal("100.00"),
                "payment_method": "credit_card",
                "booking_service": "Corte de Cabelo",
                "booking_date": "2023-12-25",
                "booking_time": "14:00",
            }
        )

        email_content = self.template.render_email(context)

        assert email_content["subject"] == "Pagamento Confirmado - ESalão"
        assert "João Silva" in email_content["html"]
        assert "R$ 100,00" in email_content["html"]
        assert "Corte de Cabelo" in email_content["html"]
        assert "25/12/2023" in email_content["html"]
        assert "14:00" in email_content["html"]
        assert "Cartão de Crédito" in email_content["html"]

    def test_render_sms(self):
        """Test rendering SMS content."""
        context = NotificationContext(
            user_id="user_123",
            user_name="João Silva",
            custom_data={
                "payment_amount": Decimal("75.50"),
                "booking_service": "Manicure",
            }
        )

        sms_content = self.template.render_sms(context)

        assert "João" in sms_content
        assert "R$ 75,50" in sms_content
        assert "Manicure" in sms_content
        assert "confirmado" in sms_content.lower()

    def test_render_push(self):
        """Test rendering push notification content."""
        context = NotificationContext(
            user_id="user_123",
            custom_data={
                "payment_amount": Decimal("50.00"),
            }
        )

        push_content = self.template.render_push(context)

        assert push_content["title"] == "Pagamento Confirmado!"
        assert "R$ 50,00" in push_content["body"]

    def test_render_in_app(self):
        """Test rendering in-app notification content."""
        context = NotificationContext(
            user_id="user_123",
            custom_data={
                "payment_amount": Decimal("120.00"),
                "booking_service": "Corte + Barba",
            }
        )

        in_app_content = self.template.render_in_app(context)

        assert in_app_content["title"] == "Pagamento Confirmado"
        assert "R$ 120,00" in in_app_content["message"]
        assert "Corte + Barba" in in_app_content["message"]
        assert in_app_content["type"] == "success"


class TestPaymentFailedTemplate:
    """Test payment failed template."""

    def setup_method(self):
        """Set up test fixtures."""
        self.template = PaymentFailedTemplate()

    def test_template_name(self):
        """Test template name."""
        assert self.template.get_name() == "payment_failed"

    def test_render_email(self):
        """Test rendering email content."""
        context = NotificationContext(
            user_id="user_123",
            user_name="Maria Santos",
            user_email="maria@example.com",
            custom_data={
                "payment_amount": Decimal("80.00"),
                "booking_service": "Escova Progressiva",
                "failure_reason": "Cartão recusado",
            }
        )

        email_content = self.template.render_email(context)

        assert email_content["subject"] == "Problema no Pagamento - ESalão"
        assert "Maria Santos" in email_content["html"]
        assert "R$ 80,00" in email_content["html"]
        assert "Escova Progressiva" in email_content["html"]
        assert "Cartão recusado" in email_content["html"]

    def test_render_push(self):
        """Test rendering push notification content."""
        context = NotificationContext(
            user_id="user_123",
            custom_data={
                "failure_reason": "Saldo insuficiente",
            }
        )

        push_content = self.template.render_push(context)

        assert push_content["title"] == "Problema no Pagamento"
        assert "Saldo insuficiente" in push_content["body"]


class TestTemplateRegistry:
    """Test template registry."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = NotificationTemplateRegistry()

    def test_get_existing_template(self):
        """Test getting existing template."""
        template = self.registry.get_template("payment_confirmation")
        assert isinstance(template, PaymentConfirmationTemplate)

        template = self.registry.get_template("payment_failed")
        assert isinstance(template, PaymentFailedTemplate)

        template = self.registry.get_template("refund_confirmation")
        assert isinstance(template, RefundConfirmationTemplate)

        template = self.registry.get_template("booking_reminder")
        assert isinstance(template, BookingReminderTemplate)

        template = self.registry.get_template("booking_cancelled")
        assert isinstance(template, BookingCancelledTemplate)

        template = self.registry.get_template("welcome")
        assert isinstance(template, WelcomeTemplate)

    def test_get_nonexistent_template(self):
        """Test getting non-existent template raises error."""
        with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
            self.registry.get_template("nonexistent")

    def test_list_templates(self):
        """Test listing all available templates."""
        templates = self.registry.list_templates()

        expected_templates = {
            "payment_confirmation",
            "payment_failed",
            "refund_confirmation",
            "booking_reminder",
            "booking_cancelled",
            "welcome",
        }

        assert set(templates) == expected_templates


class TestNotificationChannels:
    """Test notification channels."""

    def test_notification_channel_is_abstract(self):
        """Test that NotificationChannel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            NotificationChannel()

    def test_email_channel_name(self):
        """Test email channel name."""
        channel = EmailNotificationChannel()
        assert channel.get_name() == "email"

    def test_sms_channel_name(self):
        """Test SMS channel name."""
        channel = SMSNotificationChannel()
        assert channel.get_name() == "sms"

    def test_push_channel_name(self):
        """Test push channel name."""
        channel = PushNotificationChannel()
        assert channel.get_name() == "push"

    def test_in_app_channel_name(self):
        """Test in-app channel name."""
        channel = InAppNotificationChannel()
        assert channel.get_name() == "in_app"

    @pytest.mark.asyncio
    async def test_email_channel_send(self):
        """Test email channel send method."""
        channel = EmailNotificationChannel()

        content = {
            "subject": "Test Subject",
            "html": "<p>Test HTML</p>",
            "text": "Test Text",
        }

        context = NotificationContext(
            user_id="user_123",
            user_email="test@example.com",
        )

        # Mock the actual email sending
        with patch.object(channel, '_send_email') as mock_send:
            mock_send.return_value = True

            result = await channel.send(content, context)

            assert result.success is True
            assert result.channel == "email"
            mock_send.assert_called_once_with(
                "test@example.com",
                "Test Subject",
                "<p>Test HTML</p>",
                "Test Text"
            )

    @pytest.mark.asyncio
    async def test_sms_channel_send(self):
        """Test SMS channel send method."""
        channel = SMSNotificationChannel()

        content = "Test SMS message"

        context = NotificationContext(
            user_id="user_123",
            user_phone="+5511999999999",
        )

        # Mock the actual SMS sending
        with patch.object(channel, '_send_sms') as mock_send:
            mock_send.return_value = True

            result = await channel.send(content, context)

            assert result.success is True
            assert result.channel == "sms"
            mock_send.assert_called_once_with("+5511999999999", "Test SMS message")

    @pytest.mark.asyncio
    async def test_channel_send_missing_data(self):
        """Test channel send with missing required data."""
        channel = EmailNotificationChannel()

        content = {
            "subject": "Test Subject",
            "html": "<p>Test HTML</p>",
        }

        # Context without email
        context = NotificationContext(
            user_id="user_123",
        )

        result = await channel.send(content, context)

        assert result.success is False
        assert "No email address" in result.error


class TestNotificationService:
    """Test notification service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NotificationService()

    @pytest.mark.asyncio
    async def test_send_notification_single_channel(self):
        """Test sending notification to single channel."""
        request = NotificationRequest(
            template_name="payment_confirmation",
            channels=["email"],
            context=NotificationContext(
                user_id="user_123",
                user_name="João Silva",
                user_email="joao@example.com",
                custom_data={
                    "payment_amount": Decimal("100.00"),
                    "booking_service": "Corte de Cabelo",
                }
            )
        )

        # Mock email channel
        with patch.object(self.service.channels["email"], 'send') as mock_send:
            mock_response = NotificationResponse(
                success=True,
                channel="email",
                message_id="msg_123"
            )
            mock_send.return_value = mock_response

            responses = await self.service.send_notification(request)

            assert len(responses) == 1
            assert responses[0].success is True
            assert responses[0].channel == "email"
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_multiple_channels(self):
        """Test sending notification to multiple channels."""
        request = NotificationRequest(
            template_name="payment_failed",
            channels=["email", "push"],
            context=NotificationContext(
                user_id="user_123",
                user_name="Maria Santos",
                user_email="maria@example.com",
                custom_data={
                    "payment_amount": Decimal("50.00"),
                    "failure_reason": "Cartão recusado",
                }
            )
        )

        # Mock channels
        with patch.object(self.service.channels["email"], 'send') as mock_email, \
             patch.object(self.service.channels["push"], 'send') as mock_push:

            mock_email.return_value = NotificationResponse(
                success=True, channel="email", message_id="email_123"
            )
            mock_push.return_value = NotificationResponse(
                success=True, channel="push", message_id="push_123"
            )

            responses = await self.service.send_notification(request)

            assert len(responses) == 2
            assert all(r.success for r in responses)

            channels = [r.channel for r in responses]
            assert "email" in channels
            assert "push" in channels

    @pytest.mark.asyncio
    async def test_send_notification_invalid_template(self):
        """Test sending notification with invalid template."""
        request = NotificationRequest(
            template_name="nonexistent_template",
            channels=["email"],
            context=NotificationContext(user_id="user_123")
        )

        with pytest.raises(ValueError, match="Template 'nonexistent_template' not found"):
            await self.service.send_notification(request)

    @pytest.mark.asyncio
    async def test_send_notification_invalid_channel(self):
        """Test sending notification with invalid channel."""
        request = NotificationRequest(
            template_name="payment_confirmation",
            channels=["invalid_channel"],
            context=NotificationContext(user_id="user_123")
        )

        with pytest.raises(ValueError, match="Channel 'invalid_channel' not supported"):
            await self.service.send_notification(request)

    @pytest.mark.asyncio
    async def test_send_notification_partial_failure(self):
        """Test sending notification with partial failures."""
        request = NotificationRequest(
            template_name="welcome",
            channels=["email", "sms"],
            context=NotificationContext(
                user_id="user_123",
                user_name="Pedro Costa",
                user_email="pedro@example.com",
                # Missing phone number for SMS
            )
        )

        # Mock channels
        with patch.object(self.service.channels["email"], 'send') as mock_email, \
             patch.object(self.service.channels["sms"], 'send') as mock_sms:

            mock_email.return_value = NotificationResponse(
                success=True, channel="email", message_id="email_123"
            )
            mock_sms.return_value = NotificationResponse(
                success=False, channel="sms", error="No phone number provided"
            )

            responses = await self.service.send_notification(request)

            assert len(responses) == 2

            email_response = next(r for r in responses if r.channel == "email")
            sms_response = next(r for r in responses if r.channel == "sms")

            assert email_response.success is True
            assert sms_response.success is False
            assert "No phone number" in sms_response.error

    def test_get_available_channels(self):
        """Test getting available channels."""
        channels = self.service.get_available_channels()

        expected_channels = {"email", "sms", "push", "in_app"}
        assert set(channels) == expected_channels

    def test_get_available_templates(self):
        """Test getting available templates."""
        templates = self.service.get_available_templates()

        expected_templates = {
            "payment_confirmation",
            "payment_failed",
            "refund_confirmation",
            "booking_reminder",
            "booking_cancelled",
            "welcome",
        }

        assert set(templates) == expected_templates
