/**
 * API client for Story management endpoints
 */

import { apiFetch } from "./api";

export interface StoryCreateData {
  title: string;
  description?: string;
  repository: string;
  epic_option_id?: string | null;
  labels?: string[];
}

export interface StoryFormTemplate {
  // Visão Geral
  problema_atual: string;
  objetivo_resultado: string;

  // Hipótese de Valor
  hipotese_valor: string;

  // Critérios de Aceite
  criterios_aceite: string;

  // Experiência do Usuário
  fluxo_usuario: string;

  // Regras de Negócio
  permissoes: string;
  impacto_github: string;
  jobs_sincronizacao: string;
  dados_persistidos: string;

  // Dependências & Riscos
  dependencias_tecnicas: string;

  // Métricas & Observabilidade
  telemetria: string;
  kpis_alvo: string;
  logs_alertas: string;

  // Plano de QA
  testes_automatizados: string;
  cobertura_minima: string;
  cenarios_manuais: string;
  dados_teste: string;
}

export interface StoryCreateResponse {
  issue_number: number;
  issue_url: string;
  issue_node_id: string;
}

/**
 * Gera o corpo da issue formatado seguindo o template Tactyo
 */
export function generateStoryTemplate(template: StoryFormTemplate): string {
  return `# Histórias Tactyo

- Alinhe cada história ao fluxo principal (Dashboard, Solicitações, Backlog, Sprints, Setup do Projeto) e às personas do RBAC (viewer, editor, pm, admin, owner).
- Capture impacto na integração com GitHub Projects (campos obrigatórios, sync jobs, webhooks) e efeitos sobre métricas/relatórios do dashboard.
- Garanta critérios de aceite claros em formato Given/When/Then, cobrindo estados do item (pending → approved → converted) e validações de segurança/permissões.
- Liste dependências (jobs APScheduler, tokens GitHub, migrações Alembic) e anexos esperados (wireframes, GraphQL queries, referências em docs/).
- Inclua plano de QA com testes unitários (npm test, pytest), smoke manual e coberturas/metas relevantes.

## Visão Geral
- **Problema atual**: ${template.problema_atual || '_A definir_'}
- **Objetivo/Resultado**: ${template.objetivo_resultado || '_A definir_'}

## Hipótese de Valor
${template.hipotese_valor || 'Se entregarmos `<mudança proposta>`, esperamos `<métrica/efeito medível>` porque `<insight ou evidência>`.'}

## Critérios de Aceite (Given/When/Then)
${template.criterios_aceite || '_A definir_'}

## Experiência do Usuário
- **Fluxo resumido**: ${template.fluxo_usuario || '_A definir_'}

## Regras de Negócio Tactyo
- **Permissões**: ${template.permissoes || '_A definir - quem pode ver/editar/aprovar_'}
- **Impacto GitHub Projects**: ${template.impacto_github || '_A definir - queries/mutações, campos customizados, tokens_'}
- **Jobs/Sincronização**: ${template.jobs_sincronizacao || '_A definir - cron ou gatilho webhook impactado_'}
- **Dados persistidos**: ${template.dados_persistidos || '_A definir - tabelas/campos FastAPI/Postgres_'}

## Dependências & Riscos
- **Técnicas**: ${template.dependencias_tecnicas || '_A definir - módulos, migrações, feature flags_'}

## Métricas & Observabilidade
- **Telemetria**: ${template.telemetria || '_A definir - eventos, dashboards_'}
- **KPIs alvo**: ${template.kpis_alvo || '_A definir - ex: tempo de aprovação, itens convertidos_'}
- **Logs/alertas**: ${template.logs_alertas || '_A definir - ajustes em logging/monitoramento_'}

## Plano de QA
- **Testes automatizados**: ${template.testes_automatizados || '_A definir - unit/integração, caminhos feliz/triste_'}
- **Cobertura mínima**: ${template.cobertura_minima || '_A definir - % ou arquivos-chave_'}
- **Cenários manuais**: ${template.cenarios_manuais || '_A definir - checklist para smoke na dev/staging_'}
- **Dados de teste**: ${template.dados_teste || '_A definir - fixtures ou scripts necessários_'}

## Checklist de Entrega
- [ ] Docs atualizados (\`docs/\`, \`README\`, \`docs/test-plan.md\` se aplicável)
- [ ] Scripts/comandos adicionados em \`package.json\` + \`docs/commands.md\` (quando houver)
- [ ] Variáveis ambiente documentadas em \`docs/configuration.md\`
- [ ] Feature flag/config toggles revisados
`;
}

/**
 * Create a new story (issue) in GitHub
 */
export async function createStory(data: StoryCreateData): Promise<StoryCreateResponse> {
  return apiFetch<StoryCreateResponse>(`/api/projects/current/stories`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}
