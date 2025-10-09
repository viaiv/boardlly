/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import { apiFetch } from "./api";
import { useSession } from "./session";

const ACTIVE_PROJECT_KEY = "tactyo:active-project-id";

export interface Project {
  id: number;
  owner_login: string;
  project_number: number;
  project_node_id: string;
  name: string | null;
  field_mappings: Record<string, unknown> | null;
  last_synced_at: string | null;
  status_columns: string[] | null;
}

export interface ProjectState {
  status: "loading" | "ready" | "error";
  projects: Project[];
  activeProject: Project | null;
  error?: string;
  setActiveProject: (projectId: number) => void;
  refresh: () => Promise<void>;
}

const ProjectContext = createContext<ProjectState | undefined>(undefined);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { status: sessionStatus } = useSession();
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(() => {
    const stored = localStorage.getItem(ACTIVE_PROJECT_KEY);
    return stored ? parseInt(stored, 10) : null;
  });
  const [error, setError] = useState<string | undefined>();

  const loadProjects = useCallback(async () => {
    setStatus("loading");
    setError(undefined);
    try {
      const data = await apiFetch<Project[]>("/api/projects");
      console.log("🔍 [ProjectProvider] Projetos carregados:", {
        count: data.length,
        projects: data,
        activeProjectId,
        hasActiveInList: activeProjectId ? data.some((p) => p.id === activeProjectId) : null,
      });
      setProjects(data);

      // Se o projeto ativo não existe mais na lista, remove a seleção
      if (activeProjectId && !data.some((p) => p.id === activeProjectId)) {
        console.warn("⚠️ [ProjectProvider] Projeto ativo não encontrado na lista. Limpando localStorage.");
        setActiveProjectId(null);
        localStorage.removeItem(ACTIVE_PROJECT_KEY);
      }

      setStatus("ready");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao carregar projetos";
      console.error("❌ [ProjectProvider] Erro ao carregar projetos:", err);
      setError(message);
      setStatus("error");
    }
  }, [activeProjectId]);

  const setActiveProject = useCallback((projectId: number) => {
    setActiveProjectId(projectId);
    localStorage.setItem(ACTIVE_PROJECT_KEY, String(projectId));
  }, []);

  // Só carregar projetos quando estiver autenticado
  useEffect(() => {
    if (sessionStatus === "authenticated") {
      console.log("✅ [ProjectProvider] Usuário autenticado, carregando projetos...");
      void loadProjects();
    } else if (sessionStatus === "unauthenticated") {
      console.log("🚪 [ProjectProvider] Usuário não autenticado, limpando projetos...");
      // Limpar projetos ao fazer logout
      setProjects([]);
      setActiveProjectId(null);
      setStatus("ready");
    }
  }, [sessionStatus, loadProjects]);

  const activeProject = useMemo(
    () => projects.find((p) => p.id === activeProjectId) ?? null,
    [projects, activeProjectId]
  );

  const value = useMemo<ProjectState>(
    () => ({
      status,
      projects,
      activeProject,
      error,
      setActiveProject,
      refresh: loadProjects,
    }),
    [status, projects, activeProject, error, setActiveProject, loadProjects]
  );

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>;
}

export function useProject() {
  const context = useContext(ProjectContext);
  if (!context) {
    throw new Error("useProject precisa ser usado dentro de ProjectProvider");
  }
  return context;
}
