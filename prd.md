# PRD: eSalao Marketplace de Beleza

## 1. Product overview

### 1.1 Document title and version

* PRD: eSalao Marketplace de Beleza
* Version: 1.0.0 (2025-10-14)

### 1.2 Product summary

Este documento descreve um marketplace web responsivo para agendamento e gestão de serviços de beleza (cabelereiro, estética, manicure, etc.). A plataforma conecta clientes finais a múltiplos salões e profissionais independentes, oferecendo busca, comparação, reserva, pagamento, avaliações e fidelização em um ecossistema unificado.

O foco é uma solução completa (não apenas MVP) construída em arquitetura modular com backend em FastAPI (Python) e banco de dados PostgreSQL. O sistema suportará papéis multi-nível (Admin da plataforma, Franquia/gestor de unidades, Recepção, Profissional e Cliente) com controles de acesso refinados. Cobrirá integrações de pagamentos (Pix, cartão, parcelamento via gateways como Stripe, Pagar.me, Mercado Pago), notificações (WhatsApp Business API, e-mail, SMS opcional), emissão de nota fiscal eletrônica (NF-e) e relatórios operacionais e financeiros.

## 2. Goals

### 2.1 Business goals

* Criar marketplace confiável para reservas de serviços de beleza multi-salões.
* Aumentar taxa de ocupação dos profissionais e ticket médio dos salões.
* Reduzir no-shows via confirmações automatizadas e políticas claras de cancelamento.
* Monetizar através de comissão por transação e planos premium para salões.
* Estabelecer base de dados rica para insights (retenção, LTV, ocupação, desempenho de serviço).
* Expandir capacidade técnica para escalar além de 50 agendamentos/dia sem re-arquitetura.

### 2.2 User goals

* Cliente: encontrar rapidamente salões/profissionais disponíveis, reservar, pagar e avaliar.
* Profissional: visualizar agenda própria, gerir disponibilidade, acompanhar comissões.
* Recepção: administrar agenda global da unidade, reagendar, gerenciar fila de espera.
* Franquia: controlar múltiplas unidades (serviços, preços, métricas consolidadas).
* Admin da plataforma: governar cadastros, compliance, faturamento e parâmetros globais.

### 2.3 Non-goals

* Aplicativo mobile nativo (foco atual apenas web responsivo).
* Suporte multi-idioma ou múltiplos fusos horários neste estágio.
* Funcionalidade offline.
* Real-time video consultations / tele-beauty.
* Integração avançada de estoque físico além do básico para venda de produtos (fase posterior).

## 3. User personas

### 3.1 Key user types

* Cliente
* Profissional
* Recepção
* Gestor de franquia (Franquia)
* Admin da plataforma

### 3.2 Basic persona details

* **Cliente**: Usuário final que busca e agenda serviços de beleza, deseja conveniência e transparência de preços e avaliações.
* **Profissional**: Prestador de serviços (cabeleireiro, manicure, etc.) que gerencia slots e acompanha ganhos/comissões.
* **Recepção**: Funcionário do salão/unidade que administra a agenda completa, confirma presença e gerencia encaixes.
* **Gestor de franquia**: Responsável por múltiplas unidades, padronização de catálogo e desempenho operacional.
* **Admin da plataforma**: Opera nível global (compliance, configuração de taxas, auditoria, suporte).

### 3.3 Role-based access

* **Cliente**: Criar conta, editar perfil, buscar, filtrar, reservar, pagar, cancelar dentro das regras, avaliar, ver histórico.
* **Profissional**: Ver somente sua agenda, ajustar disponibilidade, marcar status (iniciado, concluído), visualizar comissões, receber notificações de novas reservas.
* **Recepção**: Ver agenda de todos os profissionais da unidade, criar/editar/cancelar agendamentos, gerenciar fila de espera e overbooking controlado, registrar presença/no-show.
* **Gestor de franquia**: Gerir múltiplas unidades, configurar catálogo e preços diferenciado por unidade, acessar relatórios consolidados, gerenciar usuários (profissionais, recepção) de suas unidades.
* **Admin**: Acesso total (inclui gestão de planos, taxas, auditoria de logs, bloqueios, suporte, parâmetros de integração, relatórios globais, moderação de avaliações).

