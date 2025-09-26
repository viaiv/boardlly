# Tactyo

Tactyo é um MVP para acompanhar projetos do GitHub Projects v2, oferecendo dashboard, solicitações e backlog integrados. Este repositório reúne o frontend (React/Vite) e o backend (FastAPI) com infraestrutura compartilhada.

## Estrutura

```
/
├─ web/    # SPA em Vite + React + Tailwind + shadcn/ui
├─ api/    # Backend FastAPI + Postgres + Alembic
├─ infra/  # Docker Compose e scripts auxiliares
├─ docs/   # Documentação incremental (comandos, configuração)
├─ MVP.md  # Documento de referência do escopo
└─ AGENTS.md
```

## Pré-requisitos
- Node.js 20+
- npm 10+
- Python 3.11+
- Docker (opcional, para o ambiente orquestrado)

## Comandos iniciais

```bash
npm install                 # instala dependências do workspace
npm run install:web         # instala dependências do frontend
pip install -r api/requirements-dev.txt  # instala dependências da API
alembic upgrade head        # aplica migração inicial
```

> Configure `api/.env` com `TACTYO_ENCRYPTION_KEY` (32 bytes em base64) e demais variáveis antes de iniciar o backend.

## Desenvolvimento

```bash
npm run dev:web   # frontend em http://localhost:5173
npm run dev:api   # backend em http://localhost:8000
```

### Ambiente via Docker Compose

```bash
docker compose -f infra/docker-compose.yml up --build
```

O Compose provisiona Postgres, API FastAPI (com reload) e Vite em modo dev. Ajuste variáveis conforme `api/.env.example` para o backend e `web/.env.example` para o frontend.

## Próximos passos
- Implementar autenticação/RBAC e fluxos do backend.
- Conectar integrações com GitHub Projects.
- Evoluir telas do frontend com dados reais e componentes shadcn.
