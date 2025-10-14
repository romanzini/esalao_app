# <!--
# ID: GH-006
# Epic: Accounts & Entities
# Phase: 1
# -->

# GH-006 Configurar catálogo de serviços

## Descrição

Como Gestor quero criar serviços com duração e preço para clientes reservarem.

## Acceptance Criteria

- CRUD completo de serviços.
- Duração em minutos validada (>0).
- Impede exclusão com reservas futuras (oferece inativar).
- Preço por unidade ou variação por profissional.

## DoD

- Migrações de tabela de serviços.
- Testes de regras de exclusão.
- Documentação OpenAPI.

## Labels

feature, backend, catalog
