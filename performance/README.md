# Performance Testing

Este diretório contém scripts e resultados de testes de carga (load testing) para a plataforma eSalão.

## Ferramenta: Locust

**Locust** é uma ferramenta de load testing open-source baseada em Python.

### Por que Locust?
- Python-based: integra bem com nosso stack
- UI web para visualização em tempo real
- Scriptável para testes complexos
- Suporta distribuição de carga (master-worker)

## Instalação

```bash
pip install locust
```

## Uso Básico

### 1. Iniciar a API (target do teste)

```bash
# Com Docker Compose
docker-compose up -d

# Ou localmente
uvicorn backend.app.main:app --reload
```

### 2. Executar Locust

**UI Web (recomendado para primeira execução):**

```bash
cd /home/romanzini/repositorios/esalao_app
locust -f performance/locustfile.py --host=http://localhost:8000
```

Acesse: http://localhost:8089

Configuração sugerida:
- **Number of users**: 50 (peak load)
- **Spawn rate**: 10 users/s
- **Run time**: 2m (120s)

**Headless (para CI/CD):**

```bash
locust -f performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 10 \
  --run-time 2m \
  --headless \
  --html performance/results/report_$(date +%Y%m%d_%H%M%S).html
```

## Endpoints Testados

### Endpoints Críticos
1. **GET /v1/scheduling/slots** - Buscar slots disponíveis (peso: 3)
2. **POST /v1/bookings** - Criar reserva (peso: 1)
3. **GET /v1/bookings** - Listar reservas do usuário (peso: 1)
4. **GET /v1/professionals** - Listar profissionais (peso: 1)
5. **GET /v1/services** - Listar serviços (peso: 1)

### Cenários de Usuário

#### eSalaoUser (autenticado)
- Registra/loga na API
- Navega slots (3x mais frequente)
- Cria reservas
- Lista profissionais e serviços

#### ReadOnlyUser (não autenticado)
- Apenas leitura (GET requests)
- Simula browsing sem login
- Testa cache de endpoints públicos

## Métricas de Performance

### Requisitos (PER-001)
- **P95 < 800ms**: 95% das requisições devem responder em menos de 800ms
- **P99 < 1500ms**: 99% das requisições devem responder em menos de 1500ms
- **Throughput**: >100 req/s para endpoints de leitura

### Métricas Coletadas
- **P50, P95, P99**: Latências percentis
- **Throughput**: Requisições por segundo
- **Error Rate**: Taxa de erros (target: <1%)
- **Response times**: Min, Max, Average

## Estrutura de Resultados

```
performance/
├── locustfile.py           # Script de teste principal
├── README.md               # Este arquivo
└── results/                # Relatórios HTML (gitignore)
    ├── report_20250122_140530.html
    └── baseline_20250122.html
```

## Análise de Resultados

Após o teste, Locust gera:
1. **HTML Report**: Gráficos e tabelas com métricas
2. **Console Output**: Resumo em tempo real
3. **CSV Files**: Dados brutos para análise (opcional)

### Exemplo de Análise

```bash
# Verificar P95 do endpoint mais crítico
grep "scheduling/slots" performance/results/latest.html

# Comparar com baseline
diff performance/results/baseline.html performance/results/latest.html
```

## Troubleshooting

### Erro: Connection Refused
```bash
# Verifique se a API está rodando
curl http://localhost:8000/health
```

### Erro: Rate Limiting (429)
```bash
# Ajuste o rate limit em .env ou reduza spawn_rate
export RATE_LIMIT_PER_MINUTE=120
```

### High Error Rate
- Verifique logs da API: `docker-compose logs -f api`
- Reduza número de usuários ou spawn_rate
- Valide se fixtures de teste existem no banco

## Próximos Passos

1. **Baseline Estabelecido**: ✅ Executar primeira rodada de testes
2. **Análise de Bottlenecks**: Identificar endpoints lentos (P95 > 800ms)
3. **Otimização**: Implementar melhorias (cache, índices, N+1 queries)
4. **Regression Testing**: Executar testes antes de cada release

## Referências

- [Locust Documentation](https://docs.locust.io/)
- [Performance Best Practices](../.github/instructions/performance-optimization.instructions.md)
- [PER-001 Requirement](../plan/phase1/PER-001-performance-baseline.md)
