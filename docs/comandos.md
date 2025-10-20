### baixando o docker compose
docker compose down

### buildando o projeto
docker compose build --no-cache

### subindo o projeto
docker compose up -d

### verificando os container
docker compose ps

### verificando os logs da API
docker compose logs api --tail=20

### testando a api
curl -s http://localhost:8000/health | python3 -m json.tool

### executar as migrações do Alembic
docker compose exec api alembic upgrade head

### verificar se há alguma migração criada e o status do banco
docker compose exec api alembic current

# Gerar migração automática com os modelos existentes
docker compose exec api alembic revision --autogenerate -m "Add core entities: User, Salon, Professional, Service, Availability, Booking"

# Aplicar as migrações
docker compose exec api alembic upgrade head

# verificar o status atual:
docker compose exec api alembic current

# verificar se as tabelas foram criadas no banco de dados
docker compose exec db psql -U esalao_user -d esalao_db -c "\dt"

# verificar a estrutura da tabela users para confirmar
docker compose exec db psql -U esalao_user -d esalao_db -c "\d users"

# testar a API fazendo um registro de usuário
curl -s -X POST "http://localhost:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@esalao.com",
    "password": "senha12345",
    "full_name": "Usuário Teste",
    "phone": "11999999999"
  }' | python3 -m json.tool

# testando o login
curl -s -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@esalao.com",
    "password": "senha12345"
  }' | python3 -m json.tool

# verificar se o usuário foi realmente criado no banco
docker compose exec db psql -U esalao_user -d esalao_db -c "SELECT id, email, full_name, role, is_active, is_verified FROM users;"

# verificar os logs do worker Celery para garantir que está funcionando
docker compose logs worker --tail=15

# 1. Testar a API via Swagger UI
# Abra no navegador:
http://localhost:8000/docs

# Ou use o ReDoc:
http://localhost:8000/redoc

# 2. Criar dados de exemplo
# Registrar profissional
curl -X POST "http://localhost:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "barbeiro@esalao.com",
    "password": "senha12345",
    "full_name": "João Barbeiro",
    "phone": "11988888888"
  }'

# 4. Monitoramento
# Ver logs em tempo real
docker compose logs -f api

# Verificar métricas
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health

# Comandos Úteis para o Desenvolvimento

# Ver status dos containers
docker compose ps

# Logs de todos os serviços
docker compose logs -f

# Acessar o banco diretamente
docker compose exec db psql -U esalao_user -d esalao_db

# Criar nova migração
docker compose exec api alembic revision --autogenerate -m "Descrição"

# Aplicar migrações
docker compose exec api alembic upgrade head

# Reverter migração
docker compose exec api alembic downgrade -1

# Histórico de migrações
docker compose exec api alembic history

# Reiniciar apenas a API
docker compose restart api

# Reconstruir containers
docker compose build
docker compose up -d

# Como Testar o Sistema
# 1. Verificar status
docker compose ps

# 2. Registrar usuário
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"senha123","full_name":"Test User"}'

# 3. Login
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"senha123"}'

# 4. Acessar perfil (com token)
curl http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer <SEU_ACCESS_TOKEN>"

# 5. Documentação interativa
# Abra: http://localhost:8000/docs

