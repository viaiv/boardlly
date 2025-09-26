# Campos Customizados Tactyo no GitHub Projects

## Objetivo
Criar e manter um conjunto padronizado de campos `tactyo_*` nos Projects v2 selecionados, permitindo que o Tactyo controle datas, milestones, funcionalidades e métricas próprias sem conflitar com configurações da equipe. Esses campos serão a base para visões estratégicas (Gantt, dashboards executivos) e para sincronização bidirecional mais segura.

## Visão Geral
- Toda vez que um projeto é conectado ou criado via Tactyo, conferimos (ou provisionamos) os campos necessários.
- Armazenamos os `field_id` em nossa base para operarmos por ID (mesmo que renomeiem o campo manualmente).
- Os campos servem como fonte de verdade para o Gantt, agrupamentos por feature/milestone e indicadores de progresso.
- Usuário pode optar por não criá-los e mapear manualmente campos existentes.

## Catálogo de Campos `tactyo_*`
| Nome sugerido        | Tipo              | Uso                                                         |
|----------------------|-------------------|-------------------------------------------------------------|
| `tactyo_feature`     | Single select     | Agrupar itens por funcionalidade/tema                       |
| `tactyo_feature_rank`| Number (float)    | Ordem/prioridade dentro da feature                          |
| `tactyo_milestone`   | Single select     | Vincular item a um marco estratégico                        |
| `tactyo_milestone_start` | Date         | Data de início do milestone (usado em Gantt)                |
| `tactyo_milestone_end`   | Date         | Data de término do milestone                                |
| `tactyo_start_date`  | Date              | Data de início planejada do item                            |
| `tactyo_end_date`    | Date              | Data de término planejada (fallback para timeline)          |
| `tactyo_story_points`| Number (float)    | Estimativa padronizada pelo Tactyo                          |
| `tactyo_health`      | Single select     | Status qualitativo (ex.: On Track, Risk, Off Track)         |
| `tactyo_notes`       | Text              | Observações estratégicas exibidas em relatórios             |

> Podemos começar com o subconjunto essencial (`tactyo_feature`, `tactyo_milestone`, `tactyo_start_date`, `tactyo_end_date`) e habilitar os demais via feature flag.

## Fluxo de Provisionamento
1. **Conexão do Projeto**
   - Após o usuário escolher ou criar um Project, chamamos `listProjects`/`projectV2` para obter `fields` existentes.
   - Construímos um mapa `nome -> (id, type)`. Para cada campo `tactyo_*`, verificamos se já existe (mesmo nome + tipo compatível).
2. **Criação de Campos Ausentes**
   - Para cada campo inexistente, executamos a mutation `createProjectV2Field` com `dataType` apropriado.
   - Para single select, definimos opções iniciais padrão (ex.: `Em Descoberta`, `Em Execução`, `Concluído`). Usuário pode editar depois.
   - Guardamos `field_id`, `field_name`, `field_type`, `options` em `github_project_field`.
3. **Persistência Local**
   - Atualizamos `github_project.field_mappings` com os metadados atualizados.
   - Caso usuário opte por **não** criar campos, abrimos wizard para mapear manualmente os campos existentes (armazenando `field_id` selecionado).

## Uso nas Sincronizações
- **Leitura (GitHub → Tactyo)**: o sync lê os campos `tactyo_*`, popula `project_item` com valores normalizados (`feature`, `milestone`, datas). Isso alimenta Gantt e dashboards.
- **Escrita (Tactyo → GitHub)**: quando usuário ajusta feature, milestone ou datas no Tactyo, enviamos mutation `updateProjectV2ItemFieldValue` usando os `field_id` armazenados. Como os campos são nossos, não há risco de sobrescrever dados do time.
- **Fallback**: se o campo estiver indisponível (ex.: usuário deletou), marcamos como “carente” e oferecemos recriação/mapeamento na UI.

## UI & Experiência do Usuário
- **Settings › GitHub**: mostrar status de cada campo `tactyo_*` (OK, ausente, re-criar). Botão para “Criar/Reconfigurar campos Tactyo”.
- **Roadmap**: habilitar filtros/agrupadores por `tactyo_feature` e `tactyo_milestone`. Gantt usa `tactyo_start_date`/`tactyo_end_date` ou, caso ausentes, `tactyo_milestone_*`.
- **Visão Executiva (futuro)**: cards com progresso por milestone/feature, destacando saúde (`tactyo_health`).
- **Personalização**: permitir renomear as opções de single select diretamente pelo Tactyo (envia mutation para atualizar opções no Project).

## Permissões & Segurança
- PAT/App GitHub precisa de escopo `project` (write). Documentar claramente esse requisito.
- Guardamos `field_id` para evitar operações por nome. Mesmo que usuário renomeie, continuamos operando por ID. Se o campo for deletado, detectamos na próxima sync.
- Opcional: permitir trabalhar em modo read-only se usuário não conceder permissão de escrita (nesse caso, apenas leitura dos campos existentes).

## Migração & Compatibilidade
- **Projetos já integrados**: rodar script/migração que busca campos `tactyo_*`. Se não existir, oferecer pop-up “Criar campos Tactyo?”.
- **Dados legados**: se cliente já possui campos com outra nomenclatura, a UI deve oferecer mapeamento manual (drop-down com `field_id`).
- **Projects criados pelo Tactyo**: gerar template com nossos campos já configurados e colunas básicas (Backlog, Em Progresso, Done).

## Roadmap de Implementação
1. _Backend_
   - [ ] Criar helpers GraphQL para `createProjectV2Field`/`updateProjectV2SingleSelectFieldOptions`.
   - [ ] Atualizar `sync_github_project` para provisionar campos (através de serviço `ensure_tactyo_fields`).
   - [ ] Ampliar `github_project_field` para armazenar `is_managed` (true/false) e data da última verificação.
2. _Frontend_
   - [ ] Settings: card “Campos Tactyo” mostrando status e ações (criar, restaurar, mapear manualmente).
   - [ ] Roadmap/Gantt: usar novos campos para filtros e agrupadores.
3. _Docs_
   - [ ] Atualizar `docs/gantt-sync.md` com dependência nos campos `tactyo_*`.
   - [ ] Escrever tutorial “Como o Tactyo usa campos customizados no GitHub Projects”.
4. _Opt-in & Flags_
   - [ ] Feature flag para introduzir gradualmente (permitindo clientes existentes migrarem sem fricção).

## Riscos & Mitigações
- **Mudanças manuais**: se usuário renomear ou excluir nossos campos, ícone de alerta aparece nas Settings e oferecemos recriação.
- **Limite de campos do GitHub**: Projects v2 impõem limites; garantir que não ultrapassamos (avaliar número máximo atual ~ 50 campos).
- **Conflito com workflows existentes**: permitir mapeamento manual e documentar como remover campos se necessário.
- **Performance**: criação em lote exige poucas mutations (8-10); podemos serializar e exibir feedback “Criando campos…”.

## Próximas Explorações
- Provisionar um “Project Template Tactyo” via API GraphQL, para permitir que usuário crie novos projetos já com fases e campos predefinidos.
- Aproveitar campos `tactyo_*` para gerar relatórios PDF/Slides automáticos (milestones, status, principais riscos).
- Criar automações (ex.: mover card para Done quando `tactyo_health = On Track` e `tactyo_end_date` < today) usando GitHub Workflows.
