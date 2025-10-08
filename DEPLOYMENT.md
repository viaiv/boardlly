# Deployment Guide - EasyPanel

Este guia mostra como fazer deploy do Tactyo no EasyPanel.

## Estrutura

- **API**: FastAPI (Python 3.12) - Porta 8000
- **Web**: React + Vite + Nginx - Porta 80
- **Database**: PostgreSQL 16

## Deploy no EasyPanel

### 1. Criar o Projeto

No EasyPanel, crie um novo projeto chamado `tactyo`.

### 2. Adicionar PostgreSQL

1. Clique em **Add Service** > **Database** > **PostgreSQL**
2. Nomeie como `tactyo-db`
3. Anote as credenciais geradas

### 3. Deploy da API

1. Clique em **Add Service** > **App**
2. Configure:
   - **Nome**: `tactyo-api`
   - **Source**: GitHub repository
   - **Build Method**: Dockerfile
   - **Dockerfile Path**: `api/Dockerfile`
   - **Build Context**: `api/`
   - **Port**: `8000`

3. **Environment Variables**:
   ```env
   TACTYO_DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@tactyo-db:5432/tactyo
   TACTYO_SESSION_SECRET=gerar-secret-seguro-aqui
   TACTYO_ENCRYPTION_KEY=gerar-key-base64-32bytes-aqui
   TACTYO_DEBUG=false
   SYNC_INTERVAL_CRON=*/10 * * * *
   ```

4. **Domains**: Configure seu domínio (ex: `api.tactyo.com`)

### 4. Deploy do Web

1. Clique em **Add Service** > **App**
2. Configure:
   - **Nome**: `tactyo-web`
   - **Source**: GitHub repository
   - **Build Method**: Dockerfile
   - **Dockerfile Path**: `web/Dockerfile`
   - **Build Context**: `web/`
   - **Port**: `80`

3. **Build Arguments**:
   ```env
   VITE_API_BASE_URL=https://api.tactyo.com
   ```

4. **Domains**: Configure seu domínio (ex: `app.tactyo.com`)

### 5. Gerar Secrets

#### Session Secret
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Encryption Key (32 bytes base64)
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Configuração GitHub OAuth (Opcional)

Se você usar autenticação GitHub, adicione estas variáveis na API:

```env
GITHUB_CLIENT_ID=seu_client_id
GITHUB_CLIENT_SECRET=seu_client_secret
```

## Verificação de Deploy

### API Health Check
```bash
curl https://api.tactyo.com/
# Deve retornar: {"message": "Tactyo API"}
```

### Web Health Check
```bash
curl https://app.tactyo.com/
# Deve retornar o HTML da aplicação
```

## Troubleshooting

### Erro de conexão com banco de dados
- Verifique se a `TACTYO_DATABASE_URL` está correta
- Confirme que o serviço do PostgreSQL está rodando
- Use o hostname interno do EasyPanel (ex: `tactyo-db`)

### Build falha na API
- Verifique se o `requirements.txt` está correto
- Confirme que está usando Python 3.12
- Veja os logs de build no EasyPanel

### Build falha no Web
- Limpe o cache de node_modules
- Verifique se o `package.json` tem todas as dependências
- Confirme que as variáveis VITE_* estão definidas em tempo de build

### CORS errors
- Verifique se `VITE_API_BASE_URL` aponta para o domínio correto da API
- Confirme que a API tem CORS habilitado para o domínio do frontend

## Docker Compose Local

Para testar localmente antes do deploy:

```bash
# Subir todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f api
docker-compose logs -f web

# Parar serviços
docker-compose down

# Rebuild após mudanças
docker-compose up -d --build
```

Acesse:
- API: http://localhost:8000
- Web: http://localhost:3000
- Docs: http://localhost:8000/docs

## Backups

Configure backups automáticos do PostgreSQL no EasyPanel:
1. Acesse o serviço `tactyo-db`
2. Vá em **Backups**
3. Configure backup diário/semanal

## Monitoramento

O EasyPanel fornece:
- Logs em tempo real
- Métricas de CPU/RAM
- Health checks automáticos
- Alertas de downtime

## Custos Estimados

- **Hobby**: ~$5-10/mês (1 CPU, 1GB RAM)
- **Production**: ~$20-50/mês (2 CPUs, 4GB RAM, backups)
