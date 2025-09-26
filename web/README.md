# Tactyo Web

Aplicação SPA criada com Vite + React + Tailwind + shadcn/ui. Estrutura inicial pronta para consumir a API FastAPI descrita no MVP.

## Scripts

```bash
npm run dev     # inicia servidor de desenvolvimento em http://localhost:5173
npm run build   # gera bundle de produção
npm run lint    # roda ESLint com regras padrão do projeto
npm run test    # executa testes (Vitest)
```

## Estrutura de pastas

```
src/
  components/      # componentes reutilizáveis (ui, layout, etc.)
  lib/             # utilitários compartilhados (api, sessão, helpers)
  routes/          # páginas protegidas e públicas da aplicação
```

Variáveis de ambiente (`.env` ou `.env.local`):

```
VITE_API_BASE_URL=http://localhost:8000
```

## Próximos passos
- Implementar consumo real da API (`/api/me`, `/api/projects/...`).
- Adicionar componentes shadcn conforme telas forem evoluindo.
- Criar testes de UI com Vitest/Testing Library.
