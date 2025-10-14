# <!--
# ID: GH-008
# Epic: Scheduling Core
# Phase: 1
# -->

# GH-008 Buscar slots disponíveis

## Descrição

Como Cliente quero buscar horários disponíveis por serviço e localização.

## Acceptance Criteria

- Filtros: serviço, data, unidade/localização.
- Retorno ordenado por horário ascendente.
- Sugestão de outro profissional se escolhido indisponível.
- Resposta em <800ms (P95) para dataset alvo inicial.

## DoD

- Índices aplicados (unidade_id, data, profissional_id).
- Testes de performance básicos.

## Labels

feature, backend, scheduling, performance
