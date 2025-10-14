# <!--
# ID: GH-009
# Epic: Scheduling Core
# Phase: 1
# -->

# GH-009 Reservar serviço

## Descrição

Como Cliente quero reservar um horário confirmando os detalhes e pagamento.

## Acceptance Criteria

- Valida disponibilidade atômica no momento do checkout.
- Cria registro de reserva com status inicial (ex.: pending_payment ou confirmed se Pix instantâneo).
- Associa pagamento (pré-autorizado ou capturado).
- Envia confirmação (WhatsApp/e-mail) após sucesso.

## DoD

- Testes de condição de corrida (reserva simultânea) simulados.
- Transação de banco assegura integridade.

## Labels

feature, backend, scheduling, payments
