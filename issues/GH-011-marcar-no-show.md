# <!--
# ID: GH-011
# Epic: Policies & Compliance
# Phase: 3
# -->

# GH-011 Marcar no-show

## Descrição

Como Recepção quero marcar um cliente como no-show para aplicar penalidades.

## Acceptance Criteria

- Registro de timestamp e usuário executor.
- Incrementa contador de no-shows do cliente.
- Dispara avaliação de bloqueio se threshold excedido.

## DoD

- Testes de incremento e bloqueio.
- Log de auditoria validado.

## Labels

feature, backend, scheduling
