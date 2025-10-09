import { useState, useEffect } from "react";
import { useProject } from "@/lib/project";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { Loader2, RefreshCw, Plus, Trash2, Star } from "lucide-react";
import {
  listRepositories,
  createRepository,
  updateRepository,
  deleteRepository,
  type ProjectRepository,
  type ProjectRepositoryCreate,
} from "@/lib/repositories";

export function ProjectRepositories() {
  const { activeProject } = useProject();
  const [repositories, setRepositories] = useState<ProjectRepository[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<ProjectRepository | null>(null);
  const [formData, setFormData] = useState<ProjectRepositoryCreate>({
    owner: "",
    repo_name: "",
    is_primary: false,
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadRepositories();
  }, [activeProject?.id]);

  async function loadRepositories() {
    try {
      setLoading(true);
      const data = await listRepositories();
      setRepositories(data);
    } catch (error) {
      toast.error("Erro ao carregar repositórios", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formData.owner.trim() || !formData.repo_name.trim()) {
      toast.error("Owner e nome do repositório são obrigatórios");
      return;
    }

    try {
      setSubmitting(true);
      await createRepository(formData);
      toast.success("Repositório adicionado com sucesso!");
      setCreateDialogOpen(false);
      setFormData({ owner: "", repo_name: "", is_primary: false });
      await loadRepositories();
    } catch (error) {
      toast.error("Erro ao adicionar repositório", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!selectedRepo) return;

    try {
      setSubmitting(true);
      await deleteRepository(selectedRepo.id);
      toast.success("Repositório removido com sucesso!");
      setDeleteDialogOpen(false);
      setSelectedRepo(null);
      await loadRepositories();
    } catch (error) {
      toast.error("Erro ao remover repositório", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function togglePrimary(repo: ProjectRepository) {
    try {
      await updateRepository(repo.id, { is_primary: !repo.is_primary });
      toast.success(repo.is_primary ? "Repositório desmarcado como principal" : "Repositório marcado como principal");
      await loadRepositories();
    } catch (error) {
      toast.error("Erro ao atualizar repositório", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    }
  }

  function openDeleteDialog(repo: ProjectRepository) {
    setSelectedRepo(repo);
    setDeleteDialogOpen(true);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Repositórios</h1>
          <p className="text-muted-foreground">
            Gerencie os repositórios vinculados ao projeto
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadRepositories} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Atualizar
          </Button>
          <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Adicionar Repositório
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Adicionar Repositório</DialogTitle>
                <DialogDescription>
                  Vincule um repositório do GitHub ao projeto
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="owner">Owner (organização ou usuário) *</Label>
                  <Input
                    id="owner"
                    placeholder="Ex: tactyo"
                    value={formData.owner}
                    onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="repo_name">Nome do Repositório *</Label>
                  <Input
                    id="repo_name"
                    placeholder="Ex: api"
                    value={formData.repo_name}
                    onChange={(e) => setFormData({ ...formData, repo_name: e.target.value })}
                  />
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="is_primary"
                    checked={formData.is_primary}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, is_primary: checked as boolean })
                    }
                  />
                  <Label htmlFor="is_primary" className="font-normal">
                    Marcar como repositório principal
                  </Label>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleCreate} disabled={submitting}>
                  {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Adicionar
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-900">
                Repositórios e Labels
              </p>
              <p className="text-sm text-blue-700">
                Épicos são gerenciados como labels do GitHub com prefixo "epic:".
                Quando você cria um épico, a label é criada em todos os repositórios vinculados.
                Adicione pelo menos um repositório para poder gerenciar épicos.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {repositories.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground text-center mb-4">
              Nenhum repositório vinculado ao projeto.
              <br />
              Adicione pelo menos um repositório para gerenciar épicos.
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Adicionar Primeiro Repositório
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {repositories.map((repo) => (
            <Card key={repo.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      {repo.is_primary && <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />}
                      {repo.owner}/{repo.repo_name}
                    </CardTitle>
                    {repo.is_primary && (
                      <p className="text-xs text-muted-foreground mt-1">
                        Repositório principal
                      </p>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => togglePrimary(repo)}
                      title={repo.is_primary ? "Desmarcar como principal" : "Marcar como principal"}
                    >
                      <Star className={`h-4 w-4 ${repo.is_primary ? "fill-yellow-400 text-yellow-400" : ""}`} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openDeleteDialog(repo)}
                      title="Remover repositório"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar Remoção</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja remover o repositório "{selectedRepo?.owner}/{selectedRepo?.repo_name}"?
              As labels (épicos) não serão removidas do repositório, apenas a vinculação ao projeto.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
