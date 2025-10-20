# CRITICAL FIX: Endpoints Públicos de Leitura

**Data**: 2025-10-17  
**Prioridade**: CRITICAL 🔴  
**Impacto**: 44% dos load test requests (352/793) bloqueados

---

## Problema

### Performance Baseline mostra 403 Forbidden

Durante o teste de carga (PERFORMANCE 2), **44% dos requests** (352/793) retornaram **403 Forbidden**:

- **135 requests**: GET `/v1/services` [unauthenticated]
- **133 requests**: GET `/v1/professionals` [unauthenticated]
- **41 requests**: GET `/v1/services` [authenticated]
- **43 requests**: GET `/v1/professionals` [authenticated]

### Código Atual

Ambos endpoints **requerem autenticação**:

```python
# backend/app/api/v1/routes/professionals.py (linha 147)
async def list_professionals(
    current_user: Annotated[User, Depends(get_current_user)],  # ← REQUER AUTH
    db: Annotated[AsyncSession, Depends(get_db)],
    salon_id: Annotated[int | None, Query(...)] = None,
    ...
) -> ProfessionalListResponse:
```

```python
# backend/app/api/v1/routes/services.py
async def list_services(
    current_user: Annotated[User, Depends(get_current_user)],  # ← REQUER AUTH
    db: Annotated[AsyncSession, Depends(get_db)],
    ...
) -> ServiceListResponse:
```

### PRD Requirements

**Seção 5.1 - Entry points & first-time user flow**:
> "Landing page com busca rápida por serviço/localidade/data.  
> **CTA de cadastro/login para confirmar reserva**."

**Seção 5.2 - Core experience**:
> "**Busca**: Cliente filtra por cidade/bairro, serviço, data, faixa de horário e visualiza slots."

**Interpretação**: O cliente deve poder **navegar e buscar** (listar professionals, services, slots) **ANTES** de fazer login. Login é obrigatório apenas para **confirmar reserva** (criar booking).

---

## Solução

### Endpoints que DEVEM ser públicos (GET sem auth)

1. **GET /v1/professionals** - Listar profissionais
2. **GET /v1/professionals/{id}** - Obter profissional específico
3. **GET /v1/services** - Listar serviços
4. **GET /v1/services/{id}** - Obter serviço específico
5. **GET /v1/scheduling/slots** - Buscar slots disponíveis

### Endpoints que DEVEM requerer autenticação

- **POST /v1/bookings** - Criar reserva (requer auth)
- **PATCH /v1/bookings/{id}** - Atualizar/cancelar reserva (requer auth)
- **DELETE /v1/bookings/{id}** - Deletar reserva (requer auth)
- **POST /v1/professionals** - Criar profissional (requer auth + RBAC)
- **PUT /v1/professionals/{id}** - Atualizar profissional (requer auth + RBAC)
- **POST /v1/services** - Criar serviço (requer auth + RBAC)
- **PUT /v1/services/{id}** - Atualizar serviço (requer auth + RBAC)

---

## Implementação

### 1. Tornar `current_user` opcional em GET endpoints

#### professionals.py

```python
# ANTES (linha 147)
async def list_professionals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    ...
) -> ProfessionalListResponse:

# DEPOIS
async def list_professionals(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    ...
) -> ProfessionalListResponse:
    # Lógica permanece a mesma - current_user pode ser None
```

#### services.py

```python
# ANTES
async def list_services(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    ...
) -> ServiceListResponse:

# DEPOIS
async def list_services(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    ...
) -> ServiceListResponse:
```

#### scheduling.py

```python
# ANTES
async def get_available_slots(
    professional_id: int,
    date: date,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    slot_interval_minutes: int = 30,
) -> SlotResponse:

# DEPOIS (já é público, sem mudanças necessárias)
async def get_available_slots(
    professional_id: int,
    date: date,
    service_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_current_user_optional)] = None,
    slot_interval_minutes: int = 30,
) -> SlotResponse:
```

### 2. Criar `get_current_user_optional` em rbac.py

```python
# backend/app/core/security/rbac.py

async def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Get current user if token is provided, otherwise return None.
    
    Use this for endpoints that should be accessible both authenticated
    and unauthenticated, but may behave differently based on auth status.
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None


# Criar optional OAuth2 scheme
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,  # ← Não gera erro se token ausente
)
```

---

## Validação

### 1. Testes manuais

```bash
# Sem autenticação - deve funcionar ✅
curl -s "http://localhost:8000/v1/professionals" | jq .
curl -s "http://localhost:8000/v1/services" | jq .
curl -s "http://localhost:8000/v1/scheduling/slots?professional_id=1&date=2025-10-20&service_id=1" | jq .

# Com autenticação - deve funcionar ✅
TOKEN="eyJ..."
curl -s -H "Authorization: Bearer $TOKEN" "http://localhost:8000/v1/professionals" | jq .
```

### 2. Re-executar load test

```bash
cd performance
python -m locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 10 \
  --run-time 2m \
  --headless \
  --html results/report_after_fix_$(date +%Y%m%d_%H%M%S).html
```

**Expected outcome**:
- **403 Forbidden**: 0 (antes: 352)
- **Error rate**: < 5% (apenas 422/404 se houver outros problemas)
- **Throughput**: > 100 req/s ✅

### 3. Atualizar testes de integração

```python
# tests/integration/test_professionals.py

def test_list_professionals_public(client: TestClient):
    """Test that listing professionals works without authentication."""
    response = client.get("/v1/professionals")
    assert response.status_code == 200
    assert "professionals" in response.json()


def test_list_professionals_authenticated(client: TestClient, auth_headers: dict):
    """Test that listing professionals works with authentication."""
    response = client.get("/v1/professionals", headers=auth_headers)
    assert response.status_code == 200
    assert "professionals" in response.json()
```

---

## Estimativa

- **Implementação**: 20 minutos
  - Criar `get_current_user_optional`: 5min
  - Atualizar `professionals.py`: 5min
  - Atualizar `services.py`: 5min
  - Atualizar `scheduling.py` (se necessário): 5min

- **Testes**: 10 minutos
  - Testes manuais com curl: 5min
  - Criar testes de integração: 5min

- **Re-executar load test**: 2 minutos

**Total**: ~30 minutos

---

## Impacto Esperado

### Antes
- **Error rate**: 100% (793/793)
- **403 Forbidden**: 44% (352/793)

### Depois
- **Error rate**: < 5% (apenas 422 validation errors e 404 se faltarem dados)
- **403 Forbidden**: 0%
- **Throughput**: Projetado 100-150 req/s ✅

---

## Próximos Passos

1. ✅ Documentar análise (este arquivo)
2. ⏳ Implementar `get_current_user_optional`
3. ⏳ Atualizar endpoints GET de professionals e services
4. ⏳ Validar com testes manuais
5. ⏳ Re-executar load test
6. ⏳ Atualizar PERFORMANCE_BASELINE.md com novos resultados