## 4. Functional requirements

* **Onboarding & cadastro (Priority: Alta)**
  * Cadastro de clientes com validação de e-mail e opção de login social (futuro) - agora: e-mail + senha.
  * Fluxo de cadastro de salões/unidades (dados legais, endereço, meios de pagamento, políticas de cancelamento).
  * Cadastro de profissionais atrelados a unidade.
* **Catálogo de serviços (Priority: Alta)**
  * CRUD de serviços com duração, preço base, categorias, nível de profissional requerido.
  * Preços configuráveis por unidade e variação por profissional (faixa ou multiplicador).
* **Agenda e disponibilidades (Priority: Alta)**
  * Gestão de horários de funcionamento da unidade e exceções (feriados, bloqueios).
  * Disponibilidade individual do profissional (bloqueios pessoais, férias, folgas).
* **Motor de agendamento (Priority: Crítica)**
  * Busca slots disponíveis por serviço, profissional, localização, data/hora.
  * Regras de conflito e prevenção de overbooking (com opção de overbooking controlado para encaixes).
  * Suporte a múltiplos serviços encadeados (pacote) com consolidação de slots.
* **Pagamentos & cobrança (Priority: Crítica)**
  * Integração com gateways (Stripe, Pagar.me, Mercado Pago) para cartão e Pix.
  * Captura imediata ou pré-autorização dependendo da política do salão.
  * Cálculo de comissão da plataforma e repasse ao salão/profissional.
  * Reembolsos parciais/integrais conforme janela de cancelamento.
* **Notificações & comunicação (Priority: Alta)**
  * Envio de confirmações e lembretes por WhatsApp (via API), e-mail (SMTP/provider) e SMS (opcional futuro).
  * Status tracking de mensagens e fallback de canal.
* **Política de cancelamento e no-show (Priority: Alta)**
  * Regras configuráveis por unidade (ex.: cancelamento gratuito até X horas; taxa Y% depois).
  * Registro de no-show e aplicação automática de penalidade (ex.: bloqueio temporário após N no-shows).
* **Avaliações & reputação (Priority: Média)**
  * Avaliação 1-5 estrelas + comentário moderado.
  * Métricas agregadas por profissional e serviço.
* **Relatórios & analytics (Priority: Média)**
  * Ocupação por profissional, faturamento diário/mensal, ticket médio, taxa de cancelamento, no-show rate, LTV, retenção.
* **Programa de fidelidade (Priority: Baixa)**
  * Acúmulo de pontos por valor gasto, resgate em serviços futuros.
* **Gestão de produtos (Priority: Baixa)**
  * Cadastro básico de produtos vendidos (para upsell), associação a venda em atendimento.
* **Segurança & compliance (Priority: Crítica)**
  * Armazenamento seguro (hash de senha, criptografia de dados sensíveis em repouso se aplicável).
  * LGPD: consentimento de marketing, direito de exclusão/anonymization.
* **Auditoria & logging (Priority: Alta)**
  * Logs de ações sensíveis (cancelamentos, reembolsos, alterações de permissão) com trilha de auditoria.
* **Admin & billing da plataforma (Priority: Média)**
  * Definição de percentuais de comissão, planos de assinatura de salões, faturamento e repasses.

## 5. User experience

### 5.1 Entry points & first-time user flow

* Landing page com busca rápida por serviço/localidade/data.
* CTA de cadastro/login para confirmar reserva.
* Wizard de onboarding para salões (dados básicos, serviços, profissionais).
* Tour guiado inicial para novos clientes após primeira reserva (opcional).

### 5.2 Core experience

