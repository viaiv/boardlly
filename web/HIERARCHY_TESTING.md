# Testando Hierarquia no Frontend

Guia completo para testar a implementação de épico → história → tarefa no frontend.

## 🚀 Iniciar o Frontend

```bash
cd /home/leandroo/GitHub/tactyo/web
npm install  # Se ainda não instalou as dependências
npm run dev
```

O frontend estará disponível em: **http://localhost:5173**

## 📋 Páginas Implementadas

### 1. **Gerenciamento de Épicos** (`/epics`)

**URL:** http://localhost:5173/epics

**Funcionalidades:**
- ✅ Listar todos os épicos do projeto
- ✅ Criar novo épico com nome, cor e descrição
- ✅ Editar épico existente
- ✅ Deletar épico
- ✅ Visualização em cards coloridos

**Como testar:**
1. Acesse `/epics`
2. Clique em "Novo Épico"
3. Preencha:
   - Nome: "Login e Autenticação"
   - Cor: escolha uma cor (ex: #0E8A16)
   - Descrição: "Funcionalidades de login, registro e autenticação"
4. Clique em "Criar"
5. Teste edição clicando no ícone de lápis
6. Teste deleção clicando no ícone de lixeira

### 2. **Visualização de Hierarquia** (`/hierarchy`)

**URL:** http://localhost:5173/hierarchy

**Funcionalidades:**
- ✅ Visualização em árvore épico → história → tarefa
- ✅ Estatísticas por tipo de item (story, task, feature, bug)
- ✅ Agrupamento por épico
- ✅ Items sem épico em seção "Outros"
- ✅ Expandir/colapsar items com filhos
- ✅ Badges coloridos por tipo
- ✅ Atualização manual

**Como testar:**
1. Acesse `/hierarchy`
2. Veja as estatísticas no topo (stories, tasks, features, bugs)
3. Expanda/colapse items clicando nas setas
4. Verifique os cards de épicos
5. Verifique a seção "Outros" para items sem épico
6. Clique em "Atualizar" para recarregar

## 🎨 Cores por Tipo de Item

- **Story** (história): 🔵 Azul
- **Task** (tarefa): 🟢 Verde
- **Feature** (funcionalidade): 🟣 Roxo
- **Bug** (erro): 🔴 Vermelho
- **Undefined** (indefinido): ⚪ Cinza

## 🔄 Fluxo de Teste Completo

### Passo 1: Criar Épicos
```
1. Acesse /epics
2. Crie 2-3 épicos:
   - "Login e Autenticação" (#0E8A16 - verde)
   - "Dashboard" (#1D76DB - azul)
   - "Relatórios" (#6F42C1 - roxo)
```

### Passo 2: Sincronizar Projeto do GitHub
```
1. Certifique-se de que o backend está rodando
2. Tenha um projeto GitHub conectado
3. No frontend, clique em "Sincronizar" ou use a API:
   curl -X POST http://localhost:8000/api/github/sync \
     -H "X-Project-Id: 1" \
     -b cookies.txt
```

### Passo 3: Verificar Labels no GitHub
Para que os items sejam classificados automaticamente, adicione labels no GitHub:
```
- type:story  → Issues que são histórias
- type:task   → Issues que são tarefas
- type:feature → Issues que são features
- type:bug    → Issues que são bugs
```

Ou use o prefixo no título:
```
- "HISTORY: User Login" → será classificado como story
```

### Passo 4: Ver Hierarquia
```
1. Acesse /hierarchy
2. Veja a estrutura organizada por épicos
3. Expanda items para ver filhos
4. Verifique as estatísticas
```

## 🐛 Troubleshooting

### Épicos não aparecem
- ✅ Verifique se o backend está rodando (http://localhost:8000)
- ✅ Verifique se você está logado
- ✅ Verifique se tem um projeto selecionado
- ✅ Abra o console do navegador (F12) para ver erros

### Hierarquia vazia
- ✅ Sincronize o projeto do GitHub primeiro
- ✅ Verifique se existem issues no projeto do GitHub
- ✅ Adicione labels `type:*` nas issues do GitHub
- ✅ Re-sincronize após adicionar labels

### Erro de CORS
```bash
# Verifique o .env.local do frontend
VITE_API_BASE_URL=http://localhost:8000

# Verifique o .env do backend
TACTYO_CORS_ORIGINS=["http://localhost:5173"]
```

### Items não têm tipo (item_type)
Os tipos são derivados de:
1. Labels: `type:story`, `type:task`, `type:feature`, `type:bug`
2. Título: prefixo `HISTORY:` indica story

Adicione essas labels no GitHub e re-sincronize.

## 📊 Endpoints da API Usados

```typescript
// Épicos
GET    /api/projects/{id}/epics          // Lista épicos
POST   /api/projects/{id}/epics          // Cria épico
GET    /api/projects/{id}/epics/{id}     // Busca épico
PATCH  /api/projects/{id}/epics/{id}     // Atualiza épico
DELETE /api/projects/{id}/epics/{id}     // Deleta épico

// Hierarquia
GET    /api/projects/{id}/hierarchy      // Busca hierarquia completa
```

## 🎯 Checklist de Testes

### Épicos (/epics)
- [ ] Página carrega sem erros
- [ ] Lista de épicos aparece (ou mensagem de vazio)
- [ ] Consegue criar novo épico
- [ ] Cor do épico é exibida corretamente
- [ ] Consegue editar épico
- [ ] Consegue deletar épico (com confirmação)
- [ ] Toast de sucesso/erro aparece

### Hierarquia (/hierarchy)
- [ ] Página carrega sem erros
- [ ] Estatísticas aparecem no topo
- [ ] Épicos são listados em cards
- [ ] Items são agrupados por épico
- [ ] Consegue expandir/colapsar items
- [ ] Cores dos tipos estão corretas
- [ ] Badges de tipo e status aparecem
- [ ] Seção "Outros" aparece se houver items sem épico
- [ ] Botão "Atualizar" funciona

## 💡 Próximos Passos

Para melhorar a experiência:

1. **React Flow**: Visualização em grafo (Fase 4 do design)
2. **Drag & Drop**: Mover items entre épicos
3. **Filtros**: Filtrar por tipo, status, épico
4. **Busca**: Buscar items por texto
5. **Edição inline**: Editar title/status direto na hierarquia
6. **Sincronização automática**: WebSocket ou polling

## 📝 Estrutura de Arquivos Criados

```
web/src/
├── lib/
│   ├── epics.ts          # API client para épicos
│   └── hierarchy.ts      # API client e helpers para hierarquia
├── routes/
│   ├── Epics.tsx         # Página de gerenciamento de épicos
│   ├── Hierarchy.tsx     # Página de visualização hierárquica
│   └── AppRoutes.tsx     # Rotas atualizadas
└── components/
    └── layout/
        └── AppShell.tsx  # Menu de navegação atualizado
```

## 🎨 Componentes UI Utilizados

Os componentes são do **shadcn/ui**:
- Card, CardHeader, CardTitle, CardContent, CardDescription
- Button
- Dialog, DialogContent, DialogHeader, DialogTitle
- Input, Textarea, Label
- Badge
- useToast (para notificações)
- Loader2 (ícone de loading)

Todos já estão disponíveis no projeto.
