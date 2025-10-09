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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2, RefreshCw, ExternalLink, Plus, Pencil, Trash2 } from "lucide-react";
import {
  listEpics,
  createEpic,
  updateEpic,
  deleteEpic,
  GITHUB_COLORS,
  getColorHex,
  getColorName,
  type EpicOption,
  type EpicOptionCreate,
} from "@/lib/epics";

export function Epics() {
  const { activeProject } = useProject();
  const [epics, setEpics] = useState<EpicOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedEpic, setSelectedEpic] = useState<EpicOption | null>(null);
  const [formData, setFormData] = useState<EpicOptionCreate>({
    name: "",
    color: "BLUE",
    description: ""
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadEpics();
  }, [activeProject?.id]);

  async function loadEpics() {
    try {
      setLoading(true);
      const data = await listEpics();
      setEpics(data);
    } catch (error) {
      toast.error("Erro ao carregar épicos", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    if (!formData.name.trim()) {
      toast.error("Nome do épico é obrigatório");
      return;
    }

    try {
      setSubmitting(true);
      await createEpic(formData);
      toast.success("Épico criado com sucesso!");
      setCreateDialogOpen(false);
      setFormData({ name: "", color: "BLUE", description: "" });
      await loadEpics();
    } catch (error) {
      toast.error("Erro ao criar épico", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUpdate() {
    if (!selectedEpic || !formData.name.trim()) {
      toast.error("Nome do épico é obrigatório");
      return;
    }

    try {
      setSubmitting(true);
      await updateEpic(selectedEpic.id, formData);
      toast.success("Épico atualizado com sucesso!");
      setEditDialogOpen(false);
      setSelectedEpic(null);
      setFormData({ name: "", color: "BLUE", description: "" });
      await loadEpics();
    } catch (error) {
      toast.error("Erro ao atualizar épico", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!selectedEpic) return;

    try {
      setSubmitting(true);
      await deleteEpic(selectedEpic.id);
      toast.success("Épico deletado com sucesso!");
      setDeleteDialogOpen(false);
      setSelectedEpic(null);
      await loadEpics();
    } catch (error) {
      toast.error("Erro ao deletar épico", {
        description: error instanceof Error ? error.message : "Erro desconhecido",
      });
    } finally {
      setSubmitting(false);
    }
  }

  function openEditDialog(epic: EpicOption) {
    setSelectedEpic(epic);
    // Converte hex de volta para nome da cor (ex: #0052cc -> BLUE)
    const formColor = getColorName(epic.color);
    setFormData({
      name: epic.name,
      color: formColor,
      description: epic.description || ""
    });
    setEditDialogOpen(true);
  }

  function openDeleteDialog(epic: EpicOption) {
    setSelectedEpic(epic);
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
          <h1 className="text-3xl font-bold tracking-tight">Épicos</h1>
          <p className="text-muted-foreground">
            Gerencie as opções do campo Epic do projeto
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={loadEpics} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Atualizar
          </Button>
          <Dialog
            open={createDialogOpen}
            onOpenChange={(open) => {
              setCreateDialogOpen(open);
              if (!open) {
                setFormData({ name: "", color: "BLUE", description: "" });
              }
            }}
          >
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Novo Épico
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Criar Novo Épico</DialogTitle>
                <DialogDescription>
                  Adicione uma nova opção ao campo Epic do projeto
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Nome do Épico *</Label>
                  <Input
                    id="name"
                    placeholder="Ex: Feature, Bug Fix, Tech Debt..."
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Descrição</Label>
                  <Textarea
                    id="description"
                    placeholder="Descreva o propósito deste épico..."
                    value={formData.description || ""}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="color">Cor</Label>
                  <Select
                    value={formData.color || "BLUE"}
                    onValueChange={(value) => setFormData({ ...formData, color: value })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Selecione uma cor" />
                    </SelectTrigger>
                    <SelectContent>
                      {GITHUB_COLORS.map((color) => (
                        <SelectItem key={color.value} value={color.value}>
                          <div className="flex items-center gap-2">
                            <div
                              className="w-4 h-4 rounded-full border border-gray-200"
                              style={{ backgroundColor: color.hex }}
                            />
                            <span>{color.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleCreate} disabled={submitting}>
                  {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Criar Épico
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Edit Epic Dialog */}
      <Dialog
        open={editDialogOpen}
        onOpenChange={(open) => {
          setEditDialogOpen(open);
          if (!open) {
            setSelectedEpic(null);
            setFormData({ name: "", color: "BLUE", description: "" });
          }
        }}
      >
        <DialogContent key={selectedEpic?.id}>
          <DialogHeader>
            <DialogTitle>Editar Épico</DialogTitle>
            <DialogDescription>
              Atualize os detalhes do épico. As mudanças serão sincronizadas em todos os repositórios.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Nome do Épico *</Label>
              <Input
                id="edit-name"
                placeholder="Ex: Feature, Bug Fix, Tech Debt..."
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Descrição</Label>
              <Textarea
                id="edit-description"
                placeholder="Descreva o propósito deste épico..."
                value={formData.description || ""}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-color">Cor</Label>
              <Select
                key={`edit-color-${selectedEpic?.id}`}
                value={formData.color || "BLUE"}
                onValueChange={(value) => setFormData({ ...formData, color: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecione uma cor" />
                </SelectTrigger>
                <SelectContent>
                  {GITHUB_COLORS.map((color) => (
                    <SelectItem key={color.value} value={color.value}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-4 h-4 rounded-full border border-gray-200"
                          style={{ backgroundColor: color.hex }}
                        />
                        <span>{color.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleUpdate} disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Salvar Alterações
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card className="border-blue-200 bg-blue-50/50">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <ExternalLink className="h-5 w-5 text-blue-600 mt-0.5" />
            <div className="space-y-1">
              <p className="text-sm font-medium text-blue-900">
                Épicos como Labels do GitHub
              </p>
              <p className="text-sm text-blue-700">
                Épicos são gerenciados como labels do GitHub com prefixo "epic:".
                Quando você cria/edita/deleta um épico, a label é sincronizada em todos
                os repositórios vinculados ao projeto. Adicione repositórios em Configurações → Repositórios.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {epics.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground text-center mb-4">
              Nenhum épico encontrado no projeto.
              <br />
              Clique em "Novo Épico" para começar.
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Criar Primeiro Épico
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {epics.map((epic) => (
            <Card key={epic.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full border border-gray-200"
                      style={{ backgroundColor: getColorHex(epic.color) }}
                    />
                    <CardTitle className="text-lg">{epic.name}</CardTitle>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditDialog(epic)}
                      title="Editar épico"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openDeleteDialog(epic)}
                      title="Deletar épico"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              {epic.description && (
                <CardContent className="pt-0">
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {epic.description}
                  </p>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar Exclusão</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja deletar o épico "{selectedEpic?.name}"?
              Esta ação não pode ser desfeita e o épico será removido de todas as issues associadas.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Deletar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