* **Busca**: Cliente filtra por cidade/bairro, serviço, data, faixa de horário e visualiza slots.
* **Seleção de serviço/profissional**: Mostra duração, preço, avaliações, próximos horários.
* **Checkout**: Resumo, política de cancelamento, seleção de método de pagamento, confirmação.
* **Confirmação**: Tela e envio imediato de notificação com ID da reserva e botão adicionar a calendário.
* **Gestão de agenda (recepção/profissional)**: Visualização diária/semana em grade, arrastar para reagendar (drag & drop conceptual), marcadores de status.
* **Relatórios**: Dashboards com KPIs e exportação CSV.

  * Experiência positiva via tempo de resposta baixo (<1s para buscas típicas) e clareza de estados (loading, sucesso, erro) e feedback pós-ação.

### 5.3 Advanced features & edge cases

* Encaixe (waitlist) automático: vaga liberada notifica lista.
* Pacotes multi-serviço sequenciais com tempo de transição.
* Overbooking controlado (limite configurável) para reduzir impacto de no-shows históricos.
* Reagendamento automático sugerindo próximo bloco disponível inteiro para pacotes.
* Detecção de conflito de recurso (sala/equipamento) futuro (extensível).
* Bloqueio automático de cliente após exceder no-shows configurados.

### 5.4 UI/UX highlights

* Design responsivo mobile-first.
* Paleta neutra com destaques de status (confirmado, pendente, atrasado, concluído).
* Acessibilidade básica (contraste, navegação teclado, labels semânticos).
* Feedback inline de validação de formulários.
* Skeleton loading em buscas e agenda.

## 6. Narrative

O cliente acessa a plataforma, busca um serviço próximo, compara opções por preço e avaliações e agenda em poucos cliques. Recebe confirmação e lembretes automatizados reduzindo esquecimentos. O salão e profissionais visualizam suas agendas em tempo real, com relatórios que orientam decisões de operação e marketing. A plataforma centraliza pagamentos e reputação, criando um ciclo de valor onde maior qualidade atrai mais reservas e gera mais dados para otimização.

## 7. Success metrics

### 7.1 User-centric metrics

* Taxa de conversão busca -> reserva.
* Tempo médio para concluir agendamento (<2 minutos alvo).
* Taxa de no-show (meta reduzir <10%).
* NPS / média de avaliações (>4.5).

### 7.2 Business metrics

* GMV mensal (Gross Merchandise Volume).
* Receita da plataforma (comissões + planos).
* Retenção de clientes (repeat bookings 30/60/90 dias).
* Crescimento de salões ativos e profissionais.

### 7.3 Technical metrics

* Latência média API P95 < 800ms em 50 agendamentos/dia (projetar escalabilidade para >1000/dia).
* Taxa de erros 5xx < 0.5%.
* Cobertura de testes backend > 70% linhas (meta inicial).
* Disponibilidade (uptime) > 99.5%.

## 8. Technical considerations

### 8.1 Integration points

* Gateways de pagamento: Stripe, Pagar.me, Mercado Pago (abstração de provider).
* Pix via provedor compatível (ex.: Pagar.me / Mercado Pago).
* WhatsApp Business API para notificações; fallback e-mail.
* Emissão de NF-e via provedor (ex.: NFE.io).
* Serviço de e-mail (SendGrid / Amazon SES) – decisão posterior.

### 8.2 Data storage & privacy

* PostgreSQL: entidades principais (Usuário, Salão, Unidade, Profissional, Serviço, AgendaSlot, Reserva, Pagamento, Avaliação, PolíticaCancelamento, FilaEspera, Relatorio agregados).
* Criptografia de campos sensíveis (ex.: documentos fiscais) em repouso (pgcrypto ou KMS futuro).
* Retenção e anonimização sob solicitação (LGPD: pseudonimizar dados pessoais em soft-delete).

### 8.3 Scalability & performance

