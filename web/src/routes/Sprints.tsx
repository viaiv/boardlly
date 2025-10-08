import { useEffect, useState } from "react";
import { toast } from "sonner";
import { CalendarIcon, TrendingUpIcon, CheckCircle2Icon, InfoIcon, ExternalLinkIcon, RefreshCwIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { apiFetch } from "@/lib/api";

type StatusBreakdown = {
  status: string | null;
  count: number;
  total_estimate: number | null;
};

type IterationSummary = {
  iteration_id: string | null;
  name: string | null;
  start_date: string | null;
  end_date: string | null;
  item_count: number;
  completed_count: number;
  total_estimate: number | null;
  completed_estimate: number | null;
  status_breakdown: StatusBreakdown[];
};

type IterationOption = {
  id: string;
  name: string;
  start_date: string | null;
  end_date: string | null;
};

type DashboardResponse = {
  summaries: IterationSummary[];
  options: IterationOption[];
};

type ProjectInfo = {
  id: number;
  owner_login: string;
  project_number: number;
  name: string | null;
};

export function Sprints() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);

  useEffect(() => {
    loadProjectInfo();
    loadDashboard();
  }, []);

  async function loadProjectInfo() {
    try {
      const info = await apiFetch<ProjectInfo>("/api/projects/current");
      setProjectInfo(info);
    } catch (err) {
      console.error("Erro ao carregar informações do projeto:", err);
    }
  }

  async function loadDashboard() {
    try {
      setLoading(true);
      setError(null);

      const response = await apiFetch<DashboardResponse>(
        "/api/projects/current/iterations/dashboard"
      );

      setData(response);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Erro ao carregar sprints";
      setError(errorMessage);
      toast.error("Erro ao carregar sprints", {
        description: errorMessage,
      });
    } finally {
      setLoading(false);
    }
  }

  function formatDate(dateString: string | null): string {
    if (!dateString) return "Sem data";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(date);
  }

  function calculateProgress(completed: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((completed / total) * 100);
  }

  function getProgressColor(progress: number): string {
    if (progress >= 80) return "text-green-600";
    if (progress >= 50) return "text-yellow-600";
    return "text-red-600";
  }

  function isActiveSprint(sprint: IterationSummary): boolean {
    if (!sprint.start_date || !sprint.end_date) return false;
    const now = new Date();
    const start = new Date(sprint.start_date);
    const end = new Date(sprint.end_date);
    return now >= start && now <= end;
  }

  // Criar sprints a partir das options (inclui sprints vazias)
  const allSprints: IterationSummary[] = (data?.options || []).map((option) => {
    // Procurar summary correspondente (pode não existir se sprint estiver vazia)
    const summary = data?.summaries.find((s) => s.iteration_id === option.id);

    if (summary) {
      return summary;
    }

    // Sprint vazia - criar summary com valores zerados
    return {
      iteration_id: option.id,
      name: option.name,
      start_date: option.start_date,
      end_date: option.end_date,
      item_count: 0,
      completed_count: 0,
      total_estimate: 0,
      completed_estimate: 0,
      status_breakdown: [],
    };
  });

  // Separar sprints em ativas, futuras e passadas
  const activeSprints = allSprints.filter((s) => isActiveSprint(s));
  const otherSprints = allSprints.filter((s) => !isActiveSprint(s));
  const withoutSprint = data?.summaries.find((s) => !s.iteration_id) || null;

  return (
    <div className="space-y-6">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Sprints</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe o progresso e métricas das suas iterações
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => loadDashboard()}
          disabled={loading}
        >
          <RefreshCwIcon className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Atualizar
        </Button>
      </header>

      {/* Aviso sobre criação de sprints */}
      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4">
            <div className="flex gap-3">
              <InfoIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="space-y-3 flex-1">
                <div>
                  <p className="text-sm font-medium text-blue-900">
                    Como criar novas sprints
                  </p>
                  <p className="text-xs text-blue-700 mt-1">
                    Por limitação da API do GitHub, sprints precisam ser criadas diretamente no GitHub Projects
                  </p>
                </div>

                <div className="space-y-2">
                  <p className="text-sm text-blue-800 font-medium">Passo a passo:</p>
                  <ol className="text-sm text-blue-800 space-y-2 ml-4 list-decimal">
                    <li>
                      Acesse seu projeto no GitHub Projects
                      {projectInfo && (
                        <span className="block text-xs text-blue-600 mt-0.5">
                          {projectInfo.owner_login} · Projeto #{projectInfo.project_number}
                        </span>
                      )}
                    </li>
                    <li>Clique no ícone de <strong>⚙️ Settings</strong> (canto superior direito)</li>
                    <li>Na seção <strong>"Fields"</strong>, localize o campo <strong>"Iteration"</strong></li>
                    <li>Clique em <strong>"+ Add iteration"</strong></li>
                    <li>Configure o título, data de início e duração da sprint</li>
                  </ol>
                </div>

                <div className="bg-blue-100 border border-blue-300 rounded-lg p-3">
                  <p className="text-xs text-blue-900 font-medium mb-1">💡 Dica:</p>
                  <p className="text-xs text-blue-800">
                    Após criar uma sprint no GitHub, clique em "Atualizar" no canto superior direito desta página
                    ou aguarde até 15 minutos para sincronização automática.
                  </p>
                </div>
              </div>
            </div>

            {projectInfo && (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const url = `https://github.com/orgs/${projectInfo.owner_login}/projects/${projectInfo.project_number}/settings`;
                    window.open(url, "_blank", "noopener,noreferrer");
                  }}
                  className="text-blue-700 border-blue-300 hover:bg-blue-100"
                >
                  <ExternalLinkIcon className="h-4 w-4 mr-2" />
                  Abrir configurações do projeto
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {loading && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent className="space-y-3">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Erro */}
      {error && !loading && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Vazio */}
      {!loading && !error && data && data.summaries.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            Nenhuma sprint encontrada. Configure iterations no seu GitHub Project.
          </p>
        </div>
      )}

      {/* Sprints Ativas */}
      {!loading && !error && activeSprints.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUpIcon className="h-5 w-5 text-green-600" />
            Sprints Ativas
          </h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {activeSprints.map((sprint) => (
              <SprintCard key={sprint.iteration_id} sprint={sprint} isActive />
            ))}
          </div>
        </div>
      )}

      {/* Outras Sprints */}
      {!loading && !error && otherSprints.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Todas as Sprints</h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {otherSprints.map((sprint) => (
              <SprintCard key={sprint.iteration_id} sprint={sprint} />
            ))}
          </div>
        </div>
      )}

      {/* Itens sem Sprint */}
      {!loading && !error && withoutSprint && withoutSprint.item_count > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-muted-foreground">Sem Sprint</h2>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-2xl font-bold">{withoutSprint.item_count}</p>
                  <p className="text-sm text-muted-foreground">
                    itens aguardando alocação
                  </p>
                </div>
                {withoutSprint.total_estimate && (
                  <Badge variant="outline" className="text-base">
                    {withoutSprint.total_estimate} pts
                  </Badge>
                )}
              </div>
              {withoutSprint.status_breakdown.length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    Por Status:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {withoutSprint.status_breakdown.map((status, idx) => (
                      <Badge key={idx} variant="secondary">
                        {status.status || "Sem status"}: {status.count}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function SprintCard({
  sprint,
  isActive = false,
}: {
  sprint: IterationSummary;
  isActive?: boolean;
}) {
  const progress = calculateProgress(sprint.completed_count, sprint.item_count);
  const progressColor = getProgressColor(progress);

  function formatDate(dateString: string | null): string {
    if (!dateString) return "Sem data";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "short",
    }).format(date);
  }

  function calculateProgress(completed: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((completed / total) * 100);
  }

  function getProgressColor(progress: number): string {
    if (progress >= 80) return "text-green-600";
    if (progress >= 50) return "text-yellow-600";
    return "text-red-600";
  }

  return (
    <Card className={isActive ? "border-primary" : ""}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg">{sprint.name}</CardTitle>
          {isActive && (
            <Badge className="bg-green-600">Ativa</Badge>
          )}
        </div>
        {sprint.start_date && sprint.end_date && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <CalendarIcon className="h-3 w-3" />
            <span>
              {formatDate(sprint.start_date)} - {formatDate(sprint.end_date)}
            </span>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progresso */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progresso</span>
            <span className={`font-bold ${progressColor}`}>{progress}%</span>
          </div>
          <Progress value={progress} className="h-2" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {sprint.completed_count} de {sprint.item_count} itens
            </span>
            {sprint.total_estimate && sprint.completed_estimate !== null && (
              <span>
                {sprint.completed_estimate}/{sprint.total_estimate} pts
              </span>
            )}
          </div>
        </div>

        {/* Métricas */}
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{sprint.item_count}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Concluídos</p>
            <p className="flex items-center gap-1 text-2xl font-bold text-green-600">
              {sprint.completed_count}
              <CheckCircle2Icon className="h-5 w-5" />
            </p>
          </div>
        </div>

        {/* Velocity */}
        {sprint.total_estimate && sprint.total_estimate > 0 && (
          <div className="space-y-1 border-t pt-3">
            <p className="text-xs text-muted-foreground">Estimativa Total</p>
            <p className="text-xl font-bold">{sprint.total_estimate} pontos</p>
          </div>
        )}

        {/* Status Breakdown */}
        {sprint.status_breakdown.length > 0 && (
          <div className="space-y-2 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground">Por Status:</p>
            <div className="flex flex-wrap gap-1">
              {sprint.status_breakdown.map((status, idx) => (
                <Badge key={idx} variant="outline" className="text-xs">
                  {status.status || "Sem status"}: {status.count}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
