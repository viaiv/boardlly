import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import { ExternalLinkIcon, ChevronLeftIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { apiFetch } from "@/lib/api";
import { useRequireRole } from "@/lib/session";

type ChangeRequestDetail = {
  id: string;
  title: string;
  description: string | null;
  impact: string | null;
  priority: string;
  status: string;
  request_type: string | null;
  creator_name: string | null;
  reviewer_name: string | null;
  github_issue_number: number | null;
  github_issue_url: string | null;
  created_at: string;
  reviewed_at: string | null;
};

const STATUS_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "Pendente", variant: "default" },
  approved: { label: "Aprovada", variant: "secondary" },
  rejected: { label: "Rejeitada", variant: "destructive" },
  converted: { label: "Convertida", variant: "outline" },
};

const PRIORITY_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  low: { label: "Baixa", variant: "outline" },
  medium: { label: "Média", variant: "secondary" },
  high: { label: "Alta", variant: "default" },
  urgent: { label: "Urgente", variant: "destructive" },
};

const TYPE_LABELS: Record<string, string> = {
  feature: "Nova Funcionalidade",
  bug: "Correção de Bug",
  tech_debt: "Dívida Técnica",
  docs: "Documentação",
};

export function RequestDetail() {
  const { requestId } = useParams<{ requestId: string }>();
  // const navigate = useNavigate(); // TODO: Usar quando implementar navegação
  // const { user } = useSession(); // TODO: Usar quando implementar permissões
  const canApprove = useRequireRole(["pm", "admin", "owner"]);

  const [request, setRequest] = useState<ChangeRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados para aprovação/rejeição
  const [approving, setApproving] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [createIssue, setCreateIssue] = useState(true);
  const [addToProject, setAddToProject] = useState(true);
  const [rejectReason, setRejectReason] = useState("");

  useEffect(() => {
    loadRequest();
  }, [requestId]);

  async function loadRequest() {
    if (!requestId) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiFetch<ChangeRequestDetail>(`/api/requests/${requestId}`);
      setRequest(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar solicitação");
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove() {
    if (!requestId) return;

    try {
      setApproving(true);
      setError(null);

      await apiFetch(`/api/requests/${requestId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          create_issue: createIssue,
          add_to_project: addToProject,
        }),
      });

      toast.success("Solicitação aprovada com sucesso!", {
        description: createIssue
          ? "Issue criada no GitHub e adicionada ao projeto."
          : "A solicitação foi aprovada.",
      });

      // Recarregar dados
      await loadRequest();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro ao aprovar solicitação";
      setError(errorMessage);
      toast.error("Erro ao aprovar solicitação", {
        description: errorMessage,
      });
    } finally {
      setApproving(false);
    }
  }

  async function handleReject() {
    if (!requestId) return;

    try {
      setRejecting(true);
      setError(null);

      await apiFetch(`/api/requests/${requestId}/reject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          rejection_reason: rejectReason || undefined,
        }),
      });

      toast.success("Solicitação rejeitada", {
        description: "A solicitação foi marcada como rejeitada.",
      });

      // Recarregar dados
      await loadRequest();
      setRejectReason("");
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Erro ao rejeitar solicitação";
      setError(errorMessage);
      toast.error("Erro ao rejeitar solicitação", {
        description: errorMessage,
      });
    } finally {
      setRejecting(false);
    }
  }

  function formatDate(dateString: string | null): string {
    if (!dateString) return "-";
    const date = new Date(dateString);
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-8 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-6 w-20" />
            </div>
          </div>
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error || "Solicitação não encontrada"}
        </div>
        <Link to="/requests">
          <Button variant="outline">Voltar para Solicitações</Button>
        </Link>
      </div>
    );
  }

  const isPending = request.status === "pending";
  const canShowActions = canApprove && isPending;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <header className="space-y-2">
        <Link to="/requests" className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ChevronLeftIcon className="h-4 w-4 mr-1" />
          Voltar para Solicitações
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h1 className="text-2xl font-semibold tracking-tight">{request.title}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Criada por {request.creator_name || "Desconhecido"} • {formatDate(request.created_at)}
            </p>
          </div>
          <div className="flex gap-2 items-center flex-shrink-0">
            <Badge variant={STATUS_LABELS[request.status]?.variant || "outline"}>
              {STATUS_LABELS[request.status]?.label || request.status}
            </Badge>
            <Badge variant={PRIORITY_LABELS[request.priority]?.variant || "outline"}>
              {PRIORITY_LABELS[request.priority]?.label || request.priority}
            </Badge>
          </div>
        </div>
      </header>

      {/* Erro de ações */}
      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Informações Principais */}
      <Card>
        <CardHeader>
          <CardTitle>Detalhes da Solicitação</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {request.request_type && (
            <div>
              <Label className="text-muted-foreground">Tipo</Label>
              <p className="text-sm">{TYPE_LABELS[request.request_type] || request.request_type}</p>
            </div>
          )}

          {request.description && (
            <div>
              <Label className="text-muted-foreground">Descrição</Label>
              <p className="text-sm whitespace-pre-wrap">{request.description}</p>
            </div>
          )}

          {request.impact && (
            <div>
              <Label className="text-muted-foreground">Impacto Esperado</Label>
              <p className="text-sm whitespace-pre-wrap">{request.impact}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Issue do GitHub (se convertida) */}
      {request.github_issue_url && (
        <Card>
          <CardHeader>
            <CardTitle>Issue Criada no GitHub</CardTitle>
            <CardDescription>
              Esta solicitação foi convertida em uma Issue no GitHub
            </CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href={request.github_issue_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
            >
              Issue #{request.github_issue_number}
              <ExternalLinkIcon className="h-4 w-4" />
            </a>
          </CardContent>
        </Card>
      )}

      {/* Informações de Revisão */}
      {request.reviewed_at && (
        <Card>
          <CardHeader>
            <CardTitle>Revisão</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div>
              <Label className="text-muted-foreground">Revisada por</Label>
              <p className="text-sm">{request.reviewer_name || "Desconhecido"}</p>
            </div>
            <div>
              <Label className="text-muted-foreground">Data da revisão</Label>
              <p className="text-sm">{formatDate(request.reviewed_at)}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ações de Aprovação/Rejeição */}
      {canShowActions && (
        <Card>
          <CardHeader>
            <CardTitle>Ações de Revisão</CardTitle>
            <CardDescription>
              Aprovar ou rejeitar esta solicitação
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            {/* Aprovar */}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button>Aprovar</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Aprovar Solicitação</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta ação aprovará a solicitação e poderá criar uma Issue no GitHub.
                  </AlertDialogDescription>
                </AlertDialogHeader>

                <div className="space-y-4 py-4">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="approve-create-issue"
                      checked={createIssue}
                      onCheckedChange={(checked) => setCreateIssue(checked === true)}
                    />
                    <label
                      htmlFor="approve-create-issue"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      Criar Issue no GitHub
                    </label>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="approve-add-to-project"
                      checked={addToProject}
                      onCheckedChange={(checked) => setAddToProject(checked === true)}
                      disabled={!createIssue}
                    />
                    <label
                      htmlFor="approve-add-to-project"
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      Adicionar ao Project
                    </label>
                  </div>
                </div>

                <AlertDialogFooter>
                  <AlertDialogCancel disabled={approving}>Cancelar</AlertDialogCancel>
                  <AlertDialogAction onClick={handleApprove} disabled={approving}>
                    {approving ? "Aprovando..." : "Confirmar"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            {/* Rejeitar */}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="secondary">Rejeitar</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Rejeitar Solicitação</AlertDialogTitle>
                  <AlertDialogDescription>
                    Esta ação marcará a solicitação como rejeitada.
                  </AlertDialogDescription>
                </AlertDialogHeader>

                <div className="space-y-2 py-4">
                  <Label htmlFor="reject-reason">Motivo da Rejeição (opcional)</Label>
                  <Textarea
                    id="reject-reason"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Explique por que esta solicitação está sendo rejeitada..."
                    rows={4}
                  />
                </div>

                <AlertDialogFooter>
                  <AlertDialogCancel disabled={rejecting} onClick={() => setRejectReason("")}>
                    Cancelar
                  </AlertDialogCancel>
                  <AlertDialogAction onClick={handleReject} disabled={rejecting}>
                    {rejecting ? "Rejeitando..." : "Confirmar"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