* Indexação composta (unidade_id, data, profissional_id) para buscas de slots.
* Estratégia de pré-computação / materialized views para dashboards.
* Fila assíncrona (ex.: Celery ou RQ + Redis) para notificações e tarefas pesadas.
* Rate limiting por IP/usuário para endpoints críticos (login, busca).

### 8.4 Potential challenges

* Complexidade de regras de disponibilidade e pacotes multi-serviço.
* Conciliação de pagamentos multi-gateway e reconciliação de repasses.
* Escalonar notificações sem ultrapassar limites da API do WhatsApp.
* Garantir consistência em reagendamentos com recursos encadeados.
* Mitigar fraudes (chargebacks) e abusos de cancelamento.

## 9. Milestones & sequencing

### 9.1 Project estimate

* Tamanho: Grande (plataforma completa multi-tenant marketplace) – estimado 6-9 meses para release completo incremental.

### 9.2 Team size & composition

* Equipe (proposta): 1 Product Manager, 1 UX/UI, 2 Backend (FastAPI), 2 Frontend (React responsivo), 1 QA, 1 DevOps, 1 Data/Analytics (parcial), 1 Tech Lead.

### 9.3 Suggested phases

* **Fase 1**: Fundamentos (auth, modelos, catálogo, agenda básica) (6-8 semanas)
  * Entidades, CRUD, disponibilidade simples, reservas básicas, testes iniciais.
* **Fase 2**: Pagamentos & notificações (6 semanas)
  * Integrações gateways, fluxo checkout, notificações WhatsApp/e-mail.
* **Fase 3**: Cancelamentos, no-show, políticas e relatórios iniciais (5 semanas)
  * Regras, penalidades, dashboards básicos.
* **Fase 4**: Avaliações, fidelidade (mínimo), overbooking controlado, fila de espera (5 semanas)
  * Reputação, pontos inicial, mecânicas avançadas de agenda.
* **Fase 5**: Otimização, performance, segurança avançada, auditoria, NF-e (6 semanas)
  * Hardening, logging completo, conformidade, tuning.
* **Fase 6**: Expansões (produtos, multi-gateway robusto, materialized views, refinamentos UX) (contínuo)
  * Iterações baseadas em métricas.

## 10. User stories

### 10.1 Cadastro de cliente

* **ID**: GH-001
* **Description**: Como Cliente quero criar uma conta para gerenciar minhas reservas.
* **Acceptance criteria**:
  * Deve exigir e-mail único e senha com regras mínimas.
  * Envia e-mail de verificação.
  * Não permite login antes da verificação (ou exibe aviso com reenviar).

### 10.2 Login e autenticação

* **ID**: GH-002
* **Description**: Como Usuário quero realizar login seguro para acessar recursos conforme meu papel.
* **Acceptance criteria**:
  * Token JWT emitido após credenciais válidas.
  * Rate limit em tentativas falhas.
  * Refresh token com expiração configurável.

### 10.3 Recuperação de senha

* **ID**: GH-003
* **Description**: Como Usuário quero redefinir minha senha quando esquecida.
* **Acceptance criteria**:
  * Link temporário com expiração.
  * Políticas de senha aplicadas.

### 10.4 Cadastro de salão/unidade

* **ID**: GH-004
* **Description**: Como Gestor de franquia quero cadastrar unidades para disponibilizar serviços.
* **Acceptance criteria**:
  * Campos obrigatórios: razão social, CNPJ, endereço, contato.
  * Validação de CNPJ.

### 10.5 Cadastro de profissional

* **ID**: GH-005
* **Description**: Como Recepção ou Gestor quero cadastrar profissionais vinculados à unidade.
* **Acceptance criteria**:
  * Associação a unidade obrigatória.
  * Definição de comissão padrão.

### 10.6 Configurar catálogo de serviços

* **ID**: GH-006
* **Description**: Como Gestor quero criar serviços com duração e preço para clientes reservarem.
* **Acceptance criteria**:
  * CRUD completo.
  * Impede exclusão se serviço tem reservas futuras; permite inativar.

