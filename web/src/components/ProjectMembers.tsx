import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { useSession } from "@/lib/session";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

interface ProjectMember {
  id: number;
  user_id: string;
  project_id: number;
  role: string;
  user_email: string;
  user_name: string | null;
  created_at: string;
  updated_at: string;
}

interface ProjectInvite {
  id: number;
  project_id: number;
  invited_email: string;
  invited_by_email: string;
  invited_by_name: string | null;
  role: string;
  status: string;
  created_at: string;
}

const ROLE_LABELS: Record<string, string> = {
  viewer: "Visualizador",
  editor: "Editor",
  pm: "Gerente de Projeto",
  admin: "Administrador",
};

const ROLE_DESCRIPTIONS: Record<string, string> = {
  viewer: "Apenas visualização",
  editor: "Pode editar itens",
  pm: "Pode gerenciar sprints e épicos",
  admin: "Administrador do projeto",
};

interface ProjectMembersProps {
  projectId: number;
}

export function ProjectMembers({ projectId }: ProjectMembersProps) {
  const { user } = useSession();
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [invites, setInvites] = useState<ProjectInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState<string>("");
  const [selectedRole, setSelectedRole] = useState<string>("viewer");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canManageTeam = user?.role === "admin" || user?.role === "owner";

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch project members
        const membersData = await apiFetch<ProjectMember[]>(
          `/api/projects/${projectId}/members`
        );
        setMembers(membersData);

        // Fetch pending invites if user can manage team
        if (canManageTeam) {
          const invitesData = await apiFetch<ProjectInvite[]>(
            `/api/projects/${projectId}/invites`
          );
          setInvites(invitesData);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Não foi possível carregar o time";
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    void fetchData();
  }, [projectId, canManageTeam]);

  const handleAddMember = async () => {
    if (!inviteEmail.trim()) return;

    setIsSubmitting(true);
    try {
      await apiFetch(
        `/api/projects/${projectId}/invites`,
        {
          method: "POST",
          body: JSON.stringify({
            email: inviteEmail.trim(),
            role: selectedRole,
          }),
        }
      );

      // Refresh invites list
      const invitesData = await apiFetch<ProjectInvite[]>(
        `/api/projects/${projectId}/invites`
      );
      setInvites(invitesData);

      setIsAddDialogOpen(false);
      setInviteEmail("");
      setSelectedRole("viewer");
      toast.success("Convite enviado com sucesso");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao enviar convite";
      toast.error("Erro ao enviar convite", {
        description: message,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateRole = async (userId: string, newRole: string) => {
    try {
      const updatedMember = await apiFetch<ProjectMember>(
        `/api/projects/${projectId}/members/${userId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ role: newRole }),
        }
      );

      setMembers(
        members.map((m) => (m.user_id === userId ? updatedMember : m))
      );
      toast.success("Permissão atualizada");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao atualizar permissão";
      toast.error("Erro ao atualizar permissão", {
        description: message,
      });
    }
  };

  const handleRemoveMember = async (userId: string, userName: string) => {
    if (!confirm(`Tem certeza que deseja remover ${userName} do projeto?`)) {
      return;
    }

    try {
      await apiFetch(`/api/projects/${projectId}/members/${userId}`, {
        method: "DELETE",
        parseJson: false,
      });

      setMembers(members.filter((m) => m.user_id !== userId));
      toast.success("Membro removido com sucesso");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao remover membro";
      toast.error("Erro ao remover membro", {
        description: message,
      });
    }
  };

  const handleCancelInvite = async (inviteId: number) => {
    if (!confirm("Tem certeza que deseja cancelar este convite?")) {
      return;
    }

    try {
      await apiFetch(`/api/projects/${projectId}/invites/${inviteId}`, {
        method: "DELETE",
        parseJson: false,
      });

      // Refresh invites list
      const invitesData = await apiFetch<ProjectInvite[]>(
        `/api/projects/${projectId}/invites`
      );
      setInvites(invitesData);
      toast.success("Convite cancelado");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao cancelar convite";
      toast.error("Erro ao cancelar convite", {
        description: message,
      });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">
            Gerencie quem tem acesso ao projeto e suas permissões.
          </p>
        </div>
        {canManageTeam && (
          <Button onClick={() => setIsAddDialogOpen(true)} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Enviar Convite
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-border bg-card">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50 text-sm uppercase text-muted-foreground">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Nome</th>
              <th className="px-4 py-3 text-left font-medium">Email</th>
              <th className="px-4 py-3 text-left font-medium">Permissão</th>
              {canManageTeam && <th className="px-4 py-3 text-left font-medium">Ações</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-border text-sm">
            {loading ? (
              <tr>
                <td className="px-4 py-6 text-center" colSpan={canManageTeam ? 4 : 3}>
                  Carregando...
                </td>
              </tr>
            ) : error ? (
              <tr>
                <td className="px-4 py-6 text-center text-red-500" colSpan={canManageTeam ? 4 : 3}>
                  {error}
                </td>
              </tr>
            ) : members.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-center" colSpan={canManageTeam ? 4 : 3}>
                  Nenhum membro neste projeto. Adicione membros para começar.
                </td>
              </tr>
            ) : (
              members.map((member) => (
                <tr key={member.id}>
                  <td className="px-4 py-3">{member.user_name ?? "—"}</td>
                  <td className="px-4 py-3">{member.user_email}</td>
                  <td className="px-4 py-3">
                    {canManageTeam ? (
                      <Select
                        value={member.role}
                        onValueChange={(value) => handleUpdateRole(member.user_id, value)}
                      >
                        <SelectTrigger className="w-[200px]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="viewer">
                            <div>
                              <div className="font-medium">{ROLE_LABELS.viewer}</div>
                              <div className="text-xs text-muted-foreground">
                                {ROLE_DESCRIPTIONS.viewer}
                              </div>
                            </div>
                          </SelectItem>
                          <SelectItem value="editor">
                            <div>
                              <div className="font-medium">{ROLE_LABELS.editor}</div>
                              <div className="text-xs text-muted-foreground">
                                {ROLE_DESCRIPTIONS.editor}
                              </div>
                            </div>
                          </SelectItem>
                          <SelectItem value="pm">
                            <div>
                              <div className="font-medium">{ROLE_LABELS.pm}</div>
                              <div className="text-xs text-muted-foreground">
                                {ROLE_DESCRIPTIONS.pm}
                              </div>
                            </div>
                          </SelectItem>
                          <SelectItem value="admin">
                            <div>
                              <div className="font-medium">{ROLE_LABELS.admin}</div>
                              <div className="text-xs text-muted-foreground">
                                {ROLE_DESCRIPTIONS.admin}
                              </div>
                            </div>
                          </SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <span className="uppercase text-muted-foreground">
                        {ROLE_LABELS[member.role] || member.role}
                      </span>
                    )}
                  </td>
                  {canManageTeam && (
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          handleRemoveMember(member.user_id, member.user_name || member.user_email)
                        }
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pending Invites Section */}
      {canManageTeam && invites.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Convites Pendentes</h3>
          <div className="rounded-lg border border-border bg-card">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50 text-sm uppercase text-muted-foreground">
                <tr>
                  <th className="px-4 py-3 text-left font-medium">Usuário Convidado</th>
                  <th className="px-4 py-3 text-left font-medium">Permissão</th>
                  <th className="px-4 py-3 text-left font-medium">Convidado por</th>
                  <th className="px-4 py-3 text-left font-medium">Data</th>
                  <th className="px-4 py-3 text-left font-medium">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {invites.map((invite) => (
                  <tr key={invite.id}>
                    <td className="px-4 py-3">
                      <div className="font-medium">{invite.invited_email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="uppercase text-muted-foreground">
                        {ROLE_LABELS[invite.role] || invite.role}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs">
                        {invite.invited_by_name ?? invite.invited_by_email}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-xs text-muted-foreground">
                        {new Date(invite.created_at).toLocaleDateString("pt-BR")}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCancelInvite(invite.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Convidar Membro para o Projeto</DialogTitle>
            <DialogDescription>
              Envie um convite para um membro da conta acessar o projeto com permissões específicas.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="usuario@exemplo.com"
                required
              />
              <p className="text-xs text-muted-foreground">
                Você pode convidar qualquer email. Se a pessoa ainda não tiver conta, ela poderá aceitar após se cadastrar.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="role">Permissão</Label>
              <Select value={selectedRole} onValueChange={setSelectedRole}>
                <SelectTrigger id="role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">
                    <div>
                      <div className="font-medium">{ROLE_LABELS.viewer}</div>
                      <div className="text-xs text-muted-foreground">
                        {ROLE_DESCRIPTIONS.viewer}
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="editor">
                    <div>
                      <div className="font-medium">{ROLE_LABELS.editor}</div>
                      <div className="text-xs text-muted-foreground">
                        {ROLE_DESCRIPTIONS.editor}
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="pm">
                    <div>
                      <div className="font-medium">{ROLE_LABELS.pm}</div>
                      <div className="text-xs text-muted-foreground">
                        {ROLE_DESCRIPTIONS.pm}
                      </div>
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div>
                      <div className="font-medium">{ROLE_LABELS.admin}</div>
                      <div className="text-xs text-muted-foreground">
                        {ROLE_DESCRIPTIONS.admin}
                      </div>
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleAddMember}
              disabled={!inviteEmail.trim() || isSubmitting}
            >
              {isSubmitting ? "Enviando..." : "Enviar Convite"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
