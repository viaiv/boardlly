import { FormEvent, useEffect, useMemo, useState } from "react";

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

interface ProjectInfo {
  id: number;
  owner_login: string;
  project_number: number;
  name: string | null;
  last_synced_at?: string | null;
  status_columns?: string[] | null;
}

interface ProjectSummary {
  node_id: string;
  number: number;
  title?: string | null;
  updated_at?: string | null;
}

export function Settings() {
  const { user } = useSession();
  const [token, setToken] = useState("");
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [isEditingToken, setIsEditingToken] = useState(true);
  const [owner, setOwner] = useState("");
  const [projectNumber, setProjectNumber] = useState("");
  const [projectInfo, setProjectInfo] = useState<ProjectInfo | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectNumber, setSelectedProjectNumber] = useState<string | null>(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSavingToken, setIsSavingToken] = useState(false);
  const [isSavingProject, setIsSavingProject] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [statusInputs, setStatusInputs] = useState<string[]>([]);
  const [isSavingStatuses, setIsSavingStatuses] = useState(false);
  const [isLoadingProject, setIsLoadingProject] = useState(false);

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

    const loadProject = async () => {
      setIsLoadingProject(true);
      try {
        const current = await apiFetch<ProjectInfo>("/api/projects/current");
        setProjectInfo(current);
      } catch (err) {
        const message = err instanceof Error ? err.message : null;
        const normalized = message?.toLowerCase() ?? "";
        if (message && !normalized.includes("não configurado")) {
          setError(message);
        }
        setProjectInfo(null);
      } finally {
        setIsLoadingProject(false);
      }
    };

    void checkToken();
    void loadProject();
  }, [canManageSettings]);

  useEffect(() => {
    if (!projectInfo) {
      setStatusInputs([]);
      return;
    }
    setOwner(projectInfo.owner_login);
    setProjectNumber(String(projectInfo.project_number));
    const configured = projectInfo.status_columns ?? [];
    const withoutDone = configured.filter((name) => name.toLowerCase() !== "done");
    setStatusInputs(withoutDone);
  }, [projectInfo]);

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
      const data = await apiFetch<ProjectInfo>("/api/settings/github-project", {
        method: "POST",
        body: JSON.stringify({ owner: ownerValue, project_number: number }),
      });
      setProjectInfo(data);
      setSelectedProjectNumber(String(number));
      setProjectNumber(String(number));
      const withoutDone = (data.status_columns ?? []).filter((name) => name.toLowerCase() !== "done");
      setStatusInputs(withoutDone);
      setSyncResult("Projeto conectado. Faça o sync para trazer dados.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao conectar projeto";
      setError(message);
    } finally {
      setIsSavingProject(false);
    }
  };

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

      {isLoadingProject ? (
        <div className="rounded-lg border border-dashed border-border p-6 text-sm text-muted-foreground">
          Carregando dados do projeto conectado...
        </div>
      ) : null}

      {projectInfo ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Projeto conectado</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <p className="text-sm font-medium">{projectInfo.name ?? "Projeto sem título"}</p>
                <p className="text-xs text-muted-foreground">
                  {projectInfo.owner_login} · #{projectInfo.project_number}
                </p>
                {projectInfo.last_synced_at ? (
                  <p className="text-xs text-muted-foreground">
                    Último sync: {new Date(projectInfo.last_synced_at).toLocaleString()}
                  </p>
                ) : null}
              </div>
              <Button onClick={handleSync} disabled={isSyncing}>
                {isSyncing ? "Sincronizando..." : "Sincronizar agora"}
              </Button>
            </CardContent>
          </Card>

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
        </div>
      ) : null}
    </div>
  );
}
