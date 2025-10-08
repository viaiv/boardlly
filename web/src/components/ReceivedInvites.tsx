import { useEffect, useState } from "react";
import { Check, X } from "lucide-react";

import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface ReceivedInvite {
  id: number;
  project_id: number;
  project_name: string | null;
  project_owner: string | null;
  project_number: number | null;
  invited_email: string;
  invited_by_user_id: string;
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

export function ReceivedInvites() {
  const [invites, setInvites] = useState<ReceivedInvite[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingInvites, setProcessingInvites] = useState<Set<number>>(new Set());

  const fetchInvites = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ReceivedInvite[]>("/api/projects/invites/received");
      setInvites(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Não foi possível carregar os convites";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchInvites();
  }, []);

  const handleAccept = async (inviteId: number, projectName: string) => {
    setProcessingInvites((prev) => new Set(prev).add(inviteId));
    try {
      await apiFetch(`/api/projects/invites/${inviteId}/accept`, {
        method: "POST",
        parseJson: false,
      });

      setInvites((prev) => prev.filter((i) => i.id !== inviteId));
      toast.success("Convite aceito", {
        description: `Você agora é membro do projeto ${projectName}`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao aceitar convite";
      toast.error("Erro ao aceitar convite", {
        description: message,
      });
    } finally {
      setProcessingInvites((prev) => {
        const next = new Set(prev);
        next.delete(inviteId);
        return next;
      });
    }
  };

  const handleReject = async (inviteId: number) => {
    if (!confirm("Tem certeza que deseja rejeitar este convite?")) {
      return;
    }

    setProcessingInvites((prev) => new Set(prev).add(inviteId));
    try {
      await apiFetch(`/api/projects/invites/${inviteId}/reject`, {
        method: "POST",
        parseJson: false,
      });

      setInvites((prev) => prev.filter((i) => i.id !== inviteId));
      toast.success("Convite rejeitado");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erro ao rejeitar convite";
      toast.error("Erro ao rejeitar convite", {
        description: message,
      });
    } finally {
      setProcessingInvites((prev) => {
        const next = new Set(prev);
        next.delete(inviteId);
        return next;
      });
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Convites Recebidos</h2>
          <p className="text-sm text-muted-foreground">
            Convites para participar de projetos aguardando sua resposta.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-center">
          Carregando...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Convites Recebidos</h2>
          <p className="text-sm text-muted-foreground">
            Convites para participar de projetos aguardando sua resposta.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-center text-red-500">
          {error}
        </div>
      </div>
    );
  }

  if (invites.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold">Convites Recebidos</h2>
          <p className="text-sm text-muted-foreground">
            Convites para participar de projetos aguardando sua resposta.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-card p-6 text-center text-muted-foreground">
          Você não tem convites pendentes.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Convites Recebidos</h2>
        <p className="text-sm text-muted-foreground">
          Convites para participar de projetos aguardando sua resposta.
        </p>
      </div>

      <div className="space-y-3">
        {invites.map((invite) => (
          <div
            key={invite.id}
            className="rounded-lg border border-border bg-card p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">
                    {invite.project_name ?? `Projeto #${invite.project_number}`}
                  </h3>
                  {invite.project_owner && (
                    <span className="text-xs text-muted-foreground">
                      ({invite.project_owner})
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  Convidado por{" "}
                  <span className="font-medium">
                    {invite.invited_by_name ?? invite.invited_by_email}
                  </span>
                </p>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-medium">Permissão:</span>
                  <span className="text-muted-foreground">
                    {ROLE_LABELS[invite.role] || invite.role}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    — {ROLE_DESCRIPTIONS[invite.role]}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Recebido em {new Date(invite.created_at).toLocaleDateString("pt-BR")}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => handleAccept(invite.id, invite.project_name || `Projeto #${invite.project_number}`)}
                  disabled={processingInvites.has(invite.id)}
                >
                  <Check className="mr-2 h-4 w-4" />
                  Aceitar
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleReject(invite.id)}
                  disabled={processingInvites.has(invite.id)}
                  className="text-destructive hover:text-destructive"
                >
                  <X className="mr-2 h-4 w-4" />
                  Rejeitar
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
