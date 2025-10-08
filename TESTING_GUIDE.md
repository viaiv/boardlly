# Guia Completo de Testes - Hierarquia Épico > História > Tarefa

## 🚀 Setup Inicial

### 1. Preparar o Ambiente

```bash
# Terminal 1 - Backend
cd /home/leandroo/GitHub/tactyo/api
source venv/bin/activate
python run.py

# Terminal 2 - Frontend
cd /home/leandroo/GitHub/tactyo/web
npm run dev

# Terminal 3 - Testes (opcional)
cd /home/leandroo/GitHub/tactyo/api
source venv/bin/activate
```

### 2. Verificar Serviços

```bash
# Backend deve estar em:
http://localhost:8000
http://localhost:8000/docs  # Swagger UI

# Frontend deve estar em:
http://localhost:5173
```

---

## ✅ Checklist Rápido (5 minutos)

### Backend
- [ ] Servidor iniciou sem erros
- [ ] Migrations aplicadas com sucesso
- [ ] `/docs` abre corretamente
- [ ] Endpoints `/epics` aparecem no Swagger
- [ ] Endpoint `/hierarchy` aparece no Swagger

### Frontend
- [ ] Frontend compilou sem erros
- [ ] Consegue fazer login
- [ ] Menu mostra "Hierarquia" e "Épicos"
- [ ] Página `/epics` carrega
- [ ] Página `/hierarchy` carrega

---

## 📋 Teste 1: Executar Script de Testes Automatizado

```bash
cd /home/leandroo/GitHub/tactyo/api
source venv/bin/activate
python test_hierarchy.py
```

**O que verifica:**
- ✅ Função `derive_item_type_from_labels()` funciona
- ✅ Tabelas `project_item` e `epic_option` existem
- ✅ Campos hierárquicos foram criados
- ✅ Items têm labels e tipo derivado
- ✅ Estatísticas da hierarquia

**Resultado esperado:**
```
============================================================
TACTYO - Testes de Hierarquia Épico > História > Tarefa
============================================================

TESTE 1: Derivação de item_type a partir de labels
============================================================
✅ Labels: ['type:story', 'priority:high'], Title: None
   Esperado: story, Resultado: story
...

✅ Testes concluídos!
```

---

## 📋 Teste 2: API via Swagger UI (Recomendado para Iniciantes)

### Passo 1: Autenticar
1. Acesse **http://localhost:8000/docs**
2. Clique em **Authorize** (cadeado no topo direito)
3. Faça login em `POST /api/auth/login`:
   ```json
   {
     "email": "seu@email.com",
     "password": "suasenha"
   }
   ```

### Passo 2: Gerenciar Épicos

**2.1 Criar Épico**
- Endpoint: `POST /api/projects/{project_id}/epics`
- Body:
  ```json
  {
    "option_name": "Login e Autenticação",
    "color": "#0E8A16",
    "description": "Funcionalidades de login, registro e autenticação"
  }
  ```
- ✅ Deve retornar status 201 com o épico criado

**2.2 Listar Épicos**
- Endpoint: `GET /api/projects/{project_id}/epics`
- ✅ Deve retornar array com o épico criado

**2.3 Atualizar Épico**
- Endpoint: `PATCH /api/projects/{project_id}/epics/{epic_id}`
- Body:
  ```json
  {
    "option_name": "Login e Autenticação V2",
    "color": "#1D76DB"
  }
  ```
- ✅ Deve retornar status 200 com épico atualizado

**2.4 Deletar Épico**
- Endpoint: `DELETE /api/projects/{project_id}/epics/{epic_id}`
- ✅ Deve retornar status 204 (No Content)

### Passo 3: Visualizar Hierarquia

**3.1 Buscar Hierarquia**
- Endpoint: `GET /api/projects/{project_id}/hierarchy`
- ✅ Deve retornar estrutura JSON com:
  ```json
  {
    "epics": [...],
    "orphans": [...]
  }
  ```

---

## 📋 Teste 3: Frontend Interativo

### Passo 1: Login
1. Acesse **http://localhost:5173/login**
2. Faça login com suas credenciais
3. ✅ Deve redirecionar para Overview

### Passo 2: Gerenciar Épicos (Interface Visual)

**2.1 Acessar Página de Épicos**
- URL: **http://localhost:5173/epics**
- ✅ Página carrega sem erros
- ✅ Se vazio: mensagem "Nenhum épico cadastrado"

**2.2 Criar Épico**
1. Clique em **"Novo Épico"**
2. Preencha:
   - Nome: `Login e Autenticação`
   - Cor: `#0E8A16` (verde)
   - Descrição: `Funcionalidades de login`
3. Clique em **"Criar"**
4. ✅ Toast de sucesso aparece
5. ✅ Card do épico aparece na lista

**2.3 Editar Épico**
1. Clique no ícone de lápis (✏️) no card
2. Altere o nome para: `Login e Auth V2`
3. Altere a cor para: `#1D76DB` (azul)
4. Clique em **"Salvar"**
5. ✅ Toast de sucesso
6. ✅ Card atualiza com nova cor

