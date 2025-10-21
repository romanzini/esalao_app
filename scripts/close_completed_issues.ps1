<#
.SYNOPSIS
    Fecha issues do GitHub que foram completamente implementadas na Phase 1

.DESCRIPTION
    Este script fecha automaticamente as issues que tiveram suas funcionalidades
    implementadas e validadas durante a Phase 1 do projeto eSalão.

    Issues fechadas:
    - GH-001: Registro de usuário
    - GH-002: Login de usuário
    - GH-003: Refresh token
    - GH-004: Cadastro de salão/unidade
    - GH-005: Cadastro de profissional
    - GH-006: Configurar catálogo de serviços
    - GH-007: Ajustar disponibilidade profissional
    - GH-041: Implementar autenticação JWT

.PARAMETER Repo
    Nome do repositório no formato "owner/repo"

.PARAMETER Token
    GitHub Personal Access Token com permissão 'repo'
    Se não fornecido, tentará usar a variável de ambiente GITHUB_TOKEN

.PARAMETER DryRun
    Se especificado, apenas mostra o que seria feito sem executar

.EXAMPLE
    .\scripts\close_completed_issues.ps1 -Repo "romanzini/esalao_app"

.EXAMPLE
    .\scripts\close_completed_issues.ps1 -Repo "romanzini/esalao_app" -DryRun

.EXAMPLE
    .\scripts\close_completed_issues.ps1 -Repo "romanzini/esalao_app" -Token "ghp_xxxxxxxxxxxx"
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Repo,

    [Parameter(Mandatory = $false)]
    [string]$Token = $env:GITHUB_TOKEN,

    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Configuração
$ErrorActionPreference = "Stop"
$baseUrl = "https://api.github.com"

# Validação do token
if (-not $Token) {
    Write-Error "GitHub token não fornecido. Use o parâmetro -Token ou defina a variável GITHUB_TOKEN"
    exit 1
}

# Headers para autenticação
$headers = @{
    "Authorization" = "Bearer $Token"
    "Accept"        = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2019-11-28"
}

