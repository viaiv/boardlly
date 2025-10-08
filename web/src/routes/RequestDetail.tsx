import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { ExternalLinkIcon, ChevronLeftIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { apiFetch } from "@/lib/api";
import { useSession, useRequireRole } from "@/lib/session";

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
  const navigate = useNavigate();
  const { user } = useSession();
  const canApprove = useRequireRole(["pm", "admin", "owner"]);

  const [request, setRequest] = useState<ChangeRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados para aprovação
  const [showApproveForm, setShowApproveForm] = useState(false);
  const [approving, setApproving] = useState(false);
  const [createIssue, setCreateIssue] = useState(true);
  const [addToProject, setAddToProject] = useState(true);

  // Estados para rejeição
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejecting, setRejecting] = useState(false);
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

      // Recarregar dados
      await loadRequest();
      setShowApproveForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao aprovar solicitação");
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

      // Recarregar dados
      await loadRequest();
      setShowRejectForm(false);
      setRejectReason("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao rejeitar solicitação");
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
      <div className="space-y-4">
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Carregando solicitação...
        </div>
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
          <CardContent className="space-y-4">
            {!showApproveForm && !showRejectForm && (
              <div className="flex gap-3">
                <Button onClick={() => setShowApproveForm(true)}>Aprovar</Button>
                <Button variant="destructive" onClick={() => setShowRejectForm(true)}>
                  Rejeitar
                </Button>
              </div>
            )}

            {/* Formulário de Aprovação */}
            {showApproveForm && (
              <div className="space-y-4 p-4 border rounded-lg bg-secondary/10">
                <h3 className="font-medium">Aprovar Solicitação</h3>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="create-issue"
                    checked={createIssue}
                    onCheckedChange={(checked) => setCreateIssue(checked === true)}
                  />
                  <label
                    htmlFor="create-issue"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    Criar Issue no GitHub
                  </label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="add-to-project"
                    checked={addToProject}
                    onCheckedChange={(checked) => setAddToProject(checked === true)}
                    disabled={!createIssue}
                  />
                  <label
                    htmlFor="add-to-project"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    Adicionar ao Project
                  </label>
                </div>

                <div className="flex gap-3 pt-2">
                  <Button onClick={handleApprove} disabled={approving}>
                    {approving ? "Aprovando..." : "Confirmar Aprovação"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => setShowApproveForm(false)}
                    disabled={approving}
                  >
                    Cancelar
                  </Button>
                </div>
              </div>
            )}

            {/* Formulário de Rejeição */}
            {showRejectForm && (
              <div className="space-y-4 p-4 border rounded-lg bg-destructive/5">
                <h3 className="font-medium">Rejeitar Solicitação</h3>

                <div className="space-y-2">
                  <Label htmlFor="reject-reason">Motivo da Rejeição (opcional)</Label>
                  <Textarea
                    id="reject-reason"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Explique por que esta solicitação está sendo rejeitada..."
                    rows={4}
                  />
                </div>

                <div className="flex gap-3 pt-2">
                  <Button variant="destructive" onClick={handleReject} disabled={rejecting}>
                    {rejecting ? "Rejeitando..." : "Confirmar Rejeição"}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setShowRejectForm(false);
                      setRejectReason("");
                    }}
                    disabled={rejecting}
                  >
                    Cancelar
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