**2.4 Deletar Épico**
1. Clique no ícone de lixeira (🗑️)
2. Confirme a deleção
3. ✅ Toast de sucesso
4. ✅ Card desaparece da lista

**2.5 Criar Múltiplos Épicos** (para teste de hierarquia)
Crie 3 épicos:
```
1. Login e Autenticação (#0E8A16 - verde)
2. Dashboard (#1D76DB - azul)
3. Relatórios (#6F42C1 - roxo)
```

### Passo 3: Visualizar Hierarquia

**3.1 Acessar Página de Hierarquia**
- URL: **http://localhost:5173/hierarchy**
- ✅ Página carrega sem erros
- ✅ Estatísticas aparecem no topo

**3.2 Verificar Estatísticas**
- ✅ Cards mostram contagem por tipo (story, task, feature, bug)
- ✅ Números correspondem aos items do projeto

**3.3 Verificar Épicos**
- ✅ Cards de épicos aparecem
- ✅ Items estão agrupados por épico
- ✅ Seção "Outros" aparece se houver items sem épico

**3.4 Expandir/Colapsar Items**
1. Clique na seta (▶️) ao lado de um item
2. ✅ Item expande mostrando filhos
3. Clique novamente
4. ✅ Item colapsa ocultando filhos

**3.5 Verificar Cores por Tipo**
- 🔵 Azul = Story
- 🟢 Verde = Task
- 🟣 Roxo = Feature
- 🔴 Vermelho = Bug
- ⚪ Cinza = Undefined

---

## 📋 Teste 4: Integração com GitHub Projects

### Passo 1: Preparar GitHub
1. Acesse seu projeto no GitHub Projects V2
2. Adicione labels nas issues:
   ```
   type:story    → Issues que são histórias
   type:task     → Issues que são tarefas
   type:feature  → Issues que são features
   type:bug      → Issues que são bugs
   ```
3. Ou use prefixo no título:
   ```
   HISTORY: User Login → será classificado como story
   ```

### Passo 2: Sincronizar Projeto

**Via Frontend:**
1. No menu, selecione o projeto
2. Vá em Settings
3. Clique em "Sincronizar"

**Via API (curl):**
```bash
# Obtenha o cookie de sessão primeiro fazendo login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "seu@email.com", "password": "senha"}' \
  -c cookies.txt

# Sincronize o projeto
curl -X POST http://localhost:8000/api/github/sync \
  -H "X-Project-Id: 1" \
  -b cookies.txt
```

### Passo 3: Verificar Dados Sincronizados

**Via SQL (PostgreSQL):**
```sql
-- Ver items com labels
SELECT id, title, item_type, labels, epic_name
FROM project_item
LIMIT 10;

-- Ver items por tipo
SELECT item_type, COUNT(*)
FROM project_item
GROUP BY item_type;

-- Ver relações pai-filho
SELECT
  p.title as pai,
  p.item_type as tipo_pai,
  c.title as filho,
  c.item_type as tipo_filho
FROM project_item c
JOIN project_item p ON c.parent_item_id = p.id;
```

**Via API:**
```bash
# Ver items do projeto
curl http://localhost:8000/api/projects/1/items \
  -b cookies.txt | jq .

# Ver hierarquia completa
curl http://localhost:8000/api/projects/1/hierarchy \
  -b cookies.txt | jq .
```

### Passo 4: Verificar no Frontend
1. Acesse **http://localhost:5173/hierarchy**
2. Clique em **"Atualizar"**
3. ✅ Items sincronizados aparecem
4. ✅ Items estão agrupados por épico
5. ✅ Tipos foram derivados corretamente

---

## 📋 Teste 5: Testes de Borda (Edge Cases)

### Teste 5.1: Item sem Label
1. Crie issue no GitHub sem label `type:*`
2. Sincronize projeto
3. ✅ Item aparece com `item_type: null`
4. ✅ Círculo é cinza na hierarquia

### Teste 5.2: Item com Múltiplas Labels
1. Crie issue com labels: `type:story`, `priority:high`, `area:backend`
2. Sincronize
3. ✅ `item_type` = `story` (primeiro type encontrado)
4. ✅ Array `labels` contém todas as labels

### Teste 5.3: História com Prefixo
1. Crie issue com título: `HISTORY: User Registration`
2. Não adicione label `type:story`
3. Sincronize
4. ✅ `item_type` = `story` (derivado do prefixo)

### Teste 5.4: Projeto sem Épicos
1. Remova todos os épicos
2. Acesse `/hierarchy`
3. ✅ Mensagem: "Nenhum épico cadastrado"
4. ✅ Seção "Outros" mostra todos os items

### Teste 5.5: Épico sem Items
1. Crie épico novo
2. Não associe items a ele
3. Acesse `/hierarchy`
4. ✅ Card do épico aparece vazio
5. ✅ Mensagem: "Nenhum item neste épico"

---

## 🐛 Troubleshooting

### Problema: Hierarquia vazia no frontend