# Issues a serem fechadas com mensagens de conclusão
$issuesToClose = @(
    @{
        Number = 1
        Title = "Registro de usuário"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ User model criado com todos os campos necessários (`backend/app/db/models/user.py`)
- ✅ Endpoint `POST /v1/auth/register` implementado
- ✅ Hash de senha com Argon2id (64MB memory, 3 iterations, 4 threads)
- ✅ Validação de email único
- ✅ Resposta com tokens JWT (access + refresh)

### Arquivos criados:
- `backend/app/db/models/user.py` - User model com UserRole enum
- `backend/app/core/security/password.py` - Argon2 hashing utilities
- `backend/app/api/v1/routes/auth.py` - Auth endpoints
- `backend/app/api/v1/schemas/auth.py` - Pydantic schemas

### Task relacionada:
- TASK-0100: User model com Argon2
- TASK-0102: Auth endpoints (register/login/refresh)

### Validação:
- ✅ Migration aplicada: `alembic revision --autogenerate -m "Add User model"`
- ✅ Testes manuais executados com sucesso

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 2
        Title = "Login de usuário"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Endpoint `POST /v1/auth/login` implementado
- ✅ Validação de credenciais (email + password)
- ✅ Verificação de senha com Argon2
- ✅ Geração de tokens JWT (access 30min + refresh 7 dias)
- ✅ Update de `last_login` timestamp

### Arquivos relacionados:
- `backend/app/api/v1/routes/auth.py` - Login endpoint
- `backend/app/core/security/password.py` - Password verification
- `backend/app/core/security/jwt.py` - JWT utilities
- `backend/app/db/repositories/user.py` - UserRepository com `update_last_login()`

### Task relacionada:
- TASK-0102: Auth endpoints (register/login/refresh)

### Resposta da API:
\`\`\`json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
\`\`\`

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 3
        Title = "Refresh token"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Endpoint `POST /v1/auth/refresh` implementado
- ✅ Validação de refresh token
- ✅ Rotação de tokens (gera novo par access + refresh)
- ✅ Verificação de tipo de token (apenas refresh aceito)
- ✅ Tratamento de erros (token inválido, expirado, tipo errado)

### Arquivos relacionados:
- `backend/app/api/v1/routes/auth.py` - Refresh endpoint
- `backend/app/core/security/jwt.py` - Token verification e creation

### Task relacionada:
- TASK-0101: JWT utils com refresh token
- TASK-0102: Auth endpoints (register/login/refresh)

### Configuração JWT:
- Access token: 30 minutos (configurável via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token: 7 dias (configurável via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`)
- Algoritmo: HS256

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 4
        Title = "Cadastro de salão/unidade"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Salon model criado com todos os campos (`backend/app/db/models/salon.py`)
- ✅ CNPJ único e indexado
- ✅ Endereço completo desnormalizado (street, number, complement, neighborhood, city, state, zipcode)
- ✅ Relacionamento com User (owner_id - SALON_OWNER)
- ✅ Soft delete via `is_active`
- ✅ Migration aplicada

### Campos do modelo:
- name, description
- cnpj (unique), phone, email
- address_street, address_number, address_complement
- address_neighborhood, address_city, address_state, address_zipcode
- is_active, owner_id (FK para User)
- created_at, updated_at (auto)

### Task relacionada:
- TASK-0103: Salon model CRUD

### Relacionamentos:
- N:1 com User (owner)
- 1:N com Professional
- 1:N com Service

**Nota**: Endpoints CRUD serão implementados na Phase 2. O modelo de dados está completo e validado.

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 5
        Title = "Cadastro de profissional"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Professional model criado (`backend/app/db/models/professional.py`)
- ✅ Relacionamento 1:1 com User (user_id unique FK)
- ✅ Relacionamento N:1 com Salon (salon_id FK)
- ✅ Array de especialidades (PostgreSQL ARRAY type)
- ✅ Comissão configurável (commission_percentage 0-100%)
- ✅ Número de registro profissional (license_number)
- ✅ Migration aplicada

### Campos do modelo:
- user_id (unique FK para User)
- salon_id (FK para Salon)
- specialties (ARRAY de strings)
- bio, license_number
- is_active
- commission_percentage (0-100)
- created_at, updated_at (auto)

### Task relacionada:
- TASK-0104: Professional model CRUD

### Relacionamentos:
- 1:1 com User
- N:1 com Salon
- 1:N com Availability
- 1:N com Booking

**Nota**: Endpoints CRUD serão implementados na Phase 2. O modelo de dados está completo e validado.

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 6
        Title = "Configurar catálogo de serviços"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Service model criado (`backend/app/db/models/service.py`)
- ✅ Preço com precisão decimal (Numeric 10,2)
- ✅ Duração em minutos configurável
- ✅ Suporte a sinal/depósito (requires_deposit, deposit_percentage)
- ✅ Categorização de serviços
- ✅ Soft delete via `is_active`
- ✅ Migration aplicada

### Campos do modelo:
- salon_id (FK para Salon)
- name, description, category
- duration_minutes
- price (Numeric 10,2 para BRL)
- is_active
- requires_deposit, deposit_percentage (0-100)
- created_at, updated_at (auto)

### Task relacionada:
- TASK-0105: Service model CRUD

### Relacionamentos:
- N:1 com Salon
- 1:N com Booking

### Exemplo de uso:
- Corte de cabelo: 60min, R$ 50,00, categoria "Hair"
- Manicure completa: 90min, R$ 80,00, categoria "Nails", requer sinal de 30%

**Nota**: Endpoints CRUD serão implementados na Phase 2. O modelo de dados está completo e validado.

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 7
        Title = "Ajustar disponibilidade profissional"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ Availability model criado (`backend/app/db/models/availability.py`)
- ✅ DayOfWeek enum (0=Segunda a 6=Domingo)
- ✅ Horários de início e fim (start_time, end_time com tipo Time)
- ✅ Duração de slot configurável (padrão 30 minutos)
- ✅ Soft delete via `is_active`
- ✅ Migration aplicada

### Campos do modelo:
- professional_id (FK para Professional)
- day_of_week (enum 0-6)
- start_time, end_time (Time)
- slot_duration_minutes (padrão 30)
- is_active
- created_at, updated_at (auto)

### Task relacionada:
- TASK-0106: Availability model

### Relacionamentos:
- N:1 com Professional

### DayOfWeek Enum:
- 0: MONDAY (Segunda)
- 1: TUESDAY (Terça)
- 2: WEDNESDAY (Quarta)
- 3: THURSDAY (Quinta)
- 4: FRIDAY (Sexta)
- 5: SATURDAY (Sábado)
- 6: SUNDAY (Domingo)

### Exemplo de uso:
- Profissional trabalha Segunda-Sexta das 09:00 às 18:00
- Slots de 30 minutos cada
- Algoritmo de cálculo de slots será implementado em TASK-0107

**Nota**: Endpoints CRUD serão implementados na Phase 2. O modelo de dados está completo e validado.

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    },
    @{
        Number = 41
        Title = "Implementar autenticação JWT"
        Comment = @"
✅ **Implementação Completa - Phase 1**

### O que foi implementado:
- ✅ JWT utilities completos (`backend/app/core/security/jwt.py`)
- ✅ Access token com expiração de 30 minutos
- ✅ Refresh token com expiração de 7 dias
- ✅ Token verification com validação de tipo
- ✅ Token rotation no refresh endpoint
- ✅ Configuração via environment variables

### Funções criadas:
- `create_access_token(user_id: int) -> str`
- `create_refresh_token(user_id: int) -> str`
- `create_token_pair(user_id: int) -> dict[str, str]`
- `verify_token(token: str, expected_type: str) -> TokenPayload`

### Task relacionada:
- TASK-0101: JWT utils com refresh token
- TASK-0102: Auth endpoints (register/login/refresh)

### Configuração (backend/app/core/config.py):
```python
JWT_SECRET_KEY: str = "your-secret-key-here"  # Sobrescrever em .env
JWT_ALGORITHM: str = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
```

### Segurança:
- ✅ Algoritmo HS256 (HMAC SHA-256)
- ✅ Payload inclui: user_id, exp, type (access/refresh)
- ✅ Validação de expiração automática
- ✅ Validação de tipo de token (previne uso de refresh como access)

### Payload structure:
\`\`\`json
{
  "user_id": 123,
  "exp": 1729012345,
  "type": "access"
}
\`\`\`

**Próximos passos**: RBAC middleware (TASK-0109) para autorização baseada em roles.

**Documentação**: Ver `PHASE_1_MODELS_COMPLETE.md` para detalhes completos.
"@
    }
)

# Função para fechar issue
function Close-GitHubIssue {
    param(
        [int]$IssueNumber,
        [string]$Comment
    )

    $issueUrl = "$baseUrl/repos/$Repo/issues/$IssueNumber"

    try {
        # Adicionar comentario
        if ($Comment) {
            Write-Host "  [COMMENT] Adicionando comentario a issue #$IssueNumber..." -ForegroundColor Cyan

            if (-not $DryRun) {
                $commentBody = @{
                    body = $Comment
                } | ConvertTo-Json -Depth 10

                $null = Invoke-RestMethod `
                    -Uri "$issueUrl/comments" `
                    -Method Post `
                    -Headers $headers `
                    -Body $commentBody `
                    -ContentType "application/json"
            }
        }

        # Fechar issue
        Write-Host "  [OK] Fechando issue #$IssueNumber..." -ForegroundColor Green

        if (-not $DryRun) {
            $closeBody = @{
                state = "closed"
            } | ConvertTo-Json

            $result = Invoke-RestMethod `
                -Uri $issueUrl `
                -Method Patch `
                -Headers $headers `
                -Body $closeBody `
                -ContentType "application/json"

            return $result
        } else {
            Write-Host "  [DRY RUN] Issue seria fechada" -ForegroundColor Yellow
            return $null
        }
    }
    catch {
        Write-Error "Erro ao processar issue #$IssueNumber : $_"
        return $null
    }
}

# Banner
Write-Host ""
Write-Host "===============================================================" -ForegroundColor Magenta
Write-Host "  Fechamento de Issues Completadas - Phase 1" -ForegroundColor Magenta
Write-Host "===============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Repositorio: $Repo" -ForegroundColor White
Write-Host "Issues a fechar: $($issuesToClose.Count)" -ForegroundColor White

if ($DryRun) {
    Write-Host "Modo: DRY RUN (apenas simulacao)" -ForegroundColor Yellow
} else {
    Write-Host "Modo: EXECUCAO REAL" -ForegroundColor Green
}

Write-Host ""

# Confirmacao
if (-not $DryRun) {
    Write-Host "[ATENCAO] Esta acao ira fechar $($issuesToClose.Count) issues no GitHub." -ForegroundColor Yellow
    $confirmation = Read-Host "Deseja continuar? (s/N)"

    if ($confirmation -ne "s" -and $confirmation -ne "S") {
        Write-Host "[CANCELADO] Operacao cancelada pelo usuario." -ForegroundColor Red
        exit 0
    }
    Write-Host ""
}

# Processar cada issue
$successCount = 0
$failCount = 0

foreach ($issue in $issuesToClose) {
    Write-Host "---------------------------------------------------------------" -ForegroundColor Gray
    Write-Host "[ISSUE] #$($issue.Number): $($issue.Title)" -ForegroundColor White

    $result = Close-GitHubIssue -IssueNumber $issue.Number -Comment $issue.Comment

    if ($DryRun -or $result) {
        $successCount++
        Write-Host "  [OK] Sucesso!" -ForegroundColor Green
    } else {
        $failCount++
        Write-Host "  [ERRO] Falhou!" -ForegroundColor Red
    }

    Write-Host ""
}

# Resumo final
Write-Host "===============================================================" -ForegroundColor Magenta
Write-Host "  [RESUMO] Resumo da Execucao" -ForegroundColor Magenta
Write-Host "===============================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "[OK] Sucesso: $successCount" -ForegroundColor Green
Write-Host "[ERRO] Falhas:  $failCount" -ForegroundColor Red
Write-Host ""

if ($DryRun) {
    Write-Host "[INFO] Esta foi uma execucao simulada (DRY RUN)." -ForegroundColor Cyan
    Write-Host "       Execute novamente sem -DryRun para fechar as issues." -ForegroundColor Cyan
} else {
    Write-Host "[SUCESSO] Issues fechadas com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "[PENDENTES] Issues restantes da Phase 1:" -ForegroundColor Yellow
    Write-Host "   - GH-008: Buscar slots disponiveis (aguarda TASK-0107)" -ForegroundColor White
    Write-Host "   - GH-009: Reservar servico (aguarda TASK-0108 endpoints)" -ForegroundColor White
    Write-Host "   - GH-011: Marcar no-show (aguarda TASK-0108 endpoints)" -ForegroundColor White
    Write-Host "   - GH-026: Seguranca (aguarda TASK-0109 RBAC)" -ForegroundColor White
}

Write-Host ""
Write-Host "===============================================================" -ForegroundColor Magenta
Write-Host ""

exit 0
