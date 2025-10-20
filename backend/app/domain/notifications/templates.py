"""
Notification templates for payment and booking events.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationPriority(Enum):
    """Notification priorities."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationContext:
    """Context data for notification rendering."""

    # User information
    user_name: str
    user_email: str
    user_phone: Optional[str] = None

    # Business context
    salon_name: str = "eSalão"
    salon_logo_url: Optional[str] = None
    salon_phone: Optional[str] = None
    salon_address: Optional[str] = None

    # Payment context
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "BRL"
    payment_method: Optional[str] = None

    # Booking context
    booking_id: Optional[str] = None
    service_name: Optional[str] = None
    professional_name: Optional[str] = None
    booking_date: Optional[datetime] = None
    booking_time: Optional[str] = None

    # Refund context
    refund_id: Optional[str] = None
    refund_amount: Optional[float] = None
    refund_reason: Optional[str] = None

    # Additional context
    extra_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_data is None:
            self.extra_data = {}


class NotificationTemplate(ABC):
    """Base class for notification templates."""

    @abstractmethod
    def get_subject(self, context: NotificationContext) -> str:
        """Get notification subject/title."""
        pass

    @abstractmethod
    def get_body(self, context: NotificationContext) -> str:
        """Get notification body content."""
        pass

    @abstractmethod
    def get_priority(self) -> NotificationPriority:
        """Get notification priority."""
        pass

    @abstractmethod
    def get_supported_types(self) -> list[NotificationType]:
        """Get supported notification types."""
        pass


class PaymentConfirmationTemplate(NotificationTemplate):
    """Template for payment confirmation notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"✅ Pagamento confirmado - {context.salon_name}"

    def get_body(self, context: NotificationContext) -> str:
        return f"""
Olá {context.user_name}!

Seu pagamento foi confirmado com sucesso! 🎉

📋 Detalhes do Pagamento:
• ID do Pagamento: {context.payment_id}
• Valor: R$ {context.amount:.2f}
• Método: {context.payment_method}

🗓️ Serviço Agendado:
• Serviço: {context.service_name}
• Profissional: {context.professional_name}
• Data: {context.booking_date.strftime("%d/%m/%Y") if context.booking_date else "N/A"}
• Horário: {context.booking_time}

📍 Local:
{context.salon_name}
{context.salon_address or "Endereço disponível no app"}

📞 Contato: {context.salon_phone or "Disponível no app"}

Obrigado por escolher o {context.salon_name}!

Atenciosamente,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.HIGH

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP]


class PaymentFailedTemplate(NotificationTemplate):
    """Template for payment failure notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"❌ Problema no pagamento - {context.salon_name}"

    def get_body(self, context: NotificationContext) -> str:
        return f"""
Olá {context.user_name},

Infelizmente, houve um problema com o processamento do seu pagamento.

📋 Detalhes:
• ID do Pagamento: {context.payment_id}
• Valor: R$ {context.amount:.2f}
• Método: {context.payment_method}

🔄 O que fazer agora:
1. Verifique os dados do seu cartão/conta
2. Confirme se há saldo/limite disponível
3. Tente realizar o pagamento novamente
4. Entre em contato conosco se precisar de ajuda

📞 Suporte: {context.salon_phone or "Disponível no app"}

Não se preocupe, sua reserva está mantida temporariamente.
Você pode tentar efetuar o pagamento novamente através do app.

Atenciosamente,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.HIGH

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP]


class RefundConfirmationTemplate(NotificationTemplate):
    """Template for refund confirmation notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"💰 Reembolso em processamento - {context.salon_name}"

    def get_body(self, context: NotificationContext) -> str:
        return f"""
Olá {context.user_name}!

Seu reembolso está sendo processado.

📋 Detalhes do Reembolso:
• ID do Reembolso: {context.refund_id}
• Valor: R$ {context.refund_amount:.2f}
• Pagamento Original: {context.payment_id}
• Motivo: {context.refund_reason}

⏰ Prazo para Processamento:
• Cartão de Crédito: 2-10 dias úteis
• Cartão de Débito: 1-5 dias úteis
• PIX: 1-2 dias úteis

O valor será creditado na mesma forma de pagamento utilizada na compra.

📞 Dúvidas? Entre em contato: {context.salon_phone or "Disponível no app"}

Obrigado pela compreensão!

Atenciosamente,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.NORMAL

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP]


class BookingReminderTemplate(NotificationTemplate):
    """Template for booking reminder notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"🕐 Lembrete: Seu agendamento é amanhã - {context.salon_name}"

    def get_body(self, context: NotificationContext) -> str:
        hours_before = context.extra_data.get('hours_before', 24)

        if hours_before <= 2:
            urgency = "HOJE em algumas horas"
            emoji = "🚨"
        elif hours_before <= 24:
            urgency = "amanhã"
            emoji = "📅"
        else:
            urgency = f"em {hours_before//24} dias"
            emoji = "📋"

        return f"""
{emoji} Olá {context.user_name}!

Lembrando que você tem um agendamento {urgency}:

