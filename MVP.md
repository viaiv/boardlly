# Objetivo

Gerar um **MVP** de um app web autenticado que exibe um **dashboard** de progresso de um **GitHub Projects (v2)**, permite que a equipe crie **Solicitações** (change requests) e, após aprovação, converta em **Backlog** (e opcionalmente cria **Issue** e adiciona ao **Project**).

> Nome oficial do projeto: **Tactyo**
> Domínio de produção: **[https://tactyo.com](https://tactyo.com)**
> Stack sugerida: **React (Vite) + React Router + Tailwind + shadcn/ui** no frontend, **FastAPI** no backend, **Postgres** no banco. **Autenticação local (email/senha)** no backend; integração com GitHub via **token (PAT) cadastrado pelo dono da conta**. Autenticação de usuário via **GitHub OAuth**; integração com GitHub via **GitHub App** (installation token + webhooks).

---

## Escopo (MVP)

1. **Autenticação** via GitHub OAuth (login) e RBAC básico (viewer, editor, pm, admin).
2. **Conectar um Project v2** (por owner + number) e listar itens (Issue/PR/Draft) com fields: Status, Iteration, Estimate, Assignees.
3. **Dashboard** com KPIs simples: Itens por Status, Itens em Progresso, Fechados na semana, Velocidade média (estimativa simplificada), Burnup/Burndown simples.
4. **Solicitações**: CRUD de change requests (criar/listar/detalhar/atualizar status).
5. **Aprovar solicitação → Backlog**: ao aprovar, cria um **BacklogItem** interno e (configurável) cria **Issue** e **adiciona ao Project**.
6. **Webhooks** do GitHub para sincronizar mudanças do Project/Issues.
7. **Sincronização** manual e periódica (endpoint + cron/job simples) do Project v2.

---

## Páginas (SPA React)

* **/** (Overview): KPIs + gráficos (itens por status, burndown/burnup).
* **/roadmap**: Timeline/Gantt agrupado por Iteration ou por campos de data.
* **/roadmap**: lista filtrável de itens do Project (status, assignee, iteration, search) com visão em quadro e timeline.
* **/requests**: lista de solicitações; botão “Nova Solicitação”.
* **/requests/:id**: detalhe da solicitação, comentários, botão **Aprovar**/**Rejeitar**.
* **/backlog**: lista de backlog interno (prioridade, estimate, status); ação para criar Issue/adicionar ao Project se ainda não existir.
* **/settings**: conectar GitHub App (mostrar installation), configurar Projeto (owner + number), mapear fields (Status/Iteration/Estimate), toggles (auto-criar Issue, auto-adicionar ao Project).

> Rotas com **React Router**; proteção de rotas via **guard** que verifica sessão (cookie httpOnly) com `/api/me`.

### Componentes de UI

* Cards de KPI, tabela avançada (filtros, paginação), modal “Nova Solicitação”, gráficos (Recharts), Gantt (lib leve; se indisponível, lista por Iteration no MVP).

---

## Backend (FastAPI)

### Endpoints

```
GET  /api/me                                 -> dados do usuário autenticado + role
POST /api/auth/register                      -> cadastro (somente admin/owner)
POST /api/auth/login                         -> login local (email/senha)
POST /api/auth/logout                        -> logout (invalida sessão)
POST /api/invite                             -> envia convite por e-mail (opcional)

GET  /api/projects/{project_id}/overview     -> KPIs e métricas agregadas
GET  /api/projects/{project_id}/items        -> itens do Project (paginado + filtros)

POST /api/requests                           -> cria change_request
GET  /api/requests                           -> lista solicitações (filtros: status, prioridade)
GET  /api/requests/{id}                      -> detalhe
PATCH /api/requests/{id}                     -> atualizar (status, campos)
POST /api/requests/{id}/approve              -> aprova e cria backlog_item; opcional: cria Issue + ProjectItem

POST /api/backlog                            -> cria backlog manual
GET  /api/backlog                            -> lista backlog
PATCH /api/backlog/{id}                      -> atualiza (status, estimate, priority)

POST /api/github/sync/{project_id}           -> força sync on-demand (polling GraphQL)
POST /api/settings/github-token              -> cadastra/atualiza token (PAT) do GitHub (somente owner)
```

### Regras de Negócio (resumo)

* **viewer**: read-only em dashboard/itens/backlog.
* **editor**: cria **Solicitações** e comenta.
* **pm**: triagem (aprovar/rejeitar), prioriza, converte em backlog, cria Issue/ProjectItem.
* **admin**: gerencia conexão GitHub e configurações.

---

## Integração GitHub

### Modelo de integração (sem OAuth)

* **Sem login GitHub para usuários.** O acesso ao GitHub é centralizado por **um token (PAT)** cadastrado pelo **dono da conta** do Tactyo.
* O backend usa esse token para consultar o **GraphQL v4** do GitHub (Projects v2) e, se habilitado, criar Issues.
* **Escopos do PAT** (mínimo para leitura de Projects v2):

  * Recomendado: **Fine-grained PAT** com acesso *read* aos repositórios relevantes e **Organization/project read** quando o Project pertence à organização.
  * Alternativa: **Classic PAT** com `repo` (read) e `read:org` (se necessário para Projects de org). Evite escopos de escrita se não for criar Issues.

> **MVP**: sincronização por **polling** (cron + botão de sync). **Webhooks** podem ser adicionados depois via GitHub App ou Webhook de repo configurado manualmente.

### Boas práticas

* Armazenar o PAT **criptografado** (AES-GCM com `ENCRYPTION_KEY`).
* Rotacionar token e aplicar **rate limiting** nas chamadas à API do GitHub.
* Mapear IDs dos fields (Status/Iteration/Estimate) ao salvar as configurações do projeto.
* Projects (read)
* Issues (read/write) — apenas se opção de criar Issue estiver ativa
* Repository metadata (read)
* Pull requests (read)
* Webhooks (deliveries)

### GraphQL (exemplos)

**Buscar Project e fields**

```graphql
query ($owner:String!, $number:Int!) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
      title
      fields(first: 50) {
        nodes {
          ... on ProjectV2FieldCommon { id name dataType }
          ... on ProjectV2IterationField { id name }
          ... on ProjectV2SingleSelectField { id name options { id name } }
          ... on ProjectV2NumberField { id name }
        }
      }
    }
  }
}
```

**Listar itens**

```graphql
query ($projectId:ID!, $first:Int!, $after:String) {
  node(id: $projectId) {
    ... on ProjectV2 {
      items(first:$first, after:$after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          content {
            __typename
            ... on Issue { id number title url assignees(first:10){nodes{login}} }
            ... on PullRequest { id number title url assignees(first:10){nodes{login}} }
          }
          fieldValues(first:50) {
            nodes {
              ... on ProjectV2ItemFieldTextValue { field { ... on ProjectV2FieldCommon { name } } text }
              ... on ProjectV2ItemFieldSingleSelectValue { field { ... on ProjectV2FieldCommon { name } } name }
              ... on ProjectV2ItemFieldIterationValue { field { ... on ProjectV2FieldCommon { name } } title }
              ... on ProjectV2ItemFieldNumberValue { field { ... on ProjectV2FieldCommon { name } } number }
            }
          }
        }
      }
    }
  }
}
```

**Adicionar Issue ao Project**

```graphql
mutation($projectId:ID!, $contentId:ID!) {
  addProjectV2ItemById(input:{ projectId:$projectId, contentId:$contentId }) {
    item { id }
  }
}
```

**Atualizar field (Status)**

```graphql
mutation($projectId:ID!, $itemId:ID!, $fieldId:ID!, $optionId:String!) {
  updateProjectV2ItemFieldValue(input:{
    projectId:$projectId,
    itemId:$itemId,
    fieldId:$fieldId,
    value:{ singleSelectOptionId:$optionId }
  }) { projectV2Item { id } }
}
```

### Webhooks (mínimo)

* `project_v2_item` (criado/atualizado/removido)
* `issues` (opened/edited/closed)
* `pull_request` (opened/closed/merged)
* `issue_comment` (comentários referenciando solicitações)

**Pseudocódigo handler**

```python
@router.post("/api/github/webhooks")
def handle_event(payload: dict, x_hub_signature_256: str = Header(...)):
    verify_signature(payload, x_hub_signature_256)
    event = request.headers.get("X-GitHub-Event")
    if event == "project_v2_item":
        upsert_project_item_from_payload(payload)
    elif event == "issues":
        upsert_issue(payload)
    elif event == "pull_request":
        upsert_pr(payload)
    elif event == "issue_comment":
        link_comment_if_matches_change_request(payload)
    return {"ok": True}
```

---

## Banco de Dados (Postgres)

```sql
-- multi-tenant simples: uma "account" (cliente) possui usuários e configs
create table account (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_user_id uuid, -- referenciado em app_user após criar usuário
  created_at timestamptz default now()
);

create table app_user (
  id uuid primary key default gen_random_uuid(),
  account_id uuid references account(id) on delete cascade,
  email text unique not null,
  password_hash text not null,
  name text,
  role text check (role in ('viewer','editor','pm','admin','owner')) default 'viewer',
  created_at timestamptz default now()
);

-- credenciais GitHub por account (apenas o dono consegue alterar)
create table account_github_credentials (
  account_id uuid primary key references account(id) on delete cascade,
  pat_ciphertext bytea not null, -- PAT criptografado (AES-GCM)
  pat_nonce bytea not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table github_project (
  id bigserial primary key,
  account_id uuid references account(id) on delete cascade,
  project_node_id text unique not null,
  project_number int,
  owner_login text,
  name text,
  created_at timestamptz default now()
);

create table project_item (
  id bigserial primary key,
  account_id uuid references account(id) on delete cascade,
  project_id bigint references github_project(id) on delete cascade,
  item_node_id text unique not null,
  content_type text,
  content_node_id text,
  title text,
  status text,
  assignees text[],
  iteration text,
  estimate numeric,
  url text,
  updated_at timestamptz,
  last_synced_at timestamptz default now()
);

create table change_request (
  id uuid primary key default gen_random_uuid(),
  account_id uuid references account(id) on delete cascade,
  created_by uuid references app_user(id),
  title text not null,
  description text,
  impact text,
  priority text check (priority in ('low','medium','high','urgent')) default 'medium',
  status text check (status in ('draft','under_review','approved','rejected','converted')) default 'under_review',
  attachments jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table backlog_item (
  id uuid primary key default gen_random_uuid(),
  account_id uuid references account(id) on delete cascade,
  source_change_request uuid references change_request(id),
  title text not null,
  description text,
  priority text check (priority in ('low','medium','high','urgent')) default 'medium',
  estimate numeric,
  github_issue_node_id text,
  github_project_item_node_id text,
  status text check (status in ('backlog','todo','in_progress','done','archived')) default 'backlog',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

**Índices sugeridos**

```sql
create index on project_item(project_id);
create index on project_item(account_id);
create index on project_item(status);
create index on project_item(updated_at);
create index on backlog_item(account_id);
create index on backlog_item(status);
create index on change_request(account_id);
create index on change_request(status);
```

---

## Lógica de Sincronização

1. **Configurações**: owner cadastra **PAT** no `/settings` → backend valida escopos com uma query simples (ex.: `viewerCanAdminister` do Project ou listagem de fields).
2. **Descoberta**: salvar `project_node_id` e mapear IDs dos fields (Status, Iteration, Estimate, etc.).
3. **Polling**: job agendado (cron: `SYNC_INTERVAL_CRON`) e endpoint de **sync on-demand** paginam itens via GraphQL.
4. **Upsert**: gravar/atualizar em `project_item` e derivar métricas.
5. **Opcional**: permitir cadastro de **Webhook de repositório** manual (com secret) para acelerar sync; ou futura adoção de **GitHub App** para webhooks.

---

## Métricas e KPIs (MVP)

* **Itens por Status** (contagem).
* **Fechados na Semana Atual** (issue/PR closed date).
* **Velocidade**: soma de `estimate` feitos/iteração (cálculo simples).
* **Burndown/Burnup**: série temporal por dia usando snapshots/sync.

---

## Segurança

* **Autenticação local** (email/senha) com **hash Argon2id** e sessão via cookie **httpOnly** (SameSite=Lax).
* **PAT criptografado** em repouso (AES-GCM com `ENCRYPTION_KEY`). Nunca expor PAT ao frontend.
* **Rate limiting** nos endpoints de sync e leitura.
* **RBAC** por `account_id` (tenant) e `role` (viewer/editor/pm/admin/owner).

---

## Variáveis de Ambiente

```env
# FRONTEND (Vite)
VITE_APP_NAME=Tactyo
VITE_API_BASE_URL=http://localhost:8000

# BACKEND
API_PORT=8000
SESSION_SECRET= # assinatura de cookies de sessão (httpOnly)
ENCRYPTION_KEY= # 32 bytes base64 (p/ criptografar PAT)
DATABASE_URL=postgresql://postgres:postgres@db:5432/tactyo

# EMAIL (opcional, para convites e reset de senha)
SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASS=
SMTP_FROM="Tactyo <no-reply@tactyo.com>"

# SYNC
SYNC_INTERVAL_CRON=*/10 * * * *
DEFAULT_OWNER=
DEFAULT_PROJECT_NUMBER=
```

---

## Docker Compose (alvo do Codex)

* Gerar `docker-compose.yml` com serviços:

  * `web` (Vite dev server em dev: porta 5173; em prod, `npm run build` e servir estático via `nginx` ou pelo próprio FastAPI usando `StaticFiles`)
  * `api` (FastAPI, porta 8000)
  * `db` (Postgres 15, porta 5432 + volume + healthcheck)
  * (opcional) `worker` (RQ/Celery) e `scheduler` (cron)

**Diretórios esperados**

```
/ (repo raiz)
  /web        # Vite + React
  /api        # FastAPI
  /infra      # docker-compose, Makefile, scripts
```

**Produção**

* Build do front: `npm run build` → servir `/web/dist`:

  * Opção A: **FastAPI** monta `StaticFiles` em `/` e redireciona rota SPA (fallback para `index.html`).
  * Opção B: **nginx** dedicado servindo estático, proxy para `/api` → FastAPI.

---

## Estrutura de Código (resumo)

### Frontend SPA (Vite/React) (`/web`)

* **src/routes/**: `Overview.tsx`, `Roadmap.tsx`, `Items.tsx`, `Requests.tsx`, `RequestDetail.tsx`, `Backlog.tsx`, `Settings.tsx`.
* **src/components/**: `KpiCard.tsx`, `ItemsTable.tsx`, `RequestForm.tsx`, `BacklogTable.tsx`, `Charts/*`, `Gantt/*`.
* **src/lib/**: `api.ts` (fetch wrapper com credenciais), `authGuard.tsx` (rota protegida), `formatters.ts`.
* **src/main.tsx** com React Router.
* **tailwind** configurado.

### FastAPI (`/api`)

* **main.py** (lifespan, routers)
* **routers/**: `auth.py`, `projects.py`, `items.py`, `requests.py`, `backlog.py`, `webhooks.py`, `sync.py`
* **services/**: `github.py` (GraphQL/REST), `sync.py`, `metrics.py`
* **models/** (SQLAlchemy) e **schemas/** (Pydantic)
* **db.py** (session), **security.py** (HMAC webhook, RBAC)

---

## OpenAPI (esqueleto)

```yaml
openapi: 3.0.3
info:
  title: Tactyo API
  version: 0.1.0
paths:
  /api/projects/{project_id}/overview:
    get:
      summary: KPIs e métricas
  /api/projects/{project_id}/items:
    get:
      summary: Itens do Project
  /api/requests:
    post:
      summary: Criar solicitação
    get:
      summary: Listar solicitações
  /api/requests/{id}:
    get:
      summary: Detalhar solicitação
    patch:
      summary: Atualizar solicitação
  /api/requests/{id}/approve:
    post:
      summary: Aprovar solicitação
  /api/backlog:
    get:
      summary: Listar backlog
    post:
      summary: Criar backlog
  /api/backlog/{id}:
    patch:
      summary: Atualizar backlog
  /api/github/sync/{project_id}:
    post:
      summary: Sincronização on-demand
  /api/github/webhooks:
    post:
      summary: Receber webhooks do GitHub
```

---

## User Stories & Critérios de Aceite

1. **Como viewer**, quero ver o dashboard com KPIs e lista de itens para entender rapidamente o andamento.

   * *Aceite*: Ao acessar `/`, vejo cards de KPI e um gráfico simples. A visão em `/roadmap` permite filtrar por Status.
2. **Como editor**, quero criar solicitações com título, descrição, impacto e prioridade.

   * *Aceite*: Em `/requests`, consigo criar; status inicial `under_review`.
3. **Como PM**, quero aprovar uma solicitação e convertê-la em backlog, criando Issue e adicionando ao Project.

   * *Aceite*: Botão **Aprovar** cria `backlog_item`, opcionalmente Issue e ProjectItem, e feedback de sucesso.
4. **Como admin**, quero configurar o Project (owner+number) e mapear fields para que o sync funcione.

   * *Aceite*: Em `/settings`, salvo owner/number e vejo teste de conexão OK.

---

## Testes (MVP)

* **Integração**: mock da API GraphQL do GitHub para
