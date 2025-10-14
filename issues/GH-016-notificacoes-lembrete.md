<!--
ID: GH-016
Epic: Notifications
Phase: 2
-->

# GH-016 Notificações de lembrete

## Descrição

Como Cliente quero receber lembrete antes do horário.

## Acceptance Criteria

- Envio em janelas configuráveis (ex.: 24h, 2h).
- Mecanismo idempotente evita duplicados.
- Fallback canal e-mail quando WhatsApp falha.

## DoD

- Worker assíncrono implementado.
- Testes de idempotência.

## Labels

feature, backend, notifications
