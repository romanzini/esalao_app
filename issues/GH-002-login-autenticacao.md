# <!--
# ID: GH-002
# Epic: Auth & Security
# Phase: 1
# -->

# GH-002 Login e autenticação

## Descrição

Como Usuário quero realizar login seguro para acessar recursos conforme meu papel.

## Acceptance Criteria

- JWT emitido após credenciais válidas.
- Refresh token separado com expiração configurável.
- Rate limiting em tentativas falhas (ex.: 5/min por IP+usuário).
- Resposta genérica para falhas (não revela se usuário existe).

## DoD

- Testes unitários de fluxo sucesso e bloqueio por tentativas.
- Rotas documentadas.
- Logs de falha com anonimização de credenciais.

## Labels

feature, auth, security, backend
