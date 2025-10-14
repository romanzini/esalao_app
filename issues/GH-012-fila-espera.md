# <!--
# ID: GH-012
# Epic: Advanced Scheduling
# Phase: 4
# -->

# GH-012 Fila de espera

## Descrição

Como Cliente quero entrar em fila de espera para ser notificado se houver vaga.

## Acceptance Criteria

- Inclusão ordenada por data/hora de solicitação.
- Liberação de slot envia notificação aos inscritos.
- Primeiro a confirmar ocupa o slot e remove demais.

## DoD

- Testes de concorrência (duas confirmações).
- Documentação de fluxo.

## Labels

feature, backend, scheduling
