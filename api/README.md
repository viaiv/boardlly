# Tactyo API

Backend FastAPI responsável pela autenticação, sincronização com o GitHub Projects v2 e regras de negócio do Tactyo.

## Requisitos
- Python 3.11+
- Postgres 15+

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Executar em desenvolvimento

```bash
python run.py
```

O script `run.py` verifica dependências, executa as migrações do Alembic (`upgrade head`) e sobe o servidor uvicorn em `http://0.0.0.0:8000` com auto-reload habilitado.

Para executar manualmente:

```bash
alembic upgrade head
uvicorn main:app --reload --app-dir api
```

Variáveis principais (ver `.env.example` neste diretório):
- `TACTYO_DATABASE_URL`
- `TACTYO_SESSION_SECRET` (mínimo 16 caracteres)
- `TACTYO_ENCRYPTION_KEY` (chave base64 de 32 bytes para criptografar PAT)

## Estrutura
```
app/
  api/
  core/
  db/
  models/
  schemas/
alembic/
```

A migração inicial cria `account`, `app_user` e `account_github_credentials`, alinhadas ao MVP.