**Diagnóstico:**
```bash
# 1. Verificar se há items no banco
cd api
source venv/bin/activate
python -c "
from app.db.session import SessionLocal
from app.models.project_item import ProjectItem
from sqlalchemy import select, func
import asyncio

async def check():
    async with SessionLocal() as db:
        stmt = select(func.count(ProjectItem.id))
        result = await db.execute(stmt)
        count = result.scalar()
        print(f'Total de items: {count}')

asyncio.run(check())
"
```

**Soluções:**
1. Se count = 0: Precisa sincronizar projeto do GitHub
2. Se count > 0: Verificar se `labels` e `item_type` estão preenchidos
3. Verificar console do navegador (F12) para erros

### Problema: Labels não derivam tipo

**Causa:** Labels do GitHub não têm formato `type:*`

**Solução:**
```bash
# Adicionar labels no GitHub:
# - type:story
# - type:task
# - type:feature
# - type:bug

# Depois re-sincronizar
curl -X POST http://localhost:8000/api/github/sync \
  -H "X-Project-Id: 1" \
  -b cookies.txt
```

### Problema: Épicos não aparecem no frontend

**Diagnóstico:**
```bash
# Verificar no banco
psql -U tactyo -d tactyo
SELECT * FROM epic_option;
```

**Soluções:**
1. Criar épicos via `/epics` no frontend
2. Verificar se está logado
3. Verificar se projeto está selecionado
4. Verificar console do navegador para erros de API

### Problema: Toast não aparece

**Causa:** Sonner não está configurado no App

**Solução:**
Verificar se `<Toaster />` está no componente raiz do app.

---

## 📊 Métricas de Sucesso

Após completar todos os testes, você deve ter:

### Backend
- ✅ 2 novas tabelas criadas (epic_option)
- ✅ 3 novos campos em project_item (item_type, parent_item_id, labels)
- ✅ 5 endpoints de épicos funcionando
- ✅ 1 endpoint de hierarquia funcionando
- ✅ Labels sendo capturadas na sincronização
- ✅ item_type sendo derivado automaticamente

### Frontend
- ✅ 2 novas páginas funcionando (/epics, /hierarchy)
- ✅ CRUD completo de épicos
- ✅ Visualização hierárquica com expand/collapse
- ✅ Estatísticas por tipo
- ✅ Cores por tipo
- ✅ Notificações (toast) funcionando

### Banco de Dados
```sql
-- Verificação final
SELECT
  (SELECT COUNT(*) FROM epic_option) as epics,
  (SELECT COUNT(*) FROM project_item WHERE item_type IS NOT NULL) as typed_items,
  (SELECT COUNT(*) FROM project_item WHERE parent_item_id IS NOT NULL) as child_items,
  (SELECT COUNT(*) FROM project_item WHERE labels IS NOT NULL) as items_with_labels;
```

---

## 🎯 Próximos Passos (Opcional)

Após validar que tudo funciona, você pode:

1. **Fase 2: GitHub GraphQL Integration**
   - Implementar mutations para criar/atualizar épicos no GitHub
   - Sincronizar relationships bidirecionalmente

2. **Fase 3: Frontend Enhancements**
   - Drag & drop entre épicos
   - Filtros avançados
   - Busca de items

3. **Fase 4: React Flow Visualization**
   - Visualização em grafo
   - Layout automático
   - Interações avançadas

4. **Fase 5: Polish**
   - Testes E2E com Playwright/Cypress
   - Documentação de usuário
   - Performance tuning

---

## 📝 Relatório de Testes

Use este template para documentar seus testes:

```markdown
# Relatório de Testes - Hierarquia

**Data:** [DATA]
**Testador:** [NOME]

## Ambiente
- Backend: ✅ OK / ❌ FALHOU
- Frontend: ✅ OK / ❌ FALHOU
- Banco: ✅ OK / ❌ FALHOU

## Testes Executados

### Backend
- [ ] Script automatizado passou
- [ ] Endpoints de épicos funcionam
- [ ] Endpoint de hierarquia funciona
- [ ] Sincronização captura labels

### Frontend
- [ ] Página /epics funciona
- [ ] Página /hierarchy funciona
- [ ] CRUD de épicos funciona
- [ ] Visualização hierárquica funciona

### Integração
- [ ] Sincronização GitHub funciona
- [ ] Labels derivam tipo corretamente
- [ ] Épicos agrupam items
- [ ] Hierarquia pai-filho funciona

## Problemas Encontrados
[LISTAR PROBLEMAS]

## Observações
[OBSERVAÇÕES GERAIS]
```

---

## 🆘 Suporte

Se encontrar problemas não documentados aqui:

1. **Backend errors**: Verificar logs em `python run.py`
2. **Frontend errors**: Abrir DevTools (F12) > Console
3. **Database issues**: Verificar migrations com `alembic current`
4. **GitHub sync issues**: Verificar token e permissões

**Debug mode:**
```bash
# Backend com mais logs
DEBUG=true python run.py

# Frontend com source maps
npm run dev -- --debug
```
