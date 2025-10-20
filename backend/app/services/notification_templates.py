"""
Default notification templates for eSalão application.

This module contains predefined notification templates for all supported
event types and channels, with proper Portuguese localization.
"""

from typing import Dict, List
from backend.app.db.models.notifications import NotificationChannel, NotificationEventType, NotificationPriority


# ==================== Email Templates ====================

EMAIL_TEMPLATES = {
    # Booking Events
    "booking_confirmed_email": {
        "name": "booking_confirmed_email",
        "event_type": NotificationEventType.BOOKING_CONFIRMED.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "✅ Agendamento Confirmado - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Seu agendamento foi confirmado com sucesso! 🎉

📋 **Detalhes do Agendamento:**
• Serviço: {{service_name}}
• Data: {{appointment_date}}
• Horário: {{appointment_time}}
• Profissional: {{professional_name}}
• Unidade: {{unit_name}}
• Valor: R$ {{service_price}}

📍 **Endereço:**
{{unit_address}}

⏰ **Lembrete:**
Chegue com 10 minutos de antecedência para não perder seu horário.

❌ **Cancelamentos:**
Cancelamentos devem ser feitos com pelo menos {{cancellation_hours}} horas de antecedência para evitar taxas.

Estamos ansiosos para recebê-lo(a)!

Atenciosamente,
Equipe {{salon_name}}

---
📱 Para reagendar ou cancelar, acesse: {{app_url}}
📞 Dúvidas? Entre em contato: {{contact_phone}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data do agendamento (DD/MM/AAAA)",
            "appointment_time": "Horário do agendamento (HH:MM)",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "unit_address": "Endereço da unidade",
            "service_price": "Preço do serviço",
            "cancellation_hours": "Horas para cancelamento",
            "app_url": "URL do aplicativo",
            "contact_phone": "Telefone de contato"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "booking_reminder_email": {
        "name": "booking_reminder_email",
        "event_type": NotificationEventType.BOOKING_REMINDER.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "⏰ Lembrete: Seu agendamento é {{reminder_period}} - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Este é um lembrete do seu agendamento {{reminder_period}}! ⏰

📋 **Detalhes do Agendamento:**
• Serviço: {{service_name}}
• Data: {{appointment_date}}
• Horário: {{appointment_time}}
• Profissional: {{professional_name}}
• Unidade: {{unit_name}}

📍 **Endereço:**
{{unit_address}}

💡 **Dicas importantes:**
• Chegue com 10 minutos de antecedência
• Traga um documento de identificação
• Em caso de atraso, entre em contato conosco

⚠️ **Precisa cancelar ou reagendar?**
Faça isso com antecedência para evitar taxas através do nosso app: {{app_url}}

Nos vemos em breve!

Atenciosamente,
Equipe {{salon_name}}

---
📞 Contato: {{contact_phone}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data do agendamento",
            "appointment_time": "Horário do agendamento",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "unit_address": "Endereço da unidade",
            "reminder_period": "Período do lembrete (hoje, amanhã, em 1 hora)",
            "app_url": "URL do aplicativo",
            "contact_phone": "Telefone de contato"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "booking_cancelled_email": {
        "name": "booking_cancelled_email",
        "event_type": NotificationEventType.BOOKING_CANCELLED.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "❌ Agendamento Cancelado - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Seu agendamento foi cancelado conforme solicitado.

📋 **Agendamento Cancelado:**
• Serviço: {{service_name}}
• Data: {{appointment_date}}
• Horário: {{appointment_time}}
• Profissional: {{professional_name}}

💰 **Informações Financeiras:**
{{#refund_info}}
• Valor reembolsado: R$ {{refund_amount}}
• Taxa de cancelamento: R$ {{cancellation_fee}}
• O reembolso será processado em até {{refund_days}} dias úteis
{{/refund_info}}
{{#no_refund}}
• Cancelamento após o prazo limite - sem reembolso
{{/no_refund}}

📱 **Novo agendamento:**
Você pode fazer um novo agendamento a qualquer momento através do nosso app: {{app_url}}

Esperamos vê-lo(a) em breve!

Atenciosamente,
Equipe {{salon_name}}

---
📞 Dúvidas? Entre em contato: {{contact_phone}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data do agendamento",
            "appointment_time": "Horário do agendamento",
            "professional_name": "Nome do profissional",
            "refund_amount": "Valor do reembolso",
            "cancellation_fee": "Taxa de cancelamento",
            "refund_days": "Dias para reembolso",
            "app_url": "URL do aplicativo",
            "contact_phone": "Telefone de contato"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "payment_received_email": {
        "name": "payment_received_email",
        "event_type": NotificationEventType.PAYMENT_RECEIVED.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "💳 Pagamento Confirmado - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Seu pagamento foi processado com sucesso! ✅

💳 **Detalhes do Pagamento:**
• Valor: R$ {{payment_amount}}
• Método: {{payment_method}}
• Data: {{payment_date}}
• ID da Transação: {{transaction_id}}

📋 **Serviços Pagos:**
{{#services}}
• {{service_name}} - R$ {{service_amount}}
{{/services}}

🧾 **Recibo:**
Este e-mail serve como comprovante de pagamento. Guarde-o para seus registros.

📱 **Próximos passos:**
Seu agendamento está confirmado e você pode acompanhar todos os detalhes no app: {{app_url}}

Obrigado por escolher nossos serviços!

Atenciosamente,
Equipe {{salon_name}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "payment_amount": "Valor do pagamento",
            "payment_method": "Método de pagamento",
            "payment_date": "Data do pagamento",
            "transaction_id": "ID da transação",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "points_earned_email": {
        "name": "points_earned_email",
        "event_type": NotificationEventType.POINTS_EARNED.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "🎁 Você ganhou {{points_earned}} pontos! - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Parabéns! Você acaba de ganhar pontos em nosso programa de fidelidade! 🎉

⭐ **Pontos Ganhos:**
• +{{points_earned}} pontos
• Motivo: {{earning_reason}}

💳 **Seu Saldo Atual:**
• Total de pontos: {{current_balance}} pontos
• Nível atual: {{current_tier}}

🎁 **Como usar seus pontos:**
{{#available_rewards}}
• {{reward_name}} - {{reward_points}} pontos
{{/available_rewards}}

📈 **Próximo nível:**
{{#next_tier}}
Faltam apenas {{points_to_next_tier}} pontos para alcançar o nível {{next_tier_name}} e desbloquear benefícios exclusivos!
{{/next_tier}}

🛍️ **Resgatar pontos:**
Acesse o app para ver todas as recompensas disponíveis: {{app_url}}

Continue acumulando pontos e aproveite nossos benefícios exclusivos!

Atenciosamente,
Equipe {{salon_name}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "points_earned": "Pontos ganhos",
            "earning_reason": "Motivo dos pontos",
            "current_balance": "Saldo atual de pontos",
            "current_tier": "Nível atual",
            "points_to_next_tier": "Pontos para próximo nível",
            "next_tier_name": "Nome do próximo nível",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "slot_available_email": {
        "name": "slot_available_email",
        "event_type": NotificationEventType.SLOT_AVAILABLE.value,
        "channel": NotificationChannel.EMAIL.value,
        "subject": "🎯 Vaga disponível para {{service_name}} - {{salon_name}}",
        "body_template": """Olá {{user_name}},

Boa notícia! Uma vaga ficou disponível para o serviço que você estava esperando! ⚡

📋 **Vaga Disponível:**
• Serviço: {{service_name}}
• Data: {{available_date}}
• Horário: {{available_time}}
• Profissional: {{professional_name}}
• Unidade: {{unit_name}}

⏱️ **Ação necessária:**
Esta vaga é sua por tempo limitado! Você tem até {{expiry_time}} para confirmar seu agendamento.

✅ **Como agendar:**
1. Acesse nosso app: {{app_url}}
2. Vá para "Lista de Espera"
3. Confirme seu agendamento

❌ **Não quer mais esta vaga?**
Você pode sair da lista de espera a qualquer momento no app.

Não perca esta oportunidade!

Atenciosamente,
Equipe {{salon_name}}

---
📞 Precisa de ajuda? Entre em contato: {{contact_phone}}""",
        "variables": {
            "user_name": "Nome do usuário",
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "available_date": "Data disponível",
            "available_time": "Horário disponível",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "expiry_time": "Tempo limite para confirmação",
            "app_url": "URL do aplicativo",
            "contact_phone": "Telefone de contato"
        },
        "priority": NotificationPriority.URGENT.value,
        "locale": "pt_BR"
    }
}


# ==================== SMS Templates ====================

SMS_TEMPLATES = {
    "booking_confirmed_sms": {
        "name": "booking_confirmed_sms",
        "event_type": NotificationEventType.BOOKING_CONFIRMED.value,
        "channel": NotificationChannel.SMS.value,
        "subject": None,
        "body_template": """✅ {{salon_name}}
Agendamento confirmado!

📋 {{service_name}}
📅 {{appointment_date}} às {{appointment_time}}
👤 {{professional_name}}
📍 {{unit_name}}

Chegue 10min antes.
App: {{app_url}}""",
        "variables": {
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data (DD/MM)",
            "appointment_time": "Horário (HH:MM)",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "booking_reminder_sms": {
        "name": "booking_reminder_sms",
        "event_type": NotificationEventType.BOOKING_REMINDER.value,
        "channel": NotificationChannel.SMS.value,
        "subject": None,
        "body_template": """⏰ {{salon_name}}
Lembrete: Agendamento {{reminder_period}}

📋 {{service_name}}
📅 {{appointment_date}} às {{appointment_time}}
👤 {{professional_name}}
📍 {{unit_name}}

Nos vemos em breve!
App: {{app_url}}""",
        "variables": {
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data (DD/MM)",
            "appointment_time": "Horário (HH:MM)",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "reminder_period": "Período (hoje, amanhã, em 1h)",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "payment_received_sms": {
        "name": "payment_received_sms",
        "event_type": NotificationEventType.PAYMENT_RECEIVED.value,
        "channel": NotificationChannel.SMS.value,
        "subject": None,
        "body_template": """💳 {{salon_name}}
Pagamento confirmado!

💰 R$ {{payment_amount}}
📅 {{payment_date}}
🆔 {{transaction_id}}

Agendamento confirmado ✅
App: {{app_url}}""",
        "variables": {
            "salon_name": "Nome do salão",
            "payment_amount": "Valor do pagamento",
            "payment_date": "Data do pagamento",
            "transaction_id": "ID da transação",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "points_earned_sms": {
        "name": "points_earned_sms",
        "event_type": NotificationEventType.POINTS_EARNED.value,
        "channel": NotificationChannel.SMS.value,
        "subject": None,
        "body_template": """🎁 {{salon_name}}
+{{points_earned}} pontos ganhos!

⭐ Total: {{current_balance}} pontos
🏆 Nível: {{current_tier}}

Resgatar: {{app_url}}""",
        "variables": {
            "salon_name": "Nome do salão",
            "points_earned": "Pontos ganhos",
            "current_balance": "Saldo atual",
            "current_tier": "Nível atual",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "slot_available_sms": {
        "name": "slot_available_sms",
        "event_type": NotificationEventType.SLOT_AVAILABLE.value,
        "channel": NotificationChannel.SMS.value,
        "subject": None,
        "body_template": """🎯 {{salon_name}}
VAGA DISPONÍVEL!

📋 {{service_name}}
📅 {{available_date}} às {{available_time}}
👤 {{professional_name}}

⏱️ Confirme até {{expiry_time}}
App: {{app_url}}""",
        "variables": {
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "available_date": "Data disponível",
            "available_time": "Horário disponível",
            "professional_name": "Nome do profissional",
            "expiry_time": "Tempo limite",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.URGENT.value,
        "locale": "pt_BR"
    }
}


# ==================== Push Notification Templates ====================

PUSH_TEMPLATES = {
    "booking_confirmed_push": {
        "name": "booking_confirmed_push",
        "event_type": NotificationEventType.BOOKING_CONFIRMED.value,
        "channel": NotificationChannel.PUSH.value,
        "subject": "Agendamento Confirmado ✅",
        "body_template": "{{service_name}} em {{appointment_date}} às {{appointment_time}} com {{professional_name}}",
        "variables": {
            "service_name": "Nome do serviço",
            "appointment_date": "Data (DD/MM)",
            "appointment_time": "Horário (HH:MM)",
            "professional_name": "Nome do profissional"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "booking_reminder_push": {
        "name": "booking_reminder_push",
        "event_type": NotificationEventType.BOOKING_REMINDER.value,
        "channel": NotificationChannel.PUSH.value,
        "subject": "Lembrete de Agendamento ⏰",
        "body_template": "{{service_name}} {{reminder_period}} com {{professional_name}}",
        "variables": {
            "service_name": "Nome do serviço",
            "reminder_period": "Período (hoje, amanhã, em 1h)",
            "professional_name": "Nome do profissional"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "payment_received_push": {
        "name": "payment_received_push",
        "event_type": NotificationEventType.PAYMENT_RECEIVED.value,
        "channel": NotificationChannel.PUSH.value,
        "subject": "Pagamento Confirmado 💳",
        "body_template": "R$ {{payment_amount}} processado com sucesso",
        "variables": {
            "payment_amount": "Valor do pagamento"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "points_earned_push": {
        "name": "points_earned_push",
        "event_type": NotificationEventType.POINTS_EARNED.value,
        "channel": NotificationChannel.PUSH.value,
        "subject": "Pontos Ganhos! 🎁",
        "body_template": "+{{points_earned}} pontos! Total: {{current_balance}}",
        "variables": {
            "points_earned": "Pontos ganhos",
            "current_balance": "Saldo atual"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "slot_available_push": {
        "name": "slot_available_push",
        "event_type": NotificationEventType.SLOT_AVAILABLE.value,
        "channel": NotificationChannel.PUSH.value,
        "subject": "Vaga Disponível! 🎯",
        "body_template": "{{service_name}} em {{available_date}} às {{available_time}}",
        "variables": {
            "service_name": "Nome do serviço",
            "available_date": "Data disponível",
            "available_time": "Horário disponível"
        },
        "priority": NotificationPriority.URGENT.value,
        "locale": "pt_BR"
    }
}


# ==================== In-App Notification Templates ====================

IN_APP_TEMPLATES = {
    "booking_confirmed_in_app": {
        "name": "booking_confirmed_in_app",
        "event_type": NotificationEventType.BOOKING_CONFIRMED.value,
        "channel": NotificationChannel.IN_APP.value,
        "subject": "Agendamento Confirmado",
        "body_template": """Seu agendamento de {{service_name}} foi confirmado para {{appointment_date}} às {{appointment_time}} com {{professional_name}}.

Não esqueça de chegar 10 minutos antes do horário marcado.""",
        "variables": {
            "service_name": "Nome do serviço",
            "appointment_date": "Data do agendamento",
            "appointment_time": "Horário do agendamento",
            "professional_name": "Nome do profissional"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "points_earned_in_app": {
        "name": "points_earned_in_app",
        "event_type": NotificationEventType.POINTS_EARNED.value,
        "channel": NotificationChannel.IN_APP.value,
        "subject": "Pontos Ganhos!",
        "body_template": """Parabéns! Você ganhou {{points_earned}} pontos.

Saldo atual: {{current_balance}} pontos
Nível: {{current_tier}}

Veja as recompensas disponíveis na aba Fidelidade.""",
        "variables": {
            "points_earned": "Pontos ganhos",
            "current_balance": "Saldo atual",
            "current_tier": "Nível atual"
        },
        "priority": NotificationPriority.NORMAL.value,
        "locale": "pt_BR"
    },

    "tier_upgraded_in_app": {
        "name": "tier_upgraded_in_app",
        "event_type": NotificationEventType.TIER_UPGRADED.value,
        "channel": NotificationChannel.IN_APP.value,
        "subject": "Parabéns! Você subiu de nível!",
        "body_template": """🎉 Você alcançou o nível {{new_tier}}!

Novos benefícios desbloqueados:
{{#benefits}}
• {{benefit_name}}: {{benefit_description}}
{{/benefits}}

Continue acumulando pontos para desbloquear ainda mais benefícios!""",
        "variables": {
            "new_tier": "Novo nível",
            "benefits": "Lista de benefícios"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    }
}


# ==================== WhatsApp Templates ====================

WHATSAPP_TEMPLATES = {
    "booking_confirmed_whatsapp": {
        "name": "booking_confirmed_whatsapp",
        "event_type": NotificationEventType.BOOKING_CONFIRMED.value,
        "channel": NotificationChannel.WHATSAPP.value,
        "subject": None,
        "body_template": """✅ *{{salon_name}}*
*Agendamento Confirmado!*

📋 *Serviço:* {{service_name}}
📅 *Data:* {{appointment_date}}
🕐 *Horário:* {{appointment_time}}
👤 *Profissional:* {{professional_name}}
📍 *Local:* {{unit_name}}

💡 *Lembrete:* Chegue com 10 minutos de antecedência

🔗 *App:* {{app_url}}

_Estamos ansiosos para recebê-lo(a)!_""",
        "variables": {
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "appointment_date": "Data do agendamento",
            "appointment_time": "Horário do agendamento",
            "professional_name": "Nome do profissional",
            "unit_name": "Nome da unidade",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.HIGH.value,
        "locale": "pt_BR"
    },

    "slot_available_whatsapp": {
        "name": "slot_available_whatsapp",
        "event_type": NotificationEventType.SLOT_AVAILABLE.value,
        "channel": NotificationChannel.WHATSAPP.value,
        "subject": None,
        "body_template": """🎯 *{{salon_name}}*
*VAGA DISPONÍVEL!*

Uma vaga ficou disponível para o serviço que você estava esperando:

📋 *Serviço:* {{service_name}}
📅 *Data:* {{available_date}}
🕐 *Horário:* {{available_time}}
👤 *Profissional:* {{professional_name}}

⏱️ *URGENTE:* Você tem até {{expiry_time}} para confirmar

✅ *Confirmar agendamento:* {{app_url}}

_Não perca esta oportunidade!_""",
        "variables": {
            "salon_name": "Nome do salão",
            "service_name": "Nome do serviço",
            "available_date": "Data disponível",
            "available_time": "Horário disponível",
            "professional_name": "Nome do profissional",
            "expiry_time": "Tempo limite",
            "app_url": "URL do aplicativo"
        },
        "priority": NotificationPriority.URGENT.value,
        "locale": "pt_BR"
    }
}


# ==================== Template Collection ====================

def get_all_default_templates() -> List[Dict]:
    """
    Get all default notification templates.

    Returns:
        List of all default template configurations
    """
    all_templates = []

    # Combine all template dictionaries
    for template_dict in [EMAIL_TEMPLATES, SMS_TEMPLATES, PUSH_TEMPLATES, IN_APP_TEMPLATES, WHATSAPP_TEMPLATES]:
        all_templates.extend(template_dict.values())

    return all_templates


def get_templates_by_channel(channel: str) -> List[Dict]:
    """
    Get default templates for a specific channel.

    Args:
        channel: Notification channel (email, sms, push, in_app, whatsapp)

    Returns:
        List of templates for the specified channel
    """
    channel_templates = {
        "email": EMAIL_TEMPLATES,
        "sms": SMS_TEMPLATES,
        "push": PUSH_TEMPLATES,
        "in_app": IN_APP_TEMPLATES,
        "whatsapp": WHATSAPP_TEMPLATES
    }

    return list(channel_templates.get(channel, {}).values())


def get_templates_by_event_type(event_type: str) -> List[Dict]:
    """
    Get default templates for a specific event type.

    Args:
        event_type: Notification event type

    Returns:
        List of templates for the specified event type
    """
    all_templates = get_all_default_templates()
    return [t for t in all_templates if t["event_type"] == event_type]
