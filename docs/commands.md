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

## Observabilidade do roadmap
- `GET /api/projects/current/iterations/dashboard` — retorna estatísticas por sprint (itens, status, estimativas, opções disponíveis).
- `GET /api/projects/current/epics/dashboard` — retorna estatísticas por épico com contagens por status.
- `GET /api/projects/current/epics/options` — lista as opções de épico disponíveis no Project.
- `POST /api/projects/current/epics/options` — cria uma nova opção de épico no Project (owners/admins).
- `PATCH /api/projects/current/epics/options/{option_id}` — renomeia ou altera a cor de um épico existente.
- `DELETE /api/projects/current/epics/options/{option_id}` — remove uma opção de épico.

> Documente novos comandos aqui sempre que scripts adicionais forem criados.
