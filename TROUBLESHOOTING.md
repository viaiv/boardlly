# Troubleshooting - Tactyo

Problemas comuns e soluções para o Tactyo.

## Erro: "error parsing value for field cors_origins"

### Sintomas
```
pydantic_settings.sources.SettingsError: error parsing value for field "cors_origins" from source "EnvSettingsSource"
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### Causa
A variável de ambiente `TACTYO_CORS_ORIGINS` está definida mas **vazia** (string vazia: `""`).

O Pydantic Settings tenta fazer parse automático de JSON para campos do tipo `List[...]`, e falha quando encontra string vazia.

### Solução

**Opção 1: Não definir a variável (recomendado)**
```bash
# ❌ ERRADO - não faça isso
export TACTYO_CORS_ORIGINS=""

# ✅ CORRETO - não defina a variável
# (o app usará o padrão: localhost:5173, 127.0.0.1:5173)
```

**Opção 2: Definir com valor válido**
```bash
# ✅ CORRETO - lista separada por vírgulas
export TACTYO_CORS_ORIGINS="http://localhost:3000,https://app.example.com"
```

**No EasyPanel:**
- Se não precisa customizar CORS origins: **não adicione** a variável `TACTYO_CORS_ORIGINS`
- Se precisa customizar: adicione com valor válido (ex: `http://app.com,http://app2.com`)

**No Docker Compose:**
```yaml
environment:
  # ❌ ERRADO
  TACTYO_CORS_ORIGINS: ""

  # ✅ CORRETO - não defina a variável
  # ou

  # ✅ CORRETO - defina com valor
  TACTYO_CORS_ORIGINS: "http://localhost:3000,https://app.com"
```

## Erro: "TACTYO_ENCRYPTION_KEY é obrigatório"

### Sintomas
```
ValueError: TACTYO_ENCRYPTION_KEY é obrigatório
```

### Causa
A variável de ambiente `TACTYO_ENCRYPTION_KEY` não está definida ou está vazia.

### Solução

**Para desenvolvimento local:**
```bash
# Gerar chave segura
python scripts/generate_secrets.py

# Copiar a chave e adicionar no .env
echo "TACTYO_ENCRYPTION_KEY=sua-chave-aqui" >> api/.env
```

**Para produção (EasyPanel, Railway, etc):**
1. Gere secrets seguros:
   ```bash
   python scripts/generate_secrets.py
   ```

2. Adicione as variáveis nas configurações do serviço:
   - `TACTYO_SESSION_SECRET`: secret para sessões
   - `TACTYO_ENCRYPTION_KEY`: chave para encriptação (32 bytes base64)

**⚠️ NUNCA use a chave de desenvolvimento do Dockerfile em produção!**

## Erro: "TACTYO_ENCRYPTION_KEY inválida: não é base64 válido"

### Sintomas
```
ValueError: TACTYO_ENCRYPTION_KEY inválida: não é base64 válido
```

### Causa
A chave não está em formato base64 válido.

### Solução
Use o script para gerar uma chave válida:
```bash
python scripts/generate_secrets.py
```

Ou gere manualmente:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## Erro: "TACTYO_ENCRYPTION_KEY deve decodificar para 32 bytes"

### Sintomas
```
ValueError: TACTYO_ENCRYPTION_KEY deve decodificar para 32 bytes
```

### Causa
A chave está em base64, mas quando decodificada não resulta em exatamente 32 bytes.

### Solução
Use o script oficial para gerar:
```bash
python scripts/generate_secrets.py
```

## Erro de conexão com banco de dados

### Sintomas
```
asyncpg.exceptions.InvalidCatalogNameError: database "tactyo" does not exist
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server
```

### Soluções

**1. Verificar se PostgreSQL está rodando**
```bash
# Docker Compose
docker-compose ps db

# Standalone
sudo systemctl status postgresql
```

**2. Criar banco de dados**
```bash
# Docker Compose
docker-compose exec db createdb -U postgres tactyo

# Standalone
createdb tactyo
```

**3. Verificar URL de conexão**
Formato correto: `postgresql+asyncpg://user:password@host:port/database`

Exemplo:
```bash
# Local
TACTYO_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tactyo

# Docker (de dentro do container)
TACTYO_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tactyo

# Externo (EasyPanel, etc)
TACTYO_DATABASE_URL=postgresql+asyncpg://user:pass@db-host.example.com:5432/tactyo
```

## CORS errors no frontend

### Sintomas
```
Access to fetch at 'http://api.example.com/api/...' from origin 'http://app.example.com'
has been blocked by CORS policy
```

### Soluções

**1. Configurar CORS_ORIGINS na API**
```bash
# Adicionar domínio do frontend
TACTYO_CORS_ORIGINS="http://localhost:3000,https://app.example.com"
```

**2. Verificar VITE_API_BASE_URL no frontend**
```bash
# Deve apontar para URL completa da API
VITE_API_BASE_URL=https://api.example.com
```

**3. Verificar se CORS está habilitado**
```bash
# No .env da API
TACTYO_ENABLE_CORS=true
```

## Container não inicia no EasyPanel/Railway

### Verificações

**1. Logs do container**
- Acesse os logs do serviço na plataforma
- Procure por erros de variáveis de ambiente
- Verifique se todas as variáveis obrigatórias estão definidas

**2. Health checks**
```bash
# Teste manualmente se a API responde
curl https://api.example.com/

# Deve retornar: {"message": "Tactyo API"}
```

**3. Verificar conectividade com banco**
```bash
# Do container da API, tente conectar ao banco
docker-compose exec api python -c "from app.db.session import SessionLocal; db = SessionLocal(); print('Connected!')"
```

## Build do Docker falha

### Sintomas comuns

**"ERROR: failed to solve: process ..."**
- Limpe cache: `docker system prune -a`
- Rebuild: `docker-compose build --no-cache`

**"npm ERR!" ou "pip install failed"**
- Verifique conexão de internet
- Verifique se package.json/requirements.txt está correto
- Tente localmente primeiro: `npm install` ou `pip install -r requirements.txt`

**"COPY failed: file not found"**
- Verifique se o arquivo existe no diretório correto
- Verifique .dockerignore - arquivo pode estar sendo ignorado

## Migrations não aplicadas

### Sintomas
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "users" does not exist
```

### Soluções

**1. Aplicar migrations manualmente**
```bash
# Docker Compose
docker-compose exec api alembic upgrade head

# Standalone
cd api && source venv/bin/activate
alembic upgrade head
```

**2. Verificar histórico de migrations**
```bash
alembic history
alembic current
```

**3. Resolver múltiplas heads**
```bash
python scripts/fix_multiple_heads.py
```

## Dúvidas ou problemas não listados?

1. Verifique os logs detalhados
2. Consulte a documentação:
   - [DEPLOYMENT.md](./DEPLOYMENT.md) - Deploy em produção
   - [DOCKER.md](./DOCKER.md) - Uso do Docker
3. Abra uma issue no GitHub com:
   - Descrição do problema
   - Logs relevantes
   - Configuração (sem secrets!)
