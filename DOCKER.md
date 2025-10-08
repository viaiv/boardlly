# Docker Guide - Tactyo

Guia completo para usar Docker no desenvolvimento e produção do Tactyo.

## Estrutura de Arquivos

```
tactyo/
├── api/
│   ├── Dockerfile          # Container da API FastAPI
│   ├── requirements.txt
│   └── ...
├── web/
│   ├── Dockerfile          # Container do Web React
│   ├── package.json
│   └── ...
├── docker-compose.yml      # Orquestração local
├── .dockerignore          # Arquivos ignorados no build
└── scripts/
    └── generate_secrets.py # Gerar secrets seguros
```

## Desenvolvimento Local

### Iniciar todos os serviços

```bash
# Primeira vez ou após mudanças no Dockerfile
docker-compose up -d --build

# Inicializações subsequentes
docker-compose up -d
```

Serviços disponíveis:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Web**: http://localhost:3000
- **PostgreSQL**: localhost:5432

### Comandos úteis

```bash
# Ver logs de todos os serviços
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f api
docker-compose logs -f web

# Parar serviços
docker-compose down

# Parar e remover volumes (⚠️ apaga banco de dados!)
docker-compose down -v

# Rebuild apenas um serviço
docker-compose up -d --build api

# Executar comando dentro do container da API
docker-compose exec api python -m pytest

# Acessar shell do container
docker-compose exec api bash
docker-compose exec web sh

# Ver status dos containers
docker-compose ps
```

## Build Manual (sem docker-compose)

### API

```bash
# Build
cd api
docker build -t tactyo-api:latest .

# Run
docker run -d \
  --name tactyo-api \
  -p 8000:8000 \
  -e TACTYO_DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/tactyo" \
  -e TACTYO_SESSION_SECRET="your-secret" \
  -e TACTYO_ENCRYPTION_KEY="your-key" \
  tactyo-api:latest

# Logs
docker logs -f tactyo-api
```

### Web

```bash
# Build
cd web
docker build -t tactyo-web:latest .

# Run
docker run -d \
  --name tactyo-web \
  -p 3000:80 \
  tactyo-web:latest

# Logs
docker logs -f tactyo-web
```

## Otimizações

### Multi-stage Build

Ambos os Dockerfiles usam multi-stage builds para:
- ✅ Reduzir tamanho da imagem final
- ✅ Separar dependências de build e runtime
- ✅ Melhorar segurança (menos pacotes em prod)

### Cache de Layers

Para builds mais rápidos:

**API:**
1. Copia `requirements.txt` primeiro
2. Instala dependências (cached se não mudou)
3. Depois copia código fonte

**Web:**
1. Copia `package*.json` primeiro
2. Instala dependências (cached se não mudou)
3. Depois copia código fonte

### Tamanhos das Imagens

- **API**: ~200-300 MB (Python slim)
- **Web**: ~50-80 MB (nginx alpine)

## Health Checks

Ambos os containers têm health checks configurados:

```bash
# Ver status de saúde
docker inspect tactyo-api | grep -A 10 Health
docker inspect tactyo-web | grep -A 10 Health

# Com docker-compose
docker-compose ps
```

## Variáveis de Ambiente

### API (obrigatórias)

```env
TACTYO_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/tactyo
TACTYO_SESSION_SECRET=<usar scripts/generate_secrets.py>
TACTYO_ENCRYPTION_KEY=<usar scripts/generate_secrets.py>
```

### API (opcionais)

```env
TACTYO_DEBUG=false
SYNC_INTERVAL_CRON=*/10 * * * *
DEFAULT_OWNER=org-name
DEFAULT_PROJECT_NUMBER=1
```

### Web (build-time)

```env
VITE_API_BASE_URL=http://localhost:8000
```

**⚠️ IMPORTANTE**: Variáveis VITE_* devem ser definidas em **build time**, não runtime!

## Troubleshooting

### Container da API não inicia

```bash
# Ver logs detalhados
docker-compose logs api

# Problemas comuns:
# 1. Database não está pronto
#    - Aguarde o health check do PostgreSQL
#    - docker-compose ps para ver status

# 2. Variáveis de ambiente faltando
#    - Verifique .env ou docker-compose.yml

# 3. Porta já em uso
#    - Mude a porta no docker-compose.yml
```

### Container do Web não inicia

```bash
# Ver logs detalhados
docker-compose logs web

# Problemas comuns:
# 1. Build falhou
#    - Verifique se node_modules está no .dockerignore
#    - docker-compose up --build web

# 2. Nginx não inicia
#    - Verifique sintaxe da config do nginx no Dockerfile
```

### Mudanças não aparecem

```bash
# Rebuild forçado sem cache
docker-compose build --no-cache api
docker-compose up -d api

# Ou rebuild tudo
docker-compose down
docker-compose up -d --build
```

### Limpar tudo e recomeçar

```bash
# ⚠️ Isso apaga volumes e dados do banco!
docker-compose down -v
docker system prune -a
docker-compose up -d --build
```

## CI/CD

### GitHub Actions exemplo

```yaml
name: Build Docker Images

on:
  push:
    branches: [main]

jobs:
  build-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build API
        run: docker build -t tactyo-api:${{ github.sha }} ./api

  build-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Web
        run: docker build -t tactyo-web:${{ github.sha }} ./web
```

## Produção

Para produção (EasyPanel, Railway, Render, etc), veja [DEPLOYMENT.md](./DEPLOYMENT.md).

### Boas práticas para produção

- ✅ Use secrets manager (não .env)
- ✅ Configure backups automáticos do PostgreSQL
- ✅ Use HTTPS (Let's Encrypt)
- ✅ Configure health checks e restart policies
- ✅ Monitor logs e métricas
- ✅ Use multi-AZ/regions para alta disponibilidade
- ✅ Configure rate limiting e CORS adequadamente

## Referências

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker Compose](https://docs.docker.com/compose/)
