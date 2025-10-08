import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useProject } from "@/lib/project";
import { Loader2 } from "lucide-react";

export function ProjectSelection() {
  const navigate = useNavigate();
  const { status, projects, activeProject, setActiveProject } = useProject();

  // Se já tem projeto ativo, redireciona
  useEffect(() => {
    if (status === "ready" && activeProject) {
      navigate("/", { replace: true });
    }
  }, [status, activeProject, navigate]);

  const handleSelectProject = (projectId: number) => {
    setActiveProject(projectId);
    navigate("/", { replace: true });
  };

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Carregando projetos...</span>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Erro ao carregar projetos</CardTitle>
            <CardDescription>
              Não foi possível carregar os projetos disponíveis.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-red-500 mb-4">
              Configure um projeto em Configurações primeiro.
            </p>
            <Button onClick={() => navigate("/settings")} className="w-full">
              Ir para Configurações
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Nenhum projeto conectado</CardTitle>
            <CardDescription>
              Você precisa conectar pelo menos um projeto GitHub para começar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate("/settings")} className="w-full">
              Conectar Projeto
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Selecione um Projeto</CardTitle>
          <CardDescription>
            Escolha o projeto GitHub no qual deseja trabalhar
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => handleSelectProject(project.id)}
                className="flex items-start justify-between rounded-lg border border-border p-4 text-left transition hover:bg-accent hover:border-accent-foreground"
              >
                <div className="flex-1">
                  <p className="font-medium">
                    {project.name || `${project.owner_login}/${project.project_number}`}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {project.owner_login} · Projeto #{project.project_number}
                  </p>
                  {project.last_synced_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Último sync: {new Date(project.last_synced_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center">
                  <span className="text-sm text-muted-foreground">Selecionar →</span>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-6 flex justify-between items-center">
            <Button
              variant="outline"
              onClick={() => navigate("/settings")}
              size="sm"
            >
              Gerenciar Projetos
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
