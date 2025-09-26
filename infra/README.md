# Tactyo Infra

Scripts e orquestrações para desenvolvimento e deploy, incluindo Docker Compose e utilitários.

## Docker Compose (desenvolvimento)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Serviços provisionados:
- `db`: Postgres 15 (porta 5432) com volume persistente.
- `api`: FastAPI executando via `uvicorn` com reload automático.
- `web`: Vite dev server servindo a SPA.

As variáveis de ambiente padrão estão em `.env.example`. Ajuste `TACTYO_SESSION_SECRET` e `TACTYO_DATABASE_URL` conforme necessário.