🗓️ Detalhes do Agendamento:
• Serviço: {context.service_name}
• Profissional: {context.professional_name}
• Data: {context.booking_date.strftime("%d/%m/%Y") if context.booking_date else "N/A"}
• Horário: {context.booking_time}
• ID: {context.booking_id}

📍 Local:
{context.salon_name}
{context.salon_address or "Endereço disponível no app"}

⚠️ Importante:
• Chegue 10 minutos antes
• Traga um documento com foto
• Em caso de imprevistos, avise com antecedência

📞 Contato: {context.salon_phone or "Disponível no app"}

Aguardamos você!

Atenciosamente,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.NORMAL

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP]


class BookingCancelledTemplate(NotificationTemplate):
    """Template for booking cancellation notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"❌ Agendamento cancelado - {context.salon_name}"

    def get_body(self, context: NotificationContext) -> str:
        return f"""
Olá {context.user_name},

Seu agendamento foi cancelado.

📋 Detalhes do Agendamento Cancelado:
• Serviço: {context.service_name}
• Profissional: {context.professional_name}
• Data: {context.booking_date.strftime("%d/%m/%Y") if context.booking_date else "N/A"}
• Horário: {context.booking_time}
• ID: {context.booking_id}

💰 Reembolso:
{f"Um reembolso de R$ {context.refund_amount:.2f} será processado automaticamente." if context.refund_amount else "Não há valores a reembolsar."}

🔄 Reagendar:
Você pode fazer um novo agendamento a qualquer momento através do nosso app.

📞 Dúvidas? Entre em contato: {context.salon_phone or "Disponível no app"}

Esperamos atendê-lo em breve!

Atenciosamente,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.HIGH

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.SMS, NotificationType.PUSH, NotificationType.IN_APP]


class WelcomeTemplate(NotificationTemplate):
    """Template for welcome notifications."""

    def get_subject(self, context: NotificationContext) -> str:
        return f"🎉 Bem-vindo ao {context.salon_name}!"

    def get_body(self, context: NotificationContext) -> str:
        return f"""
Olá {context.user_name}!

Seja muito bem-vindo ao {context.salon_name}! 🎉

Agora você pode:
✨ Agendar seus serviços favoritos
💳 Pagar de forma segura e prática
📱 Gerenciar tudo pelo app
🎁 Acumular pontos de fidelidade

🌟 Nossos Serviços:
• Cortes e penteados
• Coloração e mechas
• Tratamentos capilares
• Manicure e pedicure
• E muito mais!

📍 Nos encontre em:
{context.salon_address or "Endereço disponível no app"}

📞 Contato: {context.salon_phone or "Disponível no app"}

Faça já seu primeiro agendamento e descubra por que somos referência em beleza!

Com carinho,
Equipe {context.salon_name}
        """.strip()

    def get_priority(self) -> NotificationPriority:
        return NotificationPriority.LOW

    def get_supported_types(self) -> list[NotificationType]:
        return [NotificationType.EMAIL, NotificationType.PUSH, NotificationType.IN_APP]


class NotificationTemplateRegistry:
    """Registry for notification templates."""

    _templates = {
        "payment_confirmation": PaymentConfirmationTemplate(),
        "payment_failed": PaymentFailedTemplate(),
        "refund_confirmation": RefundConfirmationTemplate(),
        "booking_reminder": BookingReminderTemplate(),
        "booking_cancelled": BookingCancelledTemplate(),
        "welcome": WelcomeTemplate(),
    }

    @classmethod
    def get_template(cls, template_name: str) -> NotificationTemplate:
        """Get template by name."""
        if template_name not in cls._templates:
            raise ValueError(f"Template '{template_name}' not found")
        return cls._templates[template_name]

    @classmethod
    def register_template(cls, name: str, template: NotificationTemplate) -> None:
        """Register a new template."""
        cls._templates[name] = template

    @classmethod
    def list_templates(cls) -> list[str]:
        """List all available template names."""
        return list(cls._templates.keys())


# Helper functions for easy template access
def get_payment_confirmation_template() -> PaymentConfirmationTemplate:
    """Get payment confirmation template."""
    return NotificationTemplateRegistry.get_template("payment_confirmation")


def get_payment_failed_template() -> PaymentFailedTemplate:
    """Get payment failed template."""
    return NotificationTemplateRegistry.get_template("payment_failed")


def get_refund_confirmation_template() -> RefundConfirmationTemplate:
    """Get refund confirmation template."""
    return NotificationTemplateRegistry.get_template("refund_confirmation")


def get_booking_reminder_template() -> BookingReminderTemplate:
    """Get booking reminder template."""
    return NotificationTemplateRegistry.get_template("booking_reminder")


def get_booking_cancelled_template() -> BookingCancelledTemplate:
    """Get booking cancelled template."""
    return NotificationTemplateRegistry.get_template("booking_cancelled")


def get_welcome_template() -> WelcomeTemplate:
    """Get welcome template."""
    return NotificationTemplateRegistry.get_template("welcome")
