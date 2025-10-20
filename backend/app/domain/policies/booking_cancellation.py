"""
Booking Cancellation Service
Integra o sistema de políticas de cancelamento com o fluxo de booking
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from backend.app.db.repositories.booking import BookingRepository
from backend.app.db.repositories.cancellation_policy import CancellationPolicyRepository
from backend.app.domain.policies.cancellation import CancellationContext


class BookingCancellationService:
    """
    Serviço para gerenciar cancelamentos de booking com políticas de taxas.

    Responsabilidades:
    - Calcular taxa de cancelamento baseada na política aplicada
    - Aplicar cancelamento respeitando regras de negócio
    - Validar se cancelamento é permitido
    - Integrar com sistema de pagamentos para cobrança de taxas
    """

    def __init__(
        self,
        booking_repo: BookingRepository,
        policy_repo: CancellationPolicyRepository,
    ) -> None:
        """Inicializar serviço de cancelamento."""
        self.booking_repo = booking_repo
        self.policy_repo = policy_repo

    async def calculate_cancellation_fee(
        self,
        booking_id: int,
        cancellation_time: Optional[datetime] = None,
    ) -> dict:
        """
        Calcular taxa de cancelamento para um booking.

        Args:
            booking_id: ID do booking
            cancellation_time: Momento do cancelamento (padrão: agora)

        Returns:
            dict com informações da taxa:
            {
                'fee_amount': Decimal,
                'tier_name': str,
                'allows_refund': bool,
                'policy_name': str,
                'advance_hours': int
            }

        Raises:
            ValueError: Se booking não encontrado ou já cancelado
        """
        # Buscar booking
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking {booking_id} not found")

        if booking.status == "cancelled":
            raise ValueError(f"Booking {booking_id} already cancelled")

        # Usar política específica do booking ou política padrão
        policy = None
        if booking.cancellation_policy_id:
            policy = await self.policy_repo.get_by_id(booking.cancellation_policy_id)

        if not policy:
            # Buscar política padrão para o salão ou plataforma
            if hasattr(booking, 'professional') and hasattr(booking.professional, 'salon_id'):
                policy = await self.policy_repo.get_default_for_salon(booking.professional.salon_id)

            if not policy:
                policy = await self.policy_repo.get_platform_default()

        if not policy:
            raise ValueError("No cancellation policy found")

        # Calcular tempo de antecedência
        cancellation_time = cancellation_time or datetime.now(timezone.utc)
        advance_hours = (booking.scheduled_at - cancellation_time).total_seconds() / 3600

        # Criar contexto e calcular taxa
        context = CancellationContext(
            booking_id=booking_id,
            scheduled_time=booking.scheduled_at,
            cancellation_time=cancellation_time,
            service_price=Decimal(str(booking.service_price)),
            client_id=booking.client_id,
            professional_id=booking.professional_id,
        )

        evaluation = policy.evaluate_cancellation(context)

        return {
            'fee_amount': evaluation.fee_amount,
            'tier_name': evaluation.applicable_tier.name,
            'allows_refund': evaluation.applicable_tier.allows_refund,
            'policy_name': policy.name,
            'advance_hours': int(context.advance_notice_hours),
            'refund_amount': evaluation.refund_amount,
        }

    async def can_cancel_booking(
        self,
        booking_id: int,
        cancellation_time: Optional[datetime] = None,
    ) -> dict:
        """
        Verificar se um booking pode ser cancelado.

        Args:
            booking_id: ID do booking
            cancellation_time: Momento do cancelamento (padrão: agora)

        Returns:
            dict com resultado:
            {
                'can_cancel': bool,
                'reason': str,
                'fee_info': dict  # apenas se can_cancel=True
            }
        """
        try:
            # Buscar booking
            booking = await self.booking_repo.get_by_id(booking_id)
            if not booking:
                return {
                    'can_cancel': False,
                    'reason': 'Booking not found',
                }

            # Verificar status
            if booking.status == "cancelled":
                return {
                    'can_cancel': False,
                    'reason': 'Booking already cancelled',
                }

            if booking.status == "completed":
                return {
                    'can_cancel': False,
                    'reason': 'Cannot cancel completed booking',
                }

            # Verificar se não é muito próximo ao horário
            cancellation_time = cancellation_time or datetime.now(timezone.utc)
            advance_hours = (booking.scheduled_at - cancellation_time).total_seconds() / 3600

            if advance_hours < 0:
                return {
                    'can_cancel': False,
                    'reason': 'Cannot cancel past bookings',
                }

            # Calcular taxa
            fee_info = await self.calculate_cancellation_fee(booking_id, cancellation_time)

            return {
                'can_cancel': True,
                'reason': 'Cancellation allowed',
                'fee_info': fee_info,
            }

        except Exception as e:
            return {
                'can_cancel': False,
                'reason': f'Error checking cancellation: {str(e)}',
            }

    async def cancel_booking(
        self,
        booking_id: int,
        cancelled_by_id: int,
        reason: str,
        cancellation_time: Optional[datetime] = None,
    ) -> dict:
        """
        Cancelar um booking aplicando a taxa conforme política.

        Args:
            booking_id: ID do booking
            cancelled_by_id: ID do usuário que está cancelando
            reason: Motivo do cancelamento
            cancellation_time: Momento do cancelamento (padrão: agora)

        Returns:
            dict com resultado:
            {
                'success': bool,
                'message': str,
                'cancellation_fee': Decimal,
                'refund_amount': Decimal,
                'payment_required': bool  # se cliente precisa pagar taxa adicional
            }

        Raises:
            ValueError: Se booking não pode ser cancelado
        """
        # Verificar se pode cancelar
        can_cancel_result = await self.can_cancel_booking(booking_id, cancellation_time)
        if not can_cancel_result['can_cancel']:
            raise ValueError(can_cancel_result['reason'])

        fee_info = can_cancel_result['fee_info']
        cancellation_time = cancellation_time or datetime.now(timezone.utc)

        # Buscar booking novamente para atualizar
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        # Atualizar booking com informações de cancelamento
        update_data = {
            'status': 'cancelled',
            'cancelled_at': cancellation_time,
            'cancellation_reason': reason,
            'cancelled_by_id': cancelled_by_id,
            'cancellation_fee_amount': fee_info['fee_amount'],
        }

        # Aplicar política se não estava definida
        if not booking.cancellation_policy_id:
            policy = await self.policy_repo.get_platform_default()
            if policy:
                update_data['cancellation_policy_id'] = policy.id

        # Atualizar booking
        updated_booking = await self.booking_repo.update(booking_id, update_data)

        # Determinar se cliente precisa pagar taxa adicional
        # (baseado na diferença entre taxa e valor já pago)
        paid_amount = Decimal(str(booking.deposit_amount or 0))
        fee_amount = fee_info['fee_amount']
        payment_required = fee_amount > paid_amount

        return {
            'success': True,
            'message': f'Booking cancelled with {fee_info["tier_name"]} fee',
            'cancellation_fee': fee_amount,
            'refund_amount': fee_info['refund_amount'],
            'payment_required': payment_required,
            'policy_applied': fee_info['policy_name'],
            'booking': updated_booking,
        }

    async def assign_cancellation_policy(
        self,
        booking_id: int,
        policy_id: Optional[int] = None,
    ) -> dict:
        """
        Atribuir uma política de cancelamento específica ao booking.

        Args:
            booking_id: ID do booking
            policy_id: ID da política (None = usar padrão)

        Returns:
            dict com resultado da atribuição
        """
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("Booking not found")

        if policy_id:
            policy = await self.policy_repo.get_by_id(policy_id)
            if not policy:
                raise ValueError("Policy not found")
        else:
            # Usar política padrão
            policy = await self.policy_repo.get_platform_default()
            if not policy:
                raise ValueError("No default policy available")
            policy_id = policy.id

        # Atualizar booking
        await self.booking_repo.update(booking_id, {'cancellation_policy_id': policy_id})

        return {
            'success': True,
            'policy_assigned': policy.name,
            'policy_id': policy_id,
        }
