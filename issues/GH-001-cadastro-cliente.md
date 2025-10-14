# <!--
# ID: GH-001
# Epic: Auth & Security
# Phase: 1
# -->

# GH-001 Cadastro de cliente

## Descrição

Como Cliente quero criar uma conta para gerenciar minhas reservas.

## Acceptance Criteria

- Exige e-mail único e senha com regras mínimas.
- Envia e-mail de verificação após cadastro.
- Bloqueia login antes da verificação (ou exibe aviso com opção de reenviar verificação).
- Registra data/hora de criação e verificação.

## Definição de Pronto (DoD)

- Testes de validação de senha e e-mail.
- Endpoint documentado (OpenAPI).
- Auditoria de criação armazenada.

## Labels

feature, auth, backend