### 10.7 Ajustar disponibilidade profissional

* **ID**: GH-007
* **Description**: Como Profissional quero definir horários de trabalho e bloqueios.
* **Acceptance criteria**:
  * Pode criar intervalos recorrentes e exceções por data.
  * Bloqueios impedem geração de slots.

### 10.8 Buscar slots disponíveis

* **ID**: GH-008
* **Description**: Como Cliente quero buscar horários disponíveis por serviço e localização.
* **Acceptance criteria**:
  * Retorna lista ordenada por horário.
  * Inclui alternativa de outro profissional se selecionado indisponível.

### 10.9 Reservar serviço

* **ID**: GH-009
* **Description**: Como Cliente quero reservar um horário confirmando os detalhes e pagamento.
* **Acceptance criteria**:
  * Valida ainda disponível no momento do checkout.
  * Cria registro de pagamento (pré-autorizado ou capturado).
  * Envia confirmação.

### 10.10 Política de cancelamento

* **ID**: GH-010
* **Description**: Como Cliente quero cancelar dentro das regras para evitar taxas.
* **Acceptance criteria**:
  * Exibe política antes de confirmar reserva.
  * Calcula taxa conforme janela.
  * Atualiza status e dispara reembolso quando aplicável.

### 10.11 Marcar no-show

* **ID**: GH-011
* **Description**: Como Recepção quero marcar um cliente como no-show para aplicar penalidades.
* **Acceptance criteria**:
  * Registro de timestamp e operador.
  * Incrementa contador para bloqueio futuro se excedido.

### 10.12 Fila de espera

* **ID**: GH-012
* **Description**: Como Cliente quero entrar em fila de espera para ser notificado se houver vaga.
* **Acceptance criteria**:
  * Notificação enviada em liberação de slot.
  * Primeiro a confirmar garante a vaga.

### 10.13 Overbooking controlado

* **ID**: GH-013
* **Description**: Como Gestor quero permitir overbooking limitado para reduzir impacto de no-shows.
* **Acceptance criteria**:
  * Limite configurável (%) por faixa horária.
  * Agenda indica visualmente slots sobrecapacidade.

### 10.14 Pagamento Pix e cartão

* **ID**: GH-014
* **Description**: Como Cliente quero pagar via Pix ou cartão.
* **Acceptance criteria**:
  * QR code Pix ou formulário seguro cartão.
  * Atualização de status de pagamento assíncrona.

### 10.15 Reembolso parcial/integral

* **ID**: GH-015
* **Description**: Como Sistema quero processar reembolsos segundo política de cancelamento.
* **Acceptance criteria**:
  * Chama gateway adequado.
  * Registra log de auditoria.

### 10.16 Notificações de lembrete

* **ID**: GH-016
* **Description**: Como Cliente quero receber lembrete antes do horário.
* **Acceptance criteria**:
  * Envio configurado (ex.: 24h e 2h antes).
  * Evita envio duplicado (idempotência).

### 10.17 Avaliar serviço

* **ID**: GH-017
* **Description**: Como Cliente quero avaliar após conclusão.
* **Acceptance criteria**:
  * Somente após status concluído.
  * Pode editar dentro de janela (ex.: 24h).

### 10.18 Moderação de avaliações

* **ID**: GH-018
* **Description**: Como Admin quero moderar avaliações inadequadas.
* **Acceptance criteria**:
  * Lista com filtro por report.
  * Ação de ocultar mantendo histórico.

### 10.19 Relatórios operacionais

* **ID**: GH-019
* **Description**: Como Gestor quero ver ocupação e faturamento.
* **Acceptance criteria**:
  * KPIs com filtros (data, unidade, profissional).
  * Exportação CSV.

### 10.20 Relatórios de plataforma

* **ID**: GH-020
* **Description**: Como Admin quero ver métricas globais e comissões.
* **Acceptance criteria**:
  * GMV, comissão por período.
  * Top serviços.

