import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Modal } from "@/components/ui/modal";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProjectMembers } from "@/components/ProjectMembers";
import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useProject } from "@/lib/project";
import { CheckCircle2, Circle, AlertCircle, Loader2, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

interface ProjectInfo {
  id: number;
  owner_login: string;
  project_number: number;
  name: string | null;
  last_synced_at?: string | null;
  status_columns?: string[] | null;
}

interface EpicDetail {
  id: number;
  item_node_id: string;
  content_node_id: string | null;
  epic_option_id: string | null;
  epic_option_name: string | null;
  title: string;
  description: string | null;
  url: string | null;
  state: string | null;
  author: string | null;
  created_at: string | null;
  updated_at: string | null;
  labels: Array<{ name: string; color: string | null }>;
  total_issues: number;
  completed_issues: number;
  progress_percentage: number;
  total_estimate: number | null;
  completed_estimate: number | null;
  linked_issues: number[];
}

export function ProjectSettings() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { user } = useSession();
  const { projects, activeProject, setActiveProject } = useProject();

  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [isLoadingProject, setIsLoadingProject] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Roadmap Statuses
  const [statusInputs, setStatusInputs] = useState<string[]>([]);
  const [isSavingStatuses, setIsSavingStatuses] = useState(false);

  // Epics
  const [epicModalOpen, setEpicModalOpen] = useState(false);
  const [epicDetails, setEpicDetails] = useState<EpicDetail[]>([]);
  const [epicLoading, setEpicLoading] = useState(false);
  const [epicError, setEpicError] = useState<string | null>(null);
  const [epicSuccess, setEpicSuccess] = useState<string | null>(null);
  const [isCreatingEpic, setIsCreatingEpic] = useState(false);
  const [newEpicTitle, setNewEpicTitle] = useState("");
  const [newEpicDescription, setNewEpicDescription] = useState("");
  const [newEpicRepository, setNewEpicRepository] = useState("");
  const [newEpicCategory, setNewEpicCategory] = useState<string>("");
  const [epicOptions, setEpicOptions] = useState<Array<{ id: string; name: string }>>([]);

  // Setup
  const [setupStatus, setSetupStatus] = useState<Record<string, any> | null>(null);
  const [isLoadingSetup, setIsLoadingSetup] = useState(false);
  const [isRunningSetup, setIsRunningSetup] = useState(false);

  const canManageSettings = user?.role === "owner" || user?.role === "admin";

  // Encontrar projeto na lista
  const project = useMemo(
    () => projects.find((p) => p.id === parseInt(projectId || "", 10)),
    [projects, projectId]
  );

  useEffect(() => {
    if (!canManageSettings) {
      return;
    }

    if (!project) {
      navigate("/settings");
      return;
    }

    // Set active project if different
    if (activeProject?.id !== project.id) {
      setActiveProject(project.id);
    }

    const loadProject = async () => {
      setIsLoadingProject(true);
      try {
        const current = await apiFetch<ProjectInfo>("/api/projects/current");
        setProjectInfo(current);
      } catch (err) {
        const message = err instanceof Error ? err.message : null;
        setError(message);
        setProjectInfo(null);
      } finally {
        setIsLoadingProject(false);
      }
    };

    void loadProject();
  }, [canManageSettings, project, activeProject, setActiveProject, navigate]);

  useEffect(() => {
    if (!projectInfo) {
      setStatusInputs([]);
      return;
    }
    const configured = projectInfo.status_columns ?? [];
    const withoutDone = configured.filter((name) => name.toLowerCase() !== "done");
    setStatusInputs(withoutDone);
  }, [projectInfo]);

  useEffect(() => {
    if (!epicModalOpen) {
      setEpicDetails([]);
      setEpicOptions([]);
      setEpicError(null);
      setEpicSuccess(null);
      setNewEpicTitle("");
      setNewEpicDescription("");
      setNewEpicRepository("");
      setNewEpicCategory("");
      return;
    }

    const loadEpics = async () => {
      setEpicLoading(true);
      setEpicError(null);
      try {
        const [details, options] = await Promise.all([
          apiFetch<EpicDetail[]>("/api/projects/current/epics"),
          apiFetch<Array<{ id: string; name: string }>>("/api/projects/current/epics/options"),
        ]);
        setEpicDetails(details.slice().sort((a, b) => a.title.localeCompare(b.title)));
        setEpicOptions(options);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Falha ao carregar épicos";
        setEpicError(message);
      } finally {
        setEpicLoading(false);
      }
    };

    void loadEpics();
  }, [epicModalOpen]);

  const handleSync = async () => {
    if (!projectInfo) {
      setError("Conecte um projeto antes de sincronizar");
      return;
    }
    setIsSyncing(true);
    setError(null);
    setSyncResult(null);
    try {
      const result = await apiFetch<{ synced_items: number }>(`/api/github/sync/${projectInfo.id}`, {
        method: "POST",
      });
      setSyncResult(`Sincronização concluída: ${result.synced_items} itens atualizados.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao sincronizar";
      setError(message);
    } finally {
      setIsSyncing(false);
    }
  };

  const hasStatusChanges = useMemo(() => {
    const configured = projectInfo?.status_columns ?? [];
    const normalizedConfigured = configured
      .filter((name) => name.toLowerCase() !== "done")
      .map((name) => name.trim());
    const normalizedInputs = statusInputs.map((value) => value.trim()).filter(Boolean);
    if (normalizedConfigured.length !== normalizedInputs.length) {
      return true;
    }
    return normalizedConfigured.some((value, index) => value !== normalizedInputs[index]);
  }, [projectInfo?.status_columns, statusInputs]);

  const handleStatusChange = (index: number, value: string) => {
    setStatusInputs((previous) => {
      const next = [...previous];
      next[index] = value;
      return next;
    });
  };

  const handleStatusRemove = (index: number) => {
    setStatusInputs((previous) => previous.filter((_, currentIndex) => currentIndex !== index));
  };

  const handleAddStatus = () => {
    setStatusInputs((previous) => [...previous, ""]);
  };

  const handleOpenEpicManager = () => {
    if (!projectInfo) {
      setError("Conecte um projeto para visualizar épicos");
      return;
    }
    setEpicModalOpen(true);
  };

  const handleCreateEpic = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newEpicTitle.trim() || !newEpicRepository.trim()) {
      setEpicError("Título e repositório são obrigatórios");
      return;
    }

    setIsCreatingEpic(true);
    setEpicError(null);
    setEpicSuccess(null);

    try {
      const response = await apiFetch<{ issue_number: number; issue_url: string }>("/api/projects/current/epics", {
        method: "POST",
        body: JSON.stringify({
          title: newEpicTitle.trim(),
          description: newEpicDescription.trim() || null,
          repository: newEpicRepository.trim(),
          epic_option_id: newEpicCategory || null,
        }),
      });

      setEpicSuccess(`Épico criado com sucesso! Issue #${response.issue_number}`);
      setNewEpicTitle("");
      setNewEpicDescription("");
      setNewEpicRepository("");
      setNewEpicCategory("");

      const details = await apiFetch<EpicDetail[]>("/api/projects/current/epics");
      setEpicDetails(details.slice().sort((a, b) => a.title.localeCompare(b.title)));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao criar épico";
      setEpicError(message);
    } finally {
      setIsCreatingEpic(false);
    }
  };

  const handleSaveStatuses = async () => {
    if (!projectInfo) {
      setError("Conecte um projeto antes de configurar as etapas");
      return;
    }
    setIsSavingStatuses(true);
    setError(null);
    setSyncResult(null);
    try {
      const payload = statusInputs.map((value) => value.trim()).filter(Boolean);
      const columns = await apiFetch<string[]>("/api/projects/current/statuses", {
        method: "POST",
        body: JSON.stringify({ columns: payload }),
      });
      setProjectInfo((previous) => (previous ? { ...previous, status_columns: columns } : previous));
      setSyncResult("Etapas atualizadas com sucesso.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao salvar etapas";
      setError(message);
    } finally {
      setIsSavingStatuses(false);
    }
  };

  const loadSetupStatus = async () => {
    if (!projectInfo) return;

    try {
      setIsLoadingSetup(true);
      const status = await apiFetch<Record<string, any>>("/api/projects/current/setup/status");
      setSetupStatus(status);
    } catch (err) {
      console.error("Erro ao carregar status do setup:", err);
    } finally {
      setIsLoadingSetup(false);
    }
  };

  const runSetup = async () => {
    try {
      setIsRunningSetup(true);

      const report = await apiFetch<Record<string, any>>("/api/projects/current/setup", {
        method: "POST",
      });

      const createdFields = Object.entries(report)
        .filter(([_, value]: [string, any]) => value.created)
        .map(([key]) => key);

      if (createdFields.length > 0) {
        toast.success(`Campos criados: ${createdFields.join(", ")}`);
      } else {
        toast.info("Todos os campos já estavam configurados");
      }

      await loadSetupStatus();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro ao executar setup";
      toast.error("Erro ao executar setup", {
        description: errorMessage,
      });
    } finally {
      setIsRunningSetup(false);
    }
  };

  useEffect(() => {
    if (projectInfo) {
      void loadSetupStatus();
    }
  }, [projectInfo]);

  if (!canManageSettings) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Apenas administradores ou owners podem alterar configurações do GitHub.
      </div>
    );
  }

  if (!project) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Projeto não encontrado
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate("/settings")}
          className="mb-2"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Voltar para Configurações
        </Button>
        <h1 className="text-2xl font-semibold tracking-tight">
          {project.name || `${project.owner_login}/${project.project_number}`}
        </h1>
        <p className="text-sm text-muted-foreground">
          Configure etapas do roadmap, épicos e campos do projeto.
        </p>
      </header>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}
      {syncResult ? <p className="text-sm text-emerald-600">{syncResult}</p> : null}

      {isLoadingProject ? (
        <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          Carregando dados do projeto...
        </div>
      ) : projectInfo ? (
        <Tabs defaultValue="sync" className="w-full">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="sync">Sincronização</TabsTrigger>
            <TabsTrigger value="roadmap">Etapas do Roadmap</TabsTrigger>
            <TabsTrigger value="epics">Épicos</TabsTrigger>
            <TabsTrigger value="members">Membros</TabsTrigger>
            <TabsTrigger value="setup">Setup</TabsTrigger>
          </TabsList>

          <TabsContent value="sync" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Sincronização manual</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {projectInfo.last_synced_at ? (
                  <p className="text-sm text-muted-foreground">
                    Último sync: {new Date(projectInfo.last_synced_at).toLocaleString()}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground">Nunca sincronizado</p>
                )}
                <Button onClick={handleSync} disabled={isSyncing}>
                  {isSyncing ? "Sincronizando..." : "Sincronizar agora"}
                </Button>
                <p className="text-xs text-muted-foreground">
                  A sincronização busca todas as issues e pull requests do projeto GitHub e atualiza os dados locais.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="roadmap" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Etapas do Roadmap</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {statusInputs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    Adicione etapas personalizadas para organizar o roadmap. A coluna Done é mantida automaticamente.
                  </p>
                ) : (
                  statusInputs.map((value, index) => (
                    <div key={`status-${index}`} className="space-y-2">
                      <Label htmlFor={`status-${index}`}>Etapa {index + 1}</Label>
                      <div className="flex items-center gap-2">
                        <Input
                          id={`status-${index}`}
                          value={value}
                          placeholder="Em andamento"
                          onChange={(event) => handleStatusChange(index, event.target.value)}
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          className="text-xs"
                          onClick={() => handleStatusRemove(index)}
                        >
                          Remover
                        </Button>
                      </div>
                    </div>
                  ))
                )}
                <div className="flex flex-wrap items-center gap-3">
                  <Button type="button" variant="outline" onClick={handleAddStatus}>
                    Adicionar etapa
                  </Button>
                  <Button
                    type="button"
                    onClick={handleSaveStatuses}
                    disabled={isSavingStatuses || !hasStatusChanges}
                  >
                    {isSavingStatuses ? "Salvando..." : "Salvar etapas"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  A ordem das etapas define como os cartões serão exibidos no roadmap. "Done" é adicionada automaticamente ao final.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="epics" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Épicos do Projeto</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Crie novos épicos ou visualize os existentes com descrição, progresso e métricas.
                </p>
                <Button onClick={handleOpenEpicManager}>
                  Gerenciar épicos
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="members" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Membros do Projeto</CardTitle>
              </CardHeader>
              <CardContent>
                <ProjectMembers projectId={projectInfo.id} />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="setup" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Setup do Projeto</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  Verifique e configure automaticamente os campos necessários no GitHub Project.
                </p>

                {isLoadingSetup ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Verificando configuração...</span>
                  </div>
                ) : setupStatus ? (
                  <div className="space-y-3">
                    {Object.entries(setupStatus).map(([key, value]: [string, any]) => (
                      <div key={key} className="flex items-start gap-3 p-3 rounded-lg border">
                        <div className="flex-shrink-0 mt-0.5">
                          {value.exists ? (
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                          ) : value.required ? (
                            <AlertCircle className="h-5 w-5 text-yellow-600" />
                          ) : (
                            <Circle className="h-5 w-5 text-muted-foreground" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium capitalize">{key}</p>
                            {value.required && (
                              <span className="text-xs px-2 py-0.5 bg-yellow-100 text-yellow-800 rounded">
                                Obrigatório
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {value.description}
                          </p>
                          <p className="text-xs mt-1">
                            {value.exists ? (
                              <span className="text-green-600">✓ Configurado</span>
                            ) : (
                              <span className="text-muted-foreground">Não configurado</span>
                            )}
                          </p>
                        </div>
                      </div>
                    ))}

                    <div className="pt-2">
                      <Button
                        onClick={runSetup}
                        disabled={isRunningSetup || (setupStatus && Object.values(setupStatus).every((v: any) => v.exists))}
                      >
                        {isRunningSetup ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Configurando...
                          </>
                        ) : (
                          "Configurar campos automaticamente"
                        )}
                      </Button>
                      <p className="text-xs text-muted-foreground mt-2">
                        Este processo criará automaticamente os campos faltantes no seu GitHub Project.
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Configure um projeto primeiro para verificar o status dos campos.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      ) : null}

      {/* Epic Management Modal */}
      <Modal
        open={epicModalOpen}
        onClose={() => setEpicModalOpen(false)}
        title="Gerenciar Épicos"
        description="Crie novos épicos (issues) ou visualize os existentes com descrição completa, progresso e métricas."
        size="lg"
        footer={
          <Button variant="outline" onClick={() => setEpicModalOpen(false)}>
            Fechar
          </Button>
        }
      >
        <div className="space-y-4">
          {epicError ? (
            <p className="rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-600">{epicError}</p>
          ) : null}
          {epicSuccess ? (
            <p className="rounded-md border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-700">
              {epicSuccess}
            </p>
          ) : null}

          {/* Create Epic Form */}
          <form className="rounded-lg border border-border p-4 space-y-3" onSubmit={handleCreateEpic}>
            <h3 className="text-sm font-semibold">Criar novo épico</h3>

            <div className="space-y-2">
              <Label htmlFor="epic-title">Título*</Label>
              <Input
                id="epic-title"
                value={newEpicTitle}
                onChange={(e) => setNewEpicTitle(e.target.value)}
                placeholder="Sistema de Autenticação"
                disabled={isCreatingEpic}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="epic-description">Descrição</Label>
              <textarea
                id="epic-description"
                value={newEpicDescription}
                onChange={(e) => setNewEpicDescription(e.target.value)}
                placeholder="Implementar sistema completo de autenticação com JWT..."
                disabled={isCreatingEpic}
                className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="epic-repository">Repositório*</Label>
              <Input
                id="epic-repository"
                value={newEpicRepository}
                onChange={(e) => setNewEpicRepository(e.target.value)}
                placeholder="nome-do-repo"
                disabled={isCreatingEpic}
                required
              />
              <p className="text-xs text-muted-foreground">
                Nome do repositório onde a issue será criada (em {projectInfo?.owner_login})
              </p>
            </div>

            {epicOptions.length > 0 ? (
              <div className="space-y-2">
                <Label htmlFor="epic-category">Categoria (opcional)</Label>
                <Select
                  value={newEpicCategory}
                  onValueChange={setNewEpicCategory}
                  disabled={isCreatingEpic}
                >
                  <SelectTrigger id="epic-category">
                    <SelectValue placeholder="Nenhuma categoria" />
                  </SelectTrigger>
                  <SelectContent>
                    {epicOptions.map((option) => (
                      <SelectItem key={option.id} value={option.id}>
                        {option.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {newEpicCategory ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setNewEpicCategory("")}
                    disabled={isCreatingEpic}
                    className="text-xs"
                  >
                    Remover categoria
                  </Button>
                ) : null}
              </div>
            ) : null}

            <Button type="submit" disabled={isCreatingEpic} className="w-full">
              {isCreatingEpic ? "Criando..." : "Criar épico"}
            </Button>
          </form>

          {/* Epic List */}
          {epicLoading ? (
            <p className="text-sm text-muted-foreground">Carregando épicos...</p>
          ) : epicDetails.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border p-8 text-center">
              <p className="text-sm text-muted-foreground">
                Nenhum épico encontrado ainda.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {epicDetails.map((epic) => (
                <div
                  key={epic.id}
                  className="rounded-lg border border-border bg-card p-4 space-y-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-sm font-semibold text-foreground">{epic.title}</h4>
                      {epic.url ? (
                        <a
                          href={epic.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:underline"
                        >
                          Ver no GitHub →
                        </a>
                      ) : null}
                    </div>
                    {epic.description ? (
                      <p className="text-xs text-muted-foreground line-clamp-2">{epic.description}</p>
                    ) : null}
                    {epic.epic_option_name ? (
                      <p className="text-xs text-muted-foreground">
                        Categoria: <span className="font-medium">{epic.epic_option_name}</span>
                      </p>
                    ) : null}
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">Progresso</span>
                      <span className="font-medium">{epic.progress_percentage.toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all"
                        style={{ width: `${epic.progress_percentage}%` }}
                      />
                    </div>
                  </div>

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="space-y-0.5">
                      <p className="text-muted-foreground">Issues</p>
                      <p className="font-medium">
                        {epic.completed_issues} / {epic.total_issues} concluídas
                      </p>
                    </div>
                    {epic.total_estimate !== null ? (
                      <div className="space-y-0.5">
                        <p className="text-muted-foreground">Estimativa</p>
                        <p className="font-medium">
                          {epic.completed_estimate?.toFixed(1) ?? 0} / {epic.total_estimate.toFixed(1)}
                        </p>
                      </div>
                    ) : null}
                  </div>

                  {/* Labels */}
                  {epic.labels.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {epic.labels.map((label, idx) => (
                        <span
                          key={`${epic.id}-label-${idx}`}
                          className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-white"
                          style={{
                            backgroundColor: label.color ? `#${label.color}` : "#6b7280",
                          }}
                        >
                          {label.name}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
