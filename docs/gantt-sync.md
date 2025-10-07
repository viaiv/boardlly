# Gantt Timeline & Bidirectional Sync

## Objetivos
- Exibir itens sincronizados do GitHub Projects em uma visualização de Gantt com atualização contínua.
- Permitir edição das janelas (início/fim) diretamente no Tactyo, refletindo as alterações no Project v2.
- Manter compatibilidade com a visualização em colunas já existente (Roadmap Board).

## Escopo
- **Inclui**: leitura e escrita de campos de data (iteration, due date, custom dates), controles de UI para ajustes, resolução básica de conflitos e auditoria mínima.
- **Não inclui**: criação de itens GitHub, reordenação de colunas Project, alterações massivas (bulk) ou suporte offline.

## Terminologia
- **Project Item**: cartão sincronizado a partir do Project v2.
- **Timeframe**: período exibido na barra do Gantt (data inicial/final).
- **Fonte de verdade**: Project v2 é a referência oficial; Tactyo atua como cliente com cache.

## Requisitos de Dados
- **Campos obrigatórios** por item:
  - `start_date` e `end_date` normalizados em UTC.
  - `iteration_start` e `iteration_end` (quando o item estiver em uma iteration GitHub).
  - `due_date` (target date) para fallback.
  - `remote_updated_at` para conciliação de concorrência.
- **Mapeamentos necessários**:
  - Persistir `field_mappings` com IDs dos campos de Project v2 (Iteration, Target Date, Start/End custom).
  - Registrar a opção/ID de cada iteration para usar em mutações.
- **Validação**:
  - Garantir `end_date >= start_date` ao salvar.
  - Permitir itens sem datas (serão exibidos em seção "Sem datas").
- **Auditoria mínima**: registrar `synced_at` e `last_edited_by` (quando editado via Tactyo) para rastreio.

## Sincronização (GitHub → Tactyo)
1. **Fetch GraphQL** do Project v2 incluindo:
   - `items { fieldValuesByName { name, value, ... } }` com Iteration, Target Date, quaisquer campos custom.
   - `updatedAt` do item e do campo.
2. **Normalização**:
   - Iteration → `iteration_start`/`iteration_end` e usar como fallback para `start_date`/`end_date` quando custom não existir.
   - Target Date → `end_date` quando não houver iteration/end custom.
   - Definir `start_date` a partir de campo custom; se ausente, usar `iteration_start`; em último caso, `updatedAt` ou `createdAt` para visualização.
3. **Persistência** (`project_item`):
   - Novas colunas: `start_date`, `end_date`, `iteration_start`, `iteration_end`, `due_date`, `remote_updated_at`, `last_local_edit_at`, `last_local_edit_by`.
   - Atualizar somente quando `remote_updated_at` recebido for mais recente que o armazenado.
4. **Mappings**:
   - Tabela `github_project_field` (nova) para armazenar `field_name`, `field_id`, `field_type`, `options` (para iteration IDs).
5. **API**:
   - `/api/projects/current/items` passa a retornar as datas normalizadas e vínculos (`iteration_id`, `iteration_duration`, `epic_option_id`, `epic_name`).
   - Paginação ou filtros opcionais para janelas de tempo (ex.: `?from=2025-01-01&to=2025-03-31`).

## Sincronização (Tactyo → GitHub)
1. **Endpoints REST**
   - `PATCH /api/projects/current/items/{id}` com payload `{ start_date?, end_date?, iteration_id?, due_date?, epic_option_id? }`.
   - Validar permissões (`owner|admin` por default, permitir delegar?).
   - Verificar `remote_updated_at` enviado pelo cliente para evitar overwrite: recusar caso o GitHub tenha sido alterado depois.
2. **Mutações GraphQL**
   - `updateProjectV2ItemFieldValue` para Target Date / campos custom.
   - `updateProjectV2ItemFieldValue` com `iterationId` para mover entre iterations.
   - `projectV2ItemFieldValueDelete` para limpar datas removidas.
   - Reutilizar tokens já configurados; garantir escopo `project`, `repo` ou `org` com escrita.
