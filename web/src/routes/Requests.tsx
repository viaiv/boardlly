import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/lib/api";

type ChangeRequest = {
  id: string;
  title: string;
  priority: string;
  status: string;
  request_type: string | null;
  creator_name: string | null;
  github_issue_number: number | null;
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

export function Requests() {
  const [requests, setRequests] = useState<ChangeRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    loadRequests();
  }, [statusFilter]);

  async function loadRequests() {
    try {
      setLoading(true);
      setError(null);
      const params = statusFilter !== "all" ? `?status_filter=${statusFilter}` : "";
      const data = await apiFetch<ChangeRequest[]>(`/api/requests${params}`);
      setRequests(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar solicitações");
    } finally {
      setLoading(false);
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

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Solicitações</h1>
          <p className="text-sm text-muted-foreground">
            Gerencie mudanças e melhorias propostas pela equipe
          </p>
        </div>
        <Link to="/requests/new">
          <Button>Nova Solicitação</Button>
        </Link>
      </header>

      {/* Filtros */}
      <div className="flex gap-2">
        <Button
          variant={statusFilter === "all" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("all")}
        >
          Todas
        </Button>
        <Button
          variant={statusFilter === "pending" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("pending")}
        >
          Pendentes
        </Button>
        <Button
          variant={statusFilter === "approved" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("approved")}
        >
          Aprovadas
        </Button>
        <Button
          variant={statusFilter === "converted" ? "default" : "outline"}
          size="sm"
          onClick={() => setStatusFilter("converted")}
        >
          Convertidas
        </Button>
      </div>

      {/* Estado de carregamento */}
      {loading && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          Carregando solicitações...
        </div>
      )}

      {/* Estado de erro */}
      {error && (
        <div className="rounded-lg border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Lista vazia */}
      {!loading && !error && requests.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <p className="text-sm text-muted-foreground mb-4">
            {statusFilter === "all"
              ? "Nenhuma solicitação encontrada"
              : "Nenhuma solicitação com este status"}
          </p>
          <Link to="/requests/new">
            <Button variant="outline">Criar primeira solicitação</Button>
          </Link>
        </div>
      )}

      {/* Lista de solicitações */}
      {!loading && !error && requests.length > 0 && (
        <div className="space-y-2">
          {requests.map((req) => (
            <Link
              key={req.id}
              to={`/requests/${req.id}`}
              className="block p-4 border rounded-lg hover:bg-accent transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-medium truncate">{req.title}</h3>
                    {req.github_issue_number && (
                      <span className="text-xs text-muted-foreground">
                        #{req.github_issue_number}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Por {req.creator_name || "Desconhecido"} • {formatDate(req.created_at)}
                  </p>
                </div>
                <div className="flex gap-2 items-center flex-shrink-0">
                  <Badge variant={STATUS_LABELS[req.status]?.variant || "outline"}>
                    {STATUS_LABELS[req.status]?.label || req.status}
                  </Badge>
                  <Badge variant={PRIORITY_LABELS[req.priority]?.variant || "outline"}>
                    {PRIORITY_LABELS[req.priority]?.label || req.priority}
                  </Badge>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