### 10.21 Comissão profissional

* **ID**: GH-021
* **Description**: Como Profissional quero ver minhas comissões acumuladas.
* **Acceptance criteria**:
  * Lista por reserva / período.
  * Cálculo após conclusão e pagamento confirmado.

### 10.22 Fidelidade (pontos básicos)

* **ID**: GH-022
* **Description**: Como Cliente quero acumular pontos por valor gasto.
* **Acceptance criteria**:
  * Definição de taxa (pontos/real).
  * Saldo visível em perfil.

### 10.23 Resgate de pontos

* **ID**: GH-023
* **Description**: Como Cliente quero usar pontos para abater valor.
* **Acceptance criteria**:
  * Validação de saldo.
  * Geração de desconto aplicado ao pagamento.

### 10.24 Gestão de usuários e permissões

* **ID**: GH-024
* **Description**: Como Admin quero gerenciar papéis de usuários.
* **Acceptance criteria**:
  * Alterar papel com log de auditoria.
  * Revogação de acesso imediata.

### 10.25 Auditoria de eventos

* **ID**: GH-025
* **Description**: Como Admin quero consultar logs de ações críticas.
* **Acceptance criteria**:
  * Filtro por usuário, data, tipo de evento.
  * Exportação.

### 10.26 Rate limiting de login

* **ID**: GH-026
* **Description**: Como Sistema quero limitar tentativas de login para reduzir brute force.
* **Acceptance criteria**:
  * Bloqueio temporário após N falhas.
  * Retorno genérico (não revela se usuário existe).

### 10.27 Anonimização de dados (LGPD)

* **ID**: GH-027
* **Description**: Como Cliente quero solicitar exclusão dos meus dados pessoais.
* **Acceptance criteria**:
  * Marca registros e anonimiza PII mantendo integridade de relatórios agregados.

### 10.28 Reagendar reserva

* **ID**: GH-028
* **Description**: Como Cliente quero reagendar dentro da política sem refazer todo processo.
* **Acceptance criteria**:
  * Mantém pagamento se política permite.
  * Notifica profissional e recepção.

### 10.29 Pacote multi-serviço

* **ID**: GH-029
* **Description**: Como Cliente quero reservar pacote de serviços consecutivos.
* **Acceptance criteria**:
  * Agenda slots sequenciais sem conflitos.
  * Se um slot falha, aborta reserva inteira (transacionalidade lógica).

### 10.30 Notificação de fila de espera

* **ID**: GH-030
* **Description**: Como Cliente quero ser notificado da liberação de vaga da fila de espera.
* **Acceptance criteria**:
  * Notificação com link direto para confirmar.
  * Expira após tempo configurável.

### 10.31 Exportação de relatórios CSV

* **ID**: GH-031
* **Description**: Como Gestor quero exportar relatórios para análise externa.
* **Acceptance criteria**:
  * Gera arquivo com cabeçalhos padronizados.
  * Limita tamanho ou pagina.

### 10.32 Bloqueio por no-shows

* **ID**: GH-032
* **Description**: Como Sistema quero bloquear temporariamente clientes após exceder no-shows.
* **Acceptance criteria**:
  * Threshold configurável.
  * Mensagem clara no bloqueio.

### 10.33 Logs de pagamento

* **ID**: GH-033
* **Description**: Como Admin quero acessar histórico detalhado de transações e status.
* **Acceptance criteria**:
  * Armazena ID externo do gateway, valor, status, timestamps.
  * Permite reconciliação.

### 10.34 Busca por avaliações

* **ID**: GH-034
* **Description**: Como Cliente quero ver avaliações de serviços e profissionais.
* **Acceptance criteria**:
  * Paginação, média agregada, distribuição de notas.

### 10.35 Filtrar por preço e avaliação

* **ID**: GH-035
* **Description**: Como Cliente quero refinar busca por faixa de preço e nota mínima.
* **Acceptance criteria**:
  * Combinação de filtros sem duplicar resultados.

