# Comandos do Projeto

## Setup inicial
- `npm install` — instala dependências do workspace (root).
- `npm run install:web` — instala dependências do frontend (`web/`).
- `pip install -r api/requirements-dev.txt` — instala dependências do backend.
- `alembic upgrade head` — aplica migrações iniciais do banco.

## Desenvolvimento local
- `npm run dev:web` — inicia o frontend em http://localhost:5173.
- `npm run dev:api` — inicia a API FastAPI em http://localhost:8000 (requer variáveis `.env`).
- `python api/run.py` — verifica dependências, roda as migrações e inicia o backend (ideal com venv ativo e variáveis de `api/.env.example`).
- `docker compose -f infra/docker-compose.yml up` — sobe web, API e Postgres via containers.
- `curl -X POST /api/github/sync/{project_id}` — sincroniza manualmente um Project v2 depois de configurar token/projeto.

## Qualidade
- `npm run lint` — executa ESLint no frontend.
- `npm run test` — executa testes do frontend (Vitest).
- `pytest` (dentro de `api/`) — executa testes do backend.
- `ruff check api/` — lint do backend (após instalar `ruff`).

> Documente novos comandos aqui sempre que scripts adicionais forem criados.