3. **Workflow**
   - Receber PATCH → validar → chamar mutação → atualizar DB com resposta (`remote_updated_at` retornado).
   - Se mutação falhar (ex.: campo bloqueado), devolver 409/422 com mensagem.
4. **Resolução de Conflitos**
   - Guardar `remote_updated_at` e comparar antes de enviar mutação.
   - Se conflito: retornar 409 com `current_remote_updated_at` para UI decidir (refetch e sugerir merge manual).
5. **Observabilidade**
   - Logar mutações com metadata (item, campos, usuário).
   - Eventualmente integrar Webhooks Project v2 (quando disponível) para reduzir pull manual.

## Backend: Alterações Necessárias
- **Migrações**
  - Criar tabela `github_project_field` com colunas `project_id`, `field_name`, `field_id`, `field_type`, `options` (JSONB), `updated_at`.
  - Alterar `project_item` adicionando as colunas listadas e índices por `start_date`/`end_date` para filtros temporais.
- **Camada de serviço**
  - Expandir `sync_github_project_items` para popular novos campos e atualizar `github_project_field`.
  - Implementar serviço `update_project_item_dates` que encapsula validações e mutações GraphQL.
- **Schemas**
  - Atualizar `ProjectItemResponse` e criar `ProjectItemUpdateRequest`.
- **Autorização**
  - Reaproveitar `require_roles` para garantir que apenas roles com permissão alterem o Gantt.
- **Testes**
  - Fixtures com cargas GraphQL contendo iterations e campos custom.
  - Casos: normalização de dados, conflitos de atualização, validações de payload e fallback de datas.

## Frontend: Visualização e Edição
- **Layout**
  - Toggle em `/roadmap` para alternar `Board / Timeline` (armazenar preferência localmente).
  - Gantt ocupar largura total, com header mostrando escala (semanas/meses) e barra rolável horizontalmente.
- **Bibliotecas**
  - Opções avaliadas: `visx` (custom), `frappe-gantt`, `d3-gantt` wrappers. `visx` dá controle total e funciona bem com Tailwind.
- **Estado**
  - Hook `useProjectItems` compartilhado entre board e Gantt.
  - Calcular `timeframe` a partir das datas normalizadas e manter itens sem data em lista separada.
- **Interações**
  - Arrastar bordas da barra para ajustar início/fim → envia PATCH após debounce/confirm.
  - Dropdown para mudar iteration (lista das opções sincronizadas).
  - Botão para limpar datas (remove campo custom e iteration).
- **Feedback**
  - Indicadores de carregamento e de conflito (ex.: tooltip “Atualizado no GitHub por X há 2 min”).
  - Guarda de confirmação quando usuário sai com alterações não salvas.
- **Acessibilidade**
  - Permitir edição via formulário modal além do drag (teclado).
- **Testes Front**
  - Vitest + Testing Library cobrindo cálculo de barras e PATCH, testes end-to-end (Playwright) para arrastar/soltar.

## Segurança & Operação
- Tokens devem ter escopo mínimo; documentar necessidade de permissão de escrita.
- Rate limits: agrupar atualizações em batch quando usuário fizer múltiplos ajustes (Throttle).
- Registrar quem alterou (`last_local_edit_by`) para auditoria.
- Prever fallback read-only se mutações retornarem erro 403 (token sem escopo).

## Rollout
1. Lançar backend com campos e endpoint PATCH (feature flag desativada na UI).
2. Atualizar frontend com visualização apenas leitura (sem edição) para coletar feedback.
3. Habilitar edição via flag por conta após validações.
4. Medir métricas: número de edições, erros 409, tempo médio de sync.

## Pontos em Aberto
- Confirmar quais campos Project v2 serão usados como fonte (Iteration sempre presente? precisamos criar Start/End custom?).
- Definir política quando apenas `due_date` existe — assumir `start_date = due_date - 1 dia` ou exigir start explícito?
- Avaliar uso de webhooks vs. cron para sync incremental.
- Necessidade de histórico de mudanças (audit log externo?).