### 10.36 Visualizar agenda própria

* **ID**: GH-036
* **Description**: Como Profissional quero visualizar somente minha agenda.
* **Acceptance criteria**:
  * Não exibe dados de outros profissionais.
  * Atualização em tempo quase real (polling ou websockets futuro).

### 10.37 Agenda global da unidade

* **ID**: GH-037
* **Description**: Como Recepção quero ver todas as reservas da unidade.
* **Acceptance criteria**:
  * Visualização multi-coluna por profissional.
  * Filtros por serviço/status.

### 10.38 Configurar política de cancelamento

* **ID**: GH-038
* **Description**: Como Gestor quero definir janelas e taxas de cancelamento.
* **Acceptance criteria**:
  * Múltiplos tiers (ex.: >24h, 24-4h, <4h).
  * Validação de sobreposição.

### 10.39 Definir comissões

* **ID**: GH-039
* **Description**: Como Gestor quero definir comissões por profissional ou serviço.
* **Acceptance criteria**:
  * Multiplicador ou valor fixo.
  * Aplica-se no fechamento da reserva.

### 10.40 Painel de desempenho profissional

* **ID**: GH-040
* **Description**: Como Profissional quero ver KPIs pessoais.
* **Acceptance criteria**:
  * Reservas concluídas, avaliações médias, receita gerada.

### 10.41 Sessão e logout seguro

* **ID**: GH-041
* **Description**: Como Usuário quero terminar sessão de forma segura.
* **Acceptance criteria**:
  * Revogação de refresh tokens.
  * Logout invalida sessão ativa.

### 10.42 Pesquisa por localização

* **ID**: GH-042
* **Description**: Como Cliente quero filtrar salões por proximidade.
* **Acceptance criteria**:
  * Busca por cidade/bairro (geocoding).

### 10.43 Ajustar status de reserva

* **ID**: GH-043
* **Description**: Como Recepção quero marcar reservas como iniciado e concluído.
* **Acceptance criteria**:
  * Transições válidas apenas em sequência lógica.

### 10.44 Histórico de reservas cliente

* **ID**: GH-044
* **Description**: Como Cliente quero ver histórico de reservas passadas e futuras.
* **Acceptance criteria**:
  * Paginação, status, avaliação vinculada.

### 10.45 Monitoramento de erros

* **ID**: GH-045
* **Description**: Como Admin quero receber alertas de falhas críticas.
* **Acceptance criteria**:
  * Integração com serviço de observabilidade (Sentry / Prometheus).

### 10.46 Exportar dados pessoais (LGPD)

* **ID**: GH-046
* **Description**: Como Cliente quero exportar meus dados pessoais.
* **Acceptance criteria**:
  * Gera arquivo estruturado (JSON ou CSV) com PII.

### 10.47 Atualizar dados do salão

* **ID**: GH-047
* **Description**: Como Gestor quero editar dados da unidade.
* **Acceptance criteria**:
  * Auditoria de alterações sensíveis.

### 10.48 Aplicar desconto promocional

* **ID**: GH-048
* **Description**: Como Cliente quero usar um código promocional no checkout.
* **Acceptance criteria**:
  * Valida expiração e condições (serviço/unidade).

### 10.49 Cancelamento pela recepção

* **ID**: GH-049
* **Description**: Como Recepção quero cancelar reservas a pedido do cliente.
* **Acceptance criteria**:
  * Aplica mesma política de taxa.
  * Log de operador.

### 10.50 Visualizar fila de espera

* **ID**: GH-050
* **Description**: Como Recepção quero ver e priorizar clientes na fila de espera.
* **Acceptance criteria**:
  * Ordenação por horário de entrada.
  * Ação de promover para reserva.

Confirme se deseja que eu gere issues no repositório para cada user story (GH-001 a GH-050). Após sua aprovação posso prosseguir com essa etapa.
