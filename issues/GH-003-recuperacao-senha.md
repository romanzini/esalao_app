# <!--
# ID: GH-003
# Epic: Auth & Security
# Phase: 1
# -->

# GH-003 Recuperação de senha

## Descrição

Como Usuário quero redefinir minha senha quando esquecida.

## Acceptance Criteria

- Gera token único de reset com expiração (ex.: 30 min).
- Link de reset invalida tokens anteriores.
- Políticas de senha aplicadas na redefinição.
- Registro de auditoria do reset (sem guardar a senha antiga).

## DoD

- Testes de expiração e uso único do token.
- Template de e-mail configurado.
- Documentação OpenAPI atualizada.

## Labels

feature, auth, backend
