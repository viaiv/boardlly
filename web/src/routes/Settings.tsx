import { useEffect, useState } from "react";
import type { FormEvent } from "react";
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
import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useProject } from "@/lib/project";
import { Trash2, Settings as SettingsIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

interface ProjectInfo {
  id: number;
  owner_login: string;
  project_number: number;
  name: string | null;
}

interface ProjectSummary {
  node_id: string;
  number: number;
  title?: string | null;
  updated_at?: string | null;
}

export function Settings() {
  const { user } = useSession();
  const { projects: allProjects, refresh: refreshProjects, activeProject } = useProject();
  const navigate = useNavigate();

  const [token, setToken] = useState("");
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [isEditingToken, setIsEditingToken] = useState(true);
  const [owner, setOwner] = useState("");
  const [projectNumber, setProjectNumber] = useState("");
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectNumber, setSelectedProjectNumber] = useState<string | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSavingToken, setIsSavingToken] = useState(false);
  const [isSavingProject, setIsSavingProject] = useState(false);

  const canManageSettings = user?.role === "owner" || user?.role === "admin";

  useEffect(() => {
    if (!canManageSettings) {
      return;
    }

    const checkToken = async () => {
      try {
        const status = await apiFetch<{ configured: boolean }>("/api/settings/github-token");
        setTokenConfigured(status.configured);
        setIsEditingToken(!status.configured);
      } catch {
        setTokenConfigured(false);
        setIsEditingToken(true);
      }
    };

    void checkToken();
  }, [canManageSettings]);

  const handleTokenSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!token.trim()) {
      setError("Informe um token válido");
      return;
    }
    setIsSavingToken(true);
    setError(null);
    try {
      await apiFetch("/api/settings/github-token", {
        method: "POST",
        body: JSON.stringify({ token: token.trim() }),
        parseJson: false,
      });
      setSyncResult("Token salvo com sucesso");
      setToken("********");
      setTokenConfigured(true);
      setIsEditingToken(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao salvar token";
      setError(message);
    } finally {
      setIsSavingToken(false);
    }
  };

  const handleProjectSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!owner.trim() || !projectNumber) {
      setError("Preencha owner e número do projeto");
      return;
    }
    setIsSavingProject(true);
    setError(null);
    setSyncResult(null);
    try {
      const ownerValue = owner.trim();
      const number = Number(projectNumber);
      await apiFetch<ProjectInfo>("/api/settings/github-project", {
        method: "POST",
        body: JSON.stringify({ owner: ownerValue, project_number: number }),
      });

      setSyncResult("Projeto conectado com sucesso!");
      await refreshProjects();

      // Limpar formulário
      setOwner("");
      setProjectNumber("");
      setProjects([]);
      setSelectedProjectNumber(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao conectar projeto";
      setError(message);
    } finally {
      setIsSavingProject(false);
    }
  };

  const handleDeleteProject = async (projectId: number, projectName: string) => {
    if (!confirm(`Tem certeza que deseja remover o projeto "${projectName}"? Todos os itens sincronizados serão removidos também.`)) {
      return;
    }

    try {
      await apiFetch(`/api/projects/${projectId}`, {
        method: "DELETE",
        parseJson: false,
      });

      toast.success("Projeto removido com sucesso");
      await refreshProjects();

      // Se o projeto removido era o ativo, recarregar página
      if (activeProject?.id === projectId) {
        window.location.reload();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao remover projeto";
      toast.error("Erro ao remover projeto", {
        description: message,
      });
    }
  };

  if (!canManageSettings) {
    return (
      <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
        Apenas administradores ou owners podem alterar configurações do GitHub.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Configurações</h1>
        <p className="text-sm text-muted-foreground">
          Configure o token do GitHub, selecione o Project v2 e acione a sincronização manual quando necessário.
        </p>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Token do GitHub</CardTitle>
          </CardHeader>
          <CardContent>
            {tokenConfigured && !isEditingToken ? (
              <div className="space-y-3 text-sm">
                <p className="text-muted-foreground">Token configurado. Atualize se necessário.</p>
                <Button variant="secondary" onClick={() => {
                  setIsEditingToken(true);
                  setToken("");
                }}>
                  Atualizar token
                </Button>
              </div>
            ) : (
              <form className="space-y-4" onSubmit={handleTokenSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="token">Token (PAT)</Label>
                  <Input
                    id="token"
                    type="password"
                    value={token}
                    onChange={(event) => setToken(event.target.value)}
                    placeholder="ghp_..."
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Utilize um PAT com escopos mínimos para leitura de Projects v2 e Issues.
                  </p>
                </div>
                <Button type="submit" disabled={isSavingToken} className="w-full">
                  {isSavingToken ? "Salvando..." : "Salvar token"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Conectar Project</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleProjectSubmit}>
              <div className="space-y-2">
                <Label htmlFor="owner">Owner</Label>
                <Input
                  id="owner"
                  value={owner}
                  onChange={(event) => setOwner(event.target.value)}
                  placeholder="viaiv"
                  required
                />
                <Button
                  type="button"
                  variant="secondary"
                  onClick={async () => {
                    if (!owner.trim()) {
                      setError("Informe um owner válido");
                      return;
                    }
                    setIsLoadingProjects(true);
                    setError(null);
                    setSyncResult(null);
                    try {
                      const data = await apiFetch<ProjectSummary[]>(
                        `/api/settings/github-projects?owner=${encodeURIComponent(owner.trim())}`,
                      );
                      setProjects(data);
                      setSelectedProjectNumber(null);
                    } catch (err) {
                      const message = err instanceof Error ? err.message : "Falha ao listar projetos";
                      setError(message);
                    } finally {
                      setIsLoadingProjects(false);
                    }
                  }}
                  disabled={isLoadingProjects}
                >
                  {isLoadingProjects ? "Buscando..." : "Listar Projects"}
                </Button>
              </div>
              <div className="space-y-2">
                <Label htmlFor="projectNumber">Número do Project</Label>
                {projects.length > 0 ? (
                  <Select
                    value={selectedProjectNumber ?? projectNumber}
                    onValueChange={(value) => {
                      setSelectedProjectNumber(value);
                      setProjectNumber(value);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione um Project" />
                    </SelectTrigger>
                    <SelectContent>
                      {projects.map((project) => (
                        <SelectItem key={project.node_id} value={String(project.number)}>
                          #{project.number} · {project.title ?? "Sem título"}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Input
                    id="projectNumber"
                    type="number"
                    value={projectNumber}
                    onChange={(event) => setProjectNumber(event.target.value)}
                    min={1}
                    required
                  />
                )}
              </div>
              <Button type="submit" disabled={isSavingProject} className="w-full">
                {isSavingProject ? "Validando..." : "Conectar"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}
      {syncResult ? <p className="text-sm text-emerald-600">{syncResult}</p> : null}

      {/* Project Management Section */}
      {allProjects.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Projetos Conectados</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Lista de todos os projetos GitHub conectados. Clique em "Gerenciar" para configurar etapas, épicos e campos do projeto.
              </p>
              <div className="space-y-2">
                {allProjects.map((project) => (
                  <div
                    key={project.id}
                    className="flex items-center justify-between rounded-lg border border-border p-3"
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {project.name || `${project.owner_login}/${project.project_number}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {project.owner_login} · Projeto #{project.project_number}
                        {activeProject?.id === project.id ? " · Ativo" : ""}
                      </p>
                      {project.last_synced_at ? (
                        <p className="text-xs text-muted-foreground">
                          Último sync: {new Date(project.last_synced_at).toLocaleString()}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/settings/projects/${project.id}`)}
                      >
                        <SettingsIcon className="mr-2 h-4 w-4" />
                        Gerenciar
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteProject(project.id, project.name || `${project.owner_login}/${project.project_number}`)}
                        className="text-destructive hover:text-destructive"
                        disabled={allProjects.length === 1}
                        title={allProjects.length === 1 ? "Você deve manter pelo menos um projeto" : "Remover projeto"}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              {allProjects.length === 1 ? (
                <p className="text-xs text-muted-foreground">
                  Você deve manter pelo menos um projeto conectado. Adicione outro projeto antes de remover este.
                </p>
              ) : null}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
