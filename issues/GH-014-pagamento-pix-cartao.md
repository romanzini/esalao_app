<!--
ID: GH-014
Epic: Payments & Finance
Phase: 2
-->

# GH-014 Pagamento Pix e cartão

## Descrição

Como Cliente quero pagar via Pix ou cartão.

## Acceptance Criteria

- Geração de QR Code Pix / payload.
- Formulário seguro para cartão (tokenização gateway).
- Webhook/async update de status.
- Estados: pending, authorized, captured, refunded, failed.

## DoD

- Testes de integração mock gateway.
- Logs de transação armazenam ID externo.

## Labels

feature, backend, payments
